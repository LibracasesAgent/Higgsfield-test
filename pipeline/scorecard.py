#!/usr/bin/env python3
"""Scorecard: measure a finished video against the measured format of the clients' top-impression voiceover ads.

  python3 pipeline/scorecard.py ad.mp4 [more.mp4 ...] [--json out.json] [--vs ref.mp4] [--no-whisper] [--words words.json]

One video: a table (metric, value, target, PASS/FAIL) and a one-line verdict; several (or --vs ref.mp4, the reference as the
last column): one matrix, '!' marks a miss; `label=path` names a column. Library:

  score(path, words=None, whisper=True, cuts=None) -> {"path", "duration", "resolution", "fps", "metrics": {name: {"value", "target": [lo, hi],
      "pass": True|False|None}}, "info": {...}, "detail": {"cuts", "silences", "repeats", "cards", "words"}, "failed": [names],
      "pass": bool, "verdict": str}
  qa_line(path, words=None, cuts=None) -> (problems, summary)     # problems: only the failed metrics, soft (the caller flags them); never raises
  TARGETS                                              # name -> (lo, hi), None = no limit

words: [[start, end, "word"], ...] (or dicts {"w","s","e"} / {"word","start","end"}, or a words.json path), seconds of the finished
video, when the caller knows what is said and when; else faster-whisper 'small' (int8, cpu) transcribes the video once and the
words are cached in the temp dir (SCORECARD_CACHE; never in the repo). whisper=False / --no-whisper: no speech metrics (value
None, pass None). A video with sound but no words scores 0 wpm and fails them.

How it measures
  speech   words per minute over the whole video, speech share (sum of word spans / length), longest silence between words
           (the last 0.6 s are not counted), first word. Word times are whisper's: good to about 0.1-0.2 s, which is enough
           for pauses over 0.5 s, not for the first word to the frame.
  picture  cuts: ffmpeg scene > 0.3 plus a second pass on the frame-to-frame difference of 72x128 frames (>= 0.2), so soft cuts and
           cuts after a calm shot count; detections within 0.4 s are one cut (a flash or whip transition); fast motion inside
           a shot is not a cut. A review card laid over cutting B-roll hides the cuts under it (that shows as a long shot).
  repeats  16x16 dhash of every frame, Hamming <= 6: a shot with a frame like one of another shot 0.5-10 s earlier (same source
           moment, same framing). A re-crop of the moment is another picture and is not found.
  cards    held card: runs of >= 3.2 s whose frames 0.5 s apart differ by < 1% (a full-frame still; an overlay on moving
           footage is not one: see the long shot).
  sound    ebur128: integrated LUFS, LRA, true peak.
  Voices (one narrator or several) are not measured: that needs a listener.

Targets: owner's format (length 55-80 s, the Ad Library median is 66 s) plus the 3 reference ads (62 s, 49 s, 81 s; the clients'
top impressions). A target that 2 of the 3 references miss is widened to fit them (not the length: that is the owner's decision).
Measured on them, 2026-10-14: wpm 187-220, speech 88-91%, longest silence 0.38-0.66 s, average shot 1.70-1.95 s, longest shot
3.2-4.3 s, LUFS -14.0 to -14.1, LRA 1.3-2.8 LU, true peak -0.8 to -1.9 dBTP, no repeats, no held cards.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

W, H = 72, 128               # frames the picture metrics look at (area-downscaled: compression noise averages out)
CUT_SCENE = 0.3              # ffmpeg scene score of a hard cut
CUT_DIFF = 0.2               # second pass: mean abs RGB difference of two consecutive frames (0-1) that is a cut
CUT_GAP = 0.4                # detections closer than this are one cut (a flash or whip transition shows as 2-3)
EDGE = 0.3                   # a cut this close to the start or end is no cut
TAIL = 0.6                   # silence after the last word is only counted beyond this
HAMMING, LAG = 6, (0.5, 10.0)  # a repeated shot: dhash distance, seconds after the first showing
CARD_DIFF, CARD_SECS = 0.01, 3.2

TARGETS = {                  # name: (lo, hi); None = no limit
    "length_s": (55, 80),
    "wpm": (185, 215),
    "speech_share": (0.85, None),
    "longest_silence_s": (None, 0.8),
    "first_word_s": (None, 0.35),
    "avg_shot_s": (1.4, 2.6),
    "max_shot_s": (None, 4.0),
    "lufs": (-15.0, -13.0),
    "lra": (None, 4.0),
    "true_peak": (None, -1.0),
    "repeated_shots": (None, 0),
    "held_cards": (None, 0),
}
LABEL = {                    # name: (table label, value format, unit)
    "length_s": ("length", "{:.1f}", " s"),
    "wpm": ("words per minute", "{:.0f}", ""),
    "speech_share": ("speech share", "{:.0f}", "%"),
    "longest_silence_s": ("longest silence", "{:.2f}", " s"),
    "first_word_s": ("first word at", "{:.2f}", " s"),
    "avg_shot_s": ("average shot", "{:.2f}", " s"),
    "max_shot_s": ("longest shot", "{:.1f}", " s"),
    "lufs": ("loudness", "{:.1f}", " LUFS"),
    "lra": ("loudness range", "{:.1f}", " LU"),
    "true_peak": ("true peak", "{:.1f}", " dBTP"),
    "repeated_shots": ("repeated shots", "{:.0f}", ""),
    "held_cards": ("held cards", "{:.0f}", ""),
}
SHORT = {                    # name: short problem text for qa_line / the verdict
    "length_s": "length {:.0f}s", "wpm": "{:.0f} wpm", "speech_share": "speech {:.0f}%", "longest_silence_s": "pause {:.2f}s",
    "first_word_s": "first word {:.2f}s", "avg_shot_s": "avg shot {:.2f}s", "max_shot_s": "shot {:.1f}s", "lufs": "{:.1f} LUFS",
    "lra": "LRA {:.1f}", "true_peak": "peak {:.1f} dBTP", "repeated_shots": "{:.0f} repeated shots", "held_cards": "{:.0f} held cards",
}
SPEECH = ("wpm", "speech_share", "longest_silence_s", "first_word_s")
_MODEL = []


# ---------- inputs ----------
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=kw.pop("text", True), **kw)


def probe(path):
    """(duration s, width, height, fps, has sound) of the first video stream; duration from the container."""
    r = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", path])
    if r.returncode:
        raise RuntimeError(f"ffprobe failed: {r.stderr.strip()[:200]}")
    j = json.loads(r.stdout)
    vs = [x for x in j.get("streams", []) if x.get("codec_type") == "video"]
    if not vs:
        raise RuntimeError("no video stream")
    a, _, b = (vs[0].get("r_frame_rate") or "30/1").partition("/")
    fps = float(a) / float(b or 1) if float(b or 1) else 30.0
    return float(j["format"]["duration"]), int(vs[0].get("width", 0)), int(vs[0].get("height", 0)), fps, any(x.get("codec_type") == "audio" for x in j["streams"])


def norm_words(words):
    """[(start, end, word)] from lists, dicts ({"w","s","e"} / {"word","start","end"}) or a words.json path; sorted."""
    if isinstance(words, str):
        words = json.load(open(words))
    out = []
    for w in words or []:
        if isinstance(w, dict):
            s, e, t = w.get("s", w.get("start")), w.get("e", w.get("end")), w.get("w", w.get("word"))
        else:
            s, e, t = w
        if s is not None and e is not None and str(t).strip():
            out.append((float(s), max(float(e), float(s)), str(t).strip()))
    return sorted(out)


def cache_file(path):
    st = os.stat(path)
    key = hashlib.sha1(f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()[:16]
    d = os.environ.get("SCORECARD_CACHE") or os.path.join(tempfile.gettempdir(), "libra_scorecard")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, key + ".words.json")


def transcribe(path):
    """Word timings of the video's sound (faster-whisper 'small', int8, cpu); cached in the temp dir."""
    cf_ = cache_file(path)
    if os.path.exists(cf_):
        try:
            return norm_words(cf_)
        except (OSError, ValueError):
            pass
    from faster_whisper import WhisperModel
    if not _MODEL:
        _MODEL.append(WhisperModel(os.environ.get("SCORECARD_MODEL", "small"), device="cpu", compute_type="int8",
                                   cpu_threads=os.cpu_count() or 4))
    segs, _ = _MODEL[0].transcribe(path, word_timestamps=True, language="en", condition_on_previous_text=False)
    ws = [(w.start, w.end, w.word.strip()) for s in segs for w in s.words if w.word.strip()]
    json.dump(ws, open(cf_, "w"))
    return norm_words(ws)


# ---------- picture ----------
def decode(path, fps, tmp):
    """(rgb frames (n, H, W, 3) at fps, ffmpeg scene hits [(t, score)]) from one decode of the video (scratch dir tmp)."""
    scene_file = "scene.txt"        # relative to tmp: no path to escape in the filter graph
    fg = (f"[0:v]split=2[s][r];[s]scale=160:-2:flags=bilinear,select='gt(scene,{CUT_SCENE})',metadata=print:file={scene_file}[so];"
          f"[r]fps={fps},scale={W}:{H}:flags=area[ro]")
    r = run(["ffmpeg", "-v", "error", "-nostdin", "-i", os.path.abspath(path), "-an", "-filter_complex", fg, "-map", "[so]", "-f", "null", "-",
             "-map", "[ro]", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], text=False, cwd=tmp)
    if r.returncode and not r.stdout:
        raise RuntimeError(f"ffmpeg decode failed: {r.stderr.decode(errors='replace')[-200:]}")
    n = len(r.stdout) // (W * H * 3)
    a = np.frombuffer(r.stdout, np.uint8, n * W * H * 3).reshape(n, H, W, 3)
    hits = []
    if os.path.exists(os.path.join(tmp, scene_file)):
        txt = open(os.path.join(tmp, scene_file)).read()
        hits = [(float(t), float(s)) for t, s in re.findall(r"pts_time:([\d.]+)\s*\nlavfi\.scene_score=([\d.]+)", txt)]
    return a, hits


def frame_diffs(a):
    """Mean abs RGB difference (0-1) of each frame to the one before (index i = frame i+1 vs i)."""
    out = np.zeros(max(len(a) - 1, 0), np.float32)
    for i in range(0, len(out), 256):
        x = a[i:i + 257].astype(np.int16)
        out[i:i + len(x) - 1] = np.abs(x[1:] - x[:-1]).mean(axis=(1, 2, 3)) / 255
    return out


def find_cuts(a, hits, fps, dur):
    """Cut times: ffmpeg scene hits plus frame differences >= CUT_DIFF; detections within CUT_GAP are one cut."""
    d = frame_diffs(a)
    ts = [t for t, _ in hits] + [(i + 1) / fps for i in np.nonzero(d >= CUT_DIFF)[0]]
    cuts = []
    for t in sorted(ts):
        if EDGE < t < dur - EDGE and (not cuts or t - cuts[-1] >= CUT_GAP):
            cuts.append(round(float(t), 3))
    return cuts


def dhashes(a):
    """(n, 256) bool: 16x16 difference hash of every frame (16 rows x 16 left-right comparisons); valid[n]: False for a flat frame."""
    cols = np.linspace(0, W, 18).astype(int)
    bits, valid = [], []
    for i in range(0, len(a), 256):
        g = a[i:i + 256].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)      # (n, H, W)
        x = g.reshape(len(g), 16, H // 16, W).mean(2)
        x = np.add.reduceat(x, cols[:-1], axis=2) / np.diff(cols)
        bits.append((x[:, :, 1:] > x[:, :, :-1]).reshape(len(g), 256))
        valid.append(g.reshape(len(g), -1).std(1) >= 3)
    return (np.concatenate(bits), np.concatenate(valid)) if bits else (np.zeros((0, 256), bool), np.zeros(0, bool))


def find_repeats(a, cuts, fps):
    """[(t, earlier t)]: the first frame of each shot that looks like a frame of another shot 0.5-10 s before it (every frame is
    compared: footage moves, so two showings of one moment only match frame to frame)."""
    bits, valid = dhashes(a)
    ts = np.arange(len(a)) / fps
    shot = np.searchsorted(cuts, ts, side="right")
    shot_e = np.searchsorted(cuts, ts + 0.07, side="right")     # a detected cut is up to 2 frames late: frames just before it already show the new shot
    lo_lag, hi_lag = int(round(LAG[0] * fps)), int(round(LAG[1] * fps))
    seen, out = set(), []
    for i in np.nonzero(valid)[0]:
        if shot[i] in seen or i - lo_lag < 0:
            continue
        j0 = max(i - hi_lag, 0)
        ok = valid[j0:i - lo_lag + 1] & (shot[j0:i - lo_lag + 1] != shot[i]) & (shot_e[j0:i - lo_lag + 1] != shot[i]) & ((bits[j0:i - lo_lag + 1] != bits[i]).sum(1) <= HAMMING)
        if ok.any():
            seen.add(shot[i])
            out.append((round(float(ts[i]), 2), round(float(ts[j0 + np.argmax(ok)]), 2)))
    return out


def find_cards(a, fps):
    """[(t, seconds)]: runs where frames 0.5 s apart differ by < 1% for at least 3.2 s (a still card)."""
    step = max(1, round(fps / 2))
    s = a[::step].astype(np.int16)
    if len(s) < 2:
        return []
    low = np.abs(s[1:] - s[:-1]).mean(axis=(1, 2, 3)) / 255 < CARD_DIFF
    out, i = [], 0
    while i < len(low):
        if not low[i]:
            i += 1
            continue
        j = i
        while j < len(low) and low[j]:
            j += 1
        secs = (j - i) * step / fps + step / fps / 2     # first to last frame plus half a step
        if secs >= CARD_SECS:
            out.append((round(i * step / fps, 2), round(secs, 1)))
        i = j
    return out


# ---------- sound ----------
def loudness(path):
    """(integrated LUFS, LRA LU, true peak dBTP) by ebur128; None where the video has no sound."""
    r = run(["ffmpeg", "-nostdin", "-nostats", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"])
    t = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
    def g(rx):
        m = re.search(rx, t)
        return float(m.group(1)) if m else None
    return g(r"I:\s+(-?[\d.]+) LUFS"), g(r"LRA:\s+([\d.]+) LU"), g(r"Peak:\s+(-?[\d.]+) dBFS")


# ---------- speech ----------
def speech_stats(ws, dur):
    """(metrics dict, silences [(start, length)] >= 0.5 s) from [(start, end, word)]."""
    if not ws:
        return {"words": 0, "wpm": 0.0, "speech_share": 0.0, "longest_silence_s": dur, "first_word_s": dur}, []
    span = sum(min(e, dur) - min(s, dur) for s, e, _ in ws)
    gaps = [(ws[i][1], ws[i + 1][0] - ws[i][1]) for i in range(len(ws) - 1)]
    gaps.append((ws[-1][1], max(dur - TAIL - ws[-1][1], 0.0)))
    return {"words": len(ws), "wpm": len(ws) / dur * 60, "speech_share": span / dur, "longest_silence_s": max(g for _, g in gaps),
            "first_word_s": ws[0][0]}, [(round(t, 2), round(g, 2)) for t, g in gaps if g >= 0.5]


# ---------- scoring ----------
def disp(name, v):
    """The number as shown: the speech share in percent."""
    return None if v is None else v * 100 if name == "speech_share" else v


def short(name, v):
    return SHORT[name].format(disp(name, v))


def judge(name, v):
    lo, hi = TARGETS[name]
    if v is None:
        return {"value": None, "target": [lo, hi], "pass": None}
    return {"value": v, "target": [lo, hi], "pass": (lo is None or v >= lo - 1e-9) and (hi is None or v <= hi + 1e-9)}


def verdict_of(m):
    """One line: how many targets are met and which are not."""
    f = [k for k, x in m.items() if x["pass"] is False]
    n = sum(x["pass"] is not None for x in m.values())
    return f"PASS: all {n} targets met" if not f else f"FAIL {n - len(f)}/{n}: " + ", ".join(short(k, m[k]["value"]) for k in f)


def score(path, words=None, whisper=True, cuts=None):
    """Measure one video: see the module docstring for the dict. words: known word timings; whisper=False: no speech metrics;
    cuts: the cut seconds when the caller knows its own timeline (the renderer: no detection, so no cut hidden under an overlay
    or soft inside one dark clip is missed or invented)."""
    dur, w, h, fps, sound = probe(path)
    fps = 30 if fps >= 29.5 else max(int(round(fps)), 1)
    with tempfile.TemporaryDirectory(prefix="scorecard_") as td, cf.ThreadPoolExecutor(2) as ex:
        fv, fl = ex.submit(decode, path, fps, td), ex.submit(loudness, path)
        note = None if sound else "no sound track"
        try:
            ws = norm_words(words) if words is not None else (None if not whisper else [] if not sound else transcribe(path))
        except Exception as e:  # no transcriber installed, no sound track: the picture and loudness metrics still run
            ws, note = None, f"speech metrics skipped ({type(e).__name__}: {str(e)[:80]})"
        a, hits = fv.result()
        lufs, lra, tp = fl.result()
    cuts = find_cuts(a, hits, fps, dur) if cuts is None else sorted(round(float(c), 3) for c in cuts if EDGE < c < dur - EDGE)
    edges = [0.0] + cuts + [dur]
    shots = [b - x for x, b in zip(edges, edges[1:])]
    reps, cards = find_repeats(a, cuts, fps), find_cards(a, fps)
    sp, sil = speech_stats(ws, dur) if ws is not None else ({}, [])
    val = {"length_s": dur, "avg_shot_s": float(np.mean(shots)), "max_shot_s": max(shots), "lufs": lufs, "lra": lra, "true_peak": tp,
           "repeated_shots": len(reps), "held_cards": len(cards), **{k: sp.get(k) for k in SPEECH}}
    m = {k: judge(k, val[k]) for k in TARGETS}
    info = {"words": sp.get("words"), "shots": len(shots), "median_shot_s": float(np.median(shots)), "shots_under_0.8s": int(sum(x < 0.8 for x in shots)),
            "pauses_over_0.5s": len(sil) if ws is not None else None, "note": note}
    failed = [k for k, x in m.items() if x["pass"] is False]
    return {"path": path, "duration": dur, "resolution": f"{w}x{h}", "fps": fps, "metrics": m, "info": info,
            "detail": {"cuts": cuts, "silences": sil, "repeats": reps, "cards": cards, "words": len(ws) if ws is not None else None},
            "failed": failed, "pass": not failed, "verdict": verdict_of(m)}


def qa_line(path, words=None, cuts=None):
    """(problems, summary) for make_batch's render QA: problems = short strings for the failed metrics only (soft: the caller
    flags them); summary = one line with the main numbers. cuts: the renderer's own cut seconds (see score). Never raises."""
    try:
        r = score(path, words=words, cuts=cuts)
    except Exception as e:  # soft check: a missing ffmpeg or an odd file must not stop a render
        return [], f"scorecard unavailable: {str(e)[:120]}"
    m = r["metrics"]
    probs = [f"{short(k, m[k]['value'])} (target {target_text(k)})" for k in r["failed"]]
    v = {k: x["value"] for k, x in m.items()}
    bits = [f"{v['length_s']:.0f}s"]
    if v["wpm"] is not None:
        bits += [f"{v['wpm']:.0f} wpm", f"speech {v['speech_share'] * 100:.0f}%", f"longest pause {v['longest_silence_s']:.2f}s"]
    bits.append(f"shots {v['avg_shot_s']:.1f}s avg")
    if v["lufs"] is not None:
        bits.append(f"{v['lufs']:.1f} LUFS LRA {v['lra']:.1f}")
    bits += [f"{v['repeated_shots']} repeats", f"{v['held_cards']} held cards"]
    n = sum(x["pass"] is not None for x in m.values())
    return probs, " · ".join(bits) + f" · {n - len(probs)}/{n} targets met"


# ---------- output ----------
def fmt(name, v):
    if v is None:
        return "n/a"
    return LABEL[name][1].format(disp(name, v)) + LABEL[name][2]


def target_text(name):
    lo, hi = TARGETS[name]
    f, u = (lambda x: "%g" % disp(name, x)), LABEL[name][2]
    return f"{f(lo)} to {f(hi)}{u}" if lo is not None and hi is not None else f">= {f(lo)}{u}" if lo is not None else f"<= {f(hi)}{u}"


def na(v):
    return "n/a" if v is None else str(v)


def grid(rows):
    wd = [max(len(str(x[i])) for x in rows) for i in range(len(rows[0]))]
    return ["  ".join(str(c).ljust(wd[i]) for i, c in enumerate(x)).rstrip() for x in rows]


def table(r, name):
    """One video: a row per metric with its target and PASS/FAIL, the extra counts, the verdict."""
    rows = [("metric", "value", "target", "")] + [(LABEL[k][0], fmt(k, x["value"]), target_text(k), {True: "PASS", False: "FAIL", None: "skip"}[x["pass"]])
                                                  for k, x in r["metrics"].items()]
    i = r["info"]
    return "\n".join([f"{name}  ({r['resolution']}, {r['fps']} fps)"] + ["  " + x for x in grid(rows)] + [
        f"  also: {na(i['words'])} words, {i['shots']} shots (median {i['median_shot_s']:.1f} s, {i['shots_under_0.8s']} under 0.8 s), "
        f"{na(i['pauses_over_0.5s'])} pauses over 0.5 s", "  " + r["verdict"]] + (["  " + i["note"]] if i["note"] else []))


def matrix(rs, names):
    """Several videos side by side: a row per metric, '!' after a missed value."""
    rows = [["metric", "target"] + names]
    rows += [[LABEL[k][0], target_text(k)] + [fmt(k, r["metrics"][k]["value"]) + (" !" if r["metrics"][k]["pass"] is False else "") for r in rs] for k in TARGETS]
    rows += [["(words)", ""] + [na(r["info"]["words"]) for r in rs], ["(shots, under 0.8 s)", ""] + [f"{r['info']['shots']}, {r['info']['shots_under_0.8s']}" for r in rs],
             ["(pauses over 0.5 s)", ""] + [na(r["info"]["pauses_over_0.5s"]) for r in rs],
             ["targets met", ""] + [f"{sum(x['pass'] is True for x in r['metrics'].values())}/{sum(x['pass'] is not None for x in r['metrics'].values())}" for r in rs]]
    return "\n".join(grid(rows))


def main():
    ap = argparse.ArgumentParser(description="Score finished videos against the voiceover-ad format targets (label=path names a column).")
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--json", help="write the scores (a dict per video path) here")
    ap.add_argument("--vs", help="a reference video: scored too, shown as the last column")
    ap.add_argument("--no-whisper", action="store_true", help="skip the speech metrics (no transcription)")
    ap.add_argument("--words", help="words.json ([[start, end, word], ...]) for a single video: skip whisper")
    a = ap.parse_args()
    items = []
    for x in a.videos + ([a.vs] if a.vs else []):
        lab, _, p = x.partition("=")
        items.append((lab, p) if p and not os.path.exists(x) else (os.path.splitext(os.path.basename(x))[0], x))
    if a.vs:
        items[-1] = (items[-1][0] + " (ref)", items[-1][1])
    rs = []
    for lab, p in items:
        print(f"scoring {p} ...", file=sys.stderr)
        rs.append(score(p, words=a.words if a.words and len(items) == 1 else None, whisper=not a.no_whisper))
        rs[-1]["label"] = lab
    names = [lab for lab, _ in items]
    if len(rs) == 1:
        print(table(rs[0], names[0]))
    else:
        print(matrix(rs, names), "", *[f"{n}: {r['verdict']}" for n, r in zip(names, rs)], sep="\n")
    if a.json:
        json.dump({p: r for (_, p), r in zip(items, rs)}, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
