#!/usr/bin/env python3
"""Winner variation: re-edit a textless RAW winner into a new 50-90 s ad (for longform.py).

  cold open (a strong line from later in the RAW)  ->  RAW from the top  ->  real-review section
  (narrated, verbatim review cards over real B-roll) inserted before the offer  ->  RAW offer + CTA  ->  end card

  python3 pipeline/remix.py remix.json --out ad.mp4

remix.json (paths relative to the JSON; any src may also be a Drive file id or an https URL):
{
  "raw": "1LEOgUgU_hBiRceIx-SW4za6XJZlCQNrH",   # RAW file (Drive id from clip_bank winner_raws, or a local file)
  "cold_open": [12.4, 16.1],          # seconds in the RAW used as the hook (also kept in place later); optional
  "hook_label": "10 YEARS LATER",     # label at 0.1 s (over the cold open, or over the RAW start without one)
  "start": 0.0, "end": null,          # RAW range used for the body
  "cut": [[a, b], ...],               # optional RAW ranges to drop (repeats, dead air)
  "insert_at": 44.3,                  # RAW time where the review section goes (before the offer)
  "reviews": {"vo": "V01_rev.mp3", "text": "<the VO script>", "cards": [{"n": 7, "word": "carol"}, ...],
              "broll": [[src, start], ...]},   # cards anchor to their word in the VO, in order (text = fallback timing)
  "burned_captions": false,           # RAW already has captions: skip ours
  "labels": [{"text": "REASON 1", "word": "one", "after": 8.0}],   # optional number labels (RAW times)
  "offer_word": "50", "offer_after": null,     # offer card at the first offer_word after insert_at - 1 (or offer_after)
  "offer_title": "50% OFF", "offer_sub": "+ FREE MATCHING WALLET",   # "" sub: title only
  "end_title": "The Luxury Hobo Bag", "end_sub": "Tap the link below", "keywords": [...]
}
Transcripts: a committed pipeline/data/transcripts/<winner key>_words.json is used for clip-bank files (found by
Drive id), <name>_words.json for local files; anything else is transcribed once (faster-whisper) and cached.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRANS = os.path.join(HERE, "data", "transcripts")
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
STILL = (".png", ".jpg", ".jpeg", ".webp")


def loc(d, s):
    """Local file for s: a path relative to the spec, a Drive file id (downloaded in safe chunks and cached),
    or an https URL (downloaded once and cached). Needed wherever audio is mixed or speech is transcribed."""
    p = os.path.join(d, s)
    if os.path.exists(p):
        return p
    sys.path.insert(0, HERE)
    import recut
    if s.startswith("http"):
        import hashlib
        import urllib.request
        os.makedirs(recut.MEDIA_CACHE, exist_ok=True)
        f = os.path.join(recut.MEDIA_CACHE, hashlib.md5(s.encode()).hexdigest() + os.path.splitext(s.split("?")[0])[1])
        if not os.path.exists(f):
            part = f"{f}.part.{os.getpid()}"            # per process: parallel renders may fetch the same URL
            urllib.request.urlretrieve(s, part)
            os.replace(part, f)
        return f
    recut.LOCAL_MAX = max(recut.LOCAL_MAX, 600 * 2**20)
    f = recut.source(s)
    if f.startswith("http") and DRIVE_ID.match(s):   # not link-shared (or too big): download with the agent's login
        try:
            from drive_upload import access_token, download
            return download(access_token(), s, os.path.join(recut.MEDIA_CACHE, s))
        except (Exception, SystemExit) as e:  # noqa: BLE001
            print(f"loc: authenticated download of {s} failed ({e}); reading it over HTTP", file=sys.stderr)
    return f


def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True).stdout)


_DUR = {}


def fit(d, src, st, L):
    """(start, speed) so L output seconds fit inside src: move the start back, or slow a too-short clip down
    (a segment that runs out of footage would end early and push the picture out of sync with the sound)."""
    if str(src).lower().endswith(STILL):
        return st, 1.0
    if src not in _DUR:
        try:
            _DUR[src] = dur(loc(d, src))
        except (ValueError, OSError):
            _DUR[src] = None
    D = _DUR[src]
    if not D or st + L <= D - 0.05:
        return st, 1.0
    if L <= D - 0.1:
        return round(D - L - 0.1, 3), 1.0
    return 0.0, round(max((D - 0.1) / L, 0.25), 3)


def _norm(ws):
    return [w if isinstance(w, dict) else dict(w=w[0], s=w[1], e=w[2]) for w in ws]


def committed(path):
    """Committed transcript for a cached clip-bank file (by Drive id) or a local file (by base name)."""
    base = os.path.splitext(os.path.basename(path))[0]
    names = []
    try:
        bank = json.load(open(os.path.join(HERE, "data", "clip_bank.json")))
        for sec, v in bank.items():
            if isinstance(v, dict) and sec not in ("_help", "voices"):
                names += [k for k, e in v.items() if isinstance(e, dict) and e.get("id") == base]
    except (OSError, ValueError):
        pass
    for n in names + [base]:
        f = os.path.join(TRANS, n + "_words.json")
        if os.path.exists(f):
            return _norm(json.load(open(f)))
    return None


def words(path):
    ws = committed(path)
    if ws is not None:
        return ws
    j = os.path.splitext(path)[0] + "_words.json"
    if os.path.exists(j) and os.path.getmtime(j) >= os.path.getmtime(path):   # a re-made VO gets a new transcript
        return _norm(json.load(open(j)))
    from faster_whisper import WhisperModel
    m = WhisperModel("small.en", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(path, word_timestamps=True, condition_on_previous_text=False)
    ws = [dict(w=w.word.strip(), s=round(w.start, 2), e=round(w.end, 2)) for s in segs for w in s.words if w.word.strip()]
    json.dump(ws, open(j + f".{os.getpid()}", "w"))
    os.replace(j + f".{os.getpid()}", j)          # atomic: parallel renders may share a clip
    return ws


def clean(w):
    return re.sub(r"[^\w%']", "", w.lower())


def hit(w, word):
    """Whisper token w is the card word: same start, or a close spelling ('jenny'/'jennie') with the same first letter
    and length (so 'every' never stands in for 'beverly')."""
    w = clean(w)
    return w.startswith(word) or (len(word) >= 5 and w[:1] == word[:1] and abs(len(w) - len(word)) <= 2
                                  and difflib.SequenceMatcher(None, w, word).ratio() >= 0.75)


def card_starts(vw, cards, text, L):
    """Start time of each card in the review VO: its word, searched in order after the previous card's word.
    A word whisper missed is placed by its position in the script text (or 0.2 s for the first card)."""
    starts, k, tp = [], 0, 0
    toks = [clean(t) for t in (text or "").split()]
    for c in cards:
        pos = next((i for i in range(tp, len(toks)) if hit(toks[i], c["word"])), None)
        tp = tp if pos is None else pos + 1
        j = next((i for i in range(k, len(vw)) if hit(vw[i]["w"], c["word"])), None)
        if j is not None:
            starts.append(vw[j]["s"])
            k = j + 1
            continue
        print(f"review card {c['n']} placed by its script position (whisper did not hear {c['word']!r})", file=sys.stderr)
        est = L * pos / len(toks) if pos is not None else (starts[-1] + 1.5 if starts else 0.2)
        est = max(est, starts[-1] + 0.8 if starts else 0.2)
        starts.append(round(min(est, max(L - 1.0, 0.2)), 2))
    return starts


def build(r, d):
    raw = r["raw"]
    R = dur(loc(d, raw))
    start, end = r.get("start") or 0.0, r.get("end") or R
    cuts = sorted(r.get("cut") or [])
    ins = r.get("insert_at")
    has_rev = bool(ins is not None and r.get("reviews"))
    # RAW body pieces (RAW-time ranges), split at the insertion point and around cuts
    pieces, t = [], start
    for a, b in cuts + [[end, end]]:
        if a > t:
            pieces.append([t, min(a, end)])
        t = max(t, b)
    body, placed = [], not has_rev
    for a, b in pieces:
        if not placed and ins <= a:          # insert point on a cut boundary: reviews go before the next piece
            body.append("REVIEWS")
            placed = True
        if not placed and a < ins < b:
            body += [[a, ins], "REVIEWS", [ins, b]]
            placed = True
        else:
            body.append([a, b])
    if not placed:
        body.append("REVIEWS")

    segs, audio, ov, t = [], [], [], 0.0
    raw_to_out = []                         # (raw_a, raw_b, out_a) for mapping RAW times to output times

    def raw_seg(a, b, **ex):
        nonlocal t
        segs.append(dict(src=raw, start=round(a, 3), dur=round(b - a, 3), **ex))
        audio.append(("slice", raw, a, b))
        raw_to_out.append((a, b, t))
        t += b - a

    co = r.get("cold_open")
    hook = None
    if co:
        raw_seg(co[0], co[1])
        hook = dict(type="label", text=r.get("hook_label", "WAIT FOR IT"), at=0.1, dur=min(1.6, co[1] - co[0]), y=300)
    elif r.get("hook_label"):
        hook = dict(type="label", text=r["hook_label"], at=0.1, dur=1.6, y=300)
    review_at = None
    for p in body:
        if p == "REVIEWS":
            rv = r["reviews"]
            L = dur(loc(d, rv["vo"])) + 0.4
            review_at = t
            br = rv["broll"]
            for src, st in br:
                st, sp = fit(d, src, st, L / len(br))
                segs.append(dict(src=src, start=st, dur=round(L / len(br), 3), mute=True, **({"speed": sp} if sp != 1.0 else {})))
            audio.append(("file", rv["vo"], L))
            t += L
        else:
            raw_seg(p[0], p[1])

    def out_time(rt):
        for a, b, oa in raw_to_out[1 if co else 0:]:
            if a <= rt <= b:
                return oa + (rt - a)
        return None

    # review cards synced to the narration words
    if review_at is not None:
        rv = r["reviews"]
        L = dur(loc(d, rv["vo"]))
        starts = card_starts(words(loc(d, rv["vo"])), rv["cards"], rv.get("text"), L)
        for k, c in enumerate(rv["cards"]):
            a = review_at + 0.1 + starts[k]
            b = review_at + 0.1 + (starts[k + 1] if k + 1 < len(starts) else L + 0.2)
            ov.append(dict(type="review", n=c["n"], at=round(a, 2), dur=round(b - a, 2), y=330))
    # number labels and offer card from the RAW transcript
    ws = words(loc(d, raw))
    for lb in r.get("labels") or []:
        w0 = next((x for x in ws if x["s"] >= lb.get("after", 0) and x["w"].lower().strip(".,") == lb["word"]), None)
        if w0 and out_time(w0["s"]) is not None:
            ov.append(dict(type="label", text=lb["text"], at=round(out_time(w0["s"]), 2), dur=1.4, y=300))
        else:
            print(f"overlay anchor not found: label {lb['text']!r} (word {lb['word']!r})", file=sys.stderr)
    title, sub = r.get("offer_title", "50% OFF"), r.get("offer_sub", "+ FREE MATCHING WALLET")
    review_end = review_at + dur(loc(d, r["reviews"]["vo"])) + 0.4 if review_at is not None else 0
    if title and not r.get("offer_word"):    # the RAW never says the offer: the card goes with its call to action,
        a = max(review_end, t - 2.6 - 3.4)   # just before the end card, so the theme and the offer still show
        ov.append(dict(type="offer", title=title, sub=sub, at=round(a, 2), dur=3.2, y=420) if sub else
                  dict(type="label", text=title, at=round(a, 2), dur=3.2, y=470))
        print(f"offer card placed before the end card at {a:.1f}s (the RAW has no offer word)", file=sys.stderr)
    elif r.get("offer_word") and title:
        after = r.get("offer_after")
        after = (ins or 0) - 1 if after is None else after
        cands = [x for x in ws if r["offer_word"] in x["w"] and out_time(x["s"]) is not None and x["s"] >= after]
        if cands:
            a = out_time(cands[0]["s"])
            ov.append(dict(type="offer", title=title, sub=sub, at=round(a - 0.2, 2), dur=3.2, y=420) if sub else
                      dict(type="label", text=title, at=round(a - 0.2, 2), dur=3.2, y=470))   # no sub: no empty pill
        else:
            print(f"overlay anchor not found: offer word {r['offer_word']!r}", file=sys.stderr)
    if hook:                       # label box ends at y~412, the offer card starts at 420: both can show at once
        ov.insert(0, hook)
    ov.append(dict(type="end", title=r.get("end_title", "The Luxury Hobo Bag"), sub=r.get("end_sub", "Tap the link below"),
                   at=round(t - 2.6, 2), dur=2.6, opaque=bool(r.get("burned_captions"))))   # covers the RAW's own captions
    breaks = sorted({round(x[2], 2) for x in raw_to_out} | ({round(review_at, 2), round(review_end, 2)} if review_at is not None
                                                              else set()))
    return segs, audio, ov, t, breaks


def mix_audio(audio, d, out):
    inputs, fc, k = [], [], 0
    for p in audio:
        if p[0] == "slice":
            inputs += ["-i", loc(d, p[1])]
            L = p[3] - p[2]
            fc.append(f"[{k}:a]atrim={p[2]}:{p[3]},asetpts=N/SR/TB,aresample=48000,aformat=channel_layouts=stereo,"
                      f"afade=t=in:d=0.02,afade=t=out:st={max(L - 0.03, 0):.3f}:d=0.03,apad=whole_dur={L:.3f},atrim=0:{L:.3f}[p{k}]")
        elif p[0] == "silence":
            inputs += ["-f", "lavfi", "-t", f"{p[1]:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            fc.append(f"[{k}:a]atrim=0:{p[1]:.3f}[p{k}]")
        else:
            inputs += ["-i", loc(d, p[1])]
            fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={p[2]:.3f},atrim=0:{p[2]:.3f}[p{k}]")
        k += 1
    fc.append("".join(f"[p{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1,loudnorm=I=-16[o]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[o]",
                    "-y", out], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("remix")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = json.load(open(a.remix))
    d = os.path.dirname(os.path.abspath(a.remix))
    segs, audio, ov, total, breaks = build(r, d)
    name = os.path.splitext(os.path.basename(a.remix))[0]
    wav = f"_{name}_audio.wav"
    mix_audio(audio, d, os.path.join(d, wav))
    for s in segs:
        s["mute"] = True
    edl = dict(audio="mute", vo=wav, vo_start=0.0, bed_gain=0.0, segments=segs, overlays=ov, caption_y=r.get("caption_y", 1010),
               keywords=r.get("keywords", []), max_words=r.get("max_words", 4), breaks=breaks)
    if r.get("burned_captions"):
        edl["no_captions"] = [[0, 9999]]
    lj = os.path.join(d, f"_{name}_longform.json")
    json.dump(edl, open(lj, "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "longform.py"), lj, "--out", a.out], check=True)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2))))


if __name__ == "__main__":
    main()
