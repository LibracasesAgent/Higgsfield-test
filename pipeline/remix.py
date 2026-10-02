#!/usr/bin/env python3
"""Winner variation: re-edit a textless RAW winner into a new 50-90 s ad (for longform.py).

  cold open (a strong line from later in the RAW)  ->  RAW from the top  ->  real-review section
  (narrated, verbatim review cards over real B-roll) inserted before the offer  ->  RAW offer + CTA  ->  end card

  python3 pipeline/remix.py remix.json --out ad.mp4

remix.json (paths relative to the JSON):
{
  "raw": "raw94_H4.mp4",
  "cold_open": [12.4, 16.1],          # seconds in the RAW used as the hook (also kept in place later)
  "start": 0.0, "end": null,          # RAW range used for the body
  "cut": [[a, b], ...],               # optional RAW ranges to drop (repeats, dead air)
  "insert_at": 44.3,                  # RAW time where the review section goes (before the offer)
  "reviews": {"vo": "vo_reviews.mp3", "cards": [{"n": 7, "word": "carol"}, ...], "broll": [[src, start], ...]},
  "burned_captions": false,           # RAW already has captions: skip ours
  "labels": [{"text": "REASON ONE", "word": "one", "after": 8.0}],   # optional number labels (RAW times)
  "offer_word": "50", "end_title": "The Luxury Hobo Bag", "keywords": [...]
}
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True).stdout)


def words(path):
    j = path.rsplit(".", 1)[0] + "_words.json"
    if os.path.exists(j):
        return json.load(open(j))
    from faster_whisper import WhisperModel
    m = WhisperModel("small.en", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(path, word_timestamps=True)
    ws = [dict(w=w.word.strip(), s=round(w.start, 2), e=round(w.end, 2)) for s in segs for w in s.words]
    json.dump(ws, open(j, "w"))
    return ws


def build(r, d):
    raw = r["raw"]
    R = dur(os.path.join(d, raw))
    start, end = r.get("start", 0.0), r.get("end") or R
    cuts = sorted(r.get("cut", []))
    ins = r.get("insert_at")
    # RAW body pieces (RAW-time ranges), split at the insertion point and around cuts
    pieces, t = [], start
    for a, b in cuts + [[end, end]]:
        if a > t:
            pieces.append([t, min(a, end)])
        t = max(t, b)
    body = []
    for a, b in pieces:
        if ins and a < ins < b:
            body += [[a, ins], "REVIEWS", [ins, b]]
        else:
            body.append([a, b])
    if ins and "REVIEWS" not in body:
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
    if co:
        raw_seg(co[0], co[1])
        ov.append(dict(type="label", text=r.get("hook_label", "WAIT FOR IT"), at=0.1, dur=min(1.6, co[1] - co[0]), y=300))
    review_at = None
    for p in body:
        if p == "REVIEWS":
            rv = r["reviews"]
            L = dur(os.path.join(d, rv["vo"])) + 0.4
            review_at = t
            br = rv["broll"]
            for k, (src, st) in enumerate(br):
                segs.append(dict(src=src, start=st, dur=round(L / len(br), 3), mute=True))
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
        vw = words(os.path.join(d, rv["vo"]))
        L = dur(os.path.join(d, rv["vo"]))
        starts = []
        for c in rv["cards"]:
            s0 = next((x["s"] for x in vw if x["w"].lower().strip(".,:").startswith(c["word"])), None)
            starts.append(0.2 if s0 is None else s0)
        for k, c in enumerate(rv["cards"]):
            a = review_at + 0.1 + starts[k]
            b = review_at + 0.1 + (starts[k + 1] if k + 1 < len(starts) else L + 0.2)
            ov.append(dict(type="review", n=c["n"], at=round(a, 2), dur=round(b - a, 2), y=330))
    # number labels and offer card from the RAW transcript
    ws = words(os.path.join(d, raw))
    for lb in r.get("labels", []):
        w0 = next((x for x in ws if x["s"] >= lb.get("after", 0) and x["w"].lower().strip(".,") == lb["word"]), None)
        if w0 and out_time(w0["s"]) is not None:
            ov.append(dict(type="label", text=lb["text"], at=round(out_time(w0["s"]), 2), dur=1.4, y=300))
    if r.get("offer_word"):
        cands = [x for x in ws if r["offer_word"] in x["w"] and out_time(x["s"]) is not None and x["s"] >= r.get("offer_after", (ins or 0) - 1)]
        if cands:
            a = out_time(cands[0]["s"])
            ov.append(dict(type="offer", title="50% OFF", sub="+ FREE MATCHING WALLET", at=round(a - 0.2, 2), dur=3.2, y=420))
    ov.append(dict(type="end", title=r.get("end_title", "The Luxury Hobo Bag"), sub="Tap the link below",
                   at=round(t - 2.6, 2), dur=2.6))
    return segs, audio, ov, t


def mix_audio(audio, d, out):
    inputs, fc, k = [], [], 0
    for p in audio:
        if p[0] == "slice":
            inputs += ["-i", os.path.join(d, p[1])]
            L = p[3] - p[2]
            fc.append(f"[{k}:a]atrim={p[2]}:{p[3]},asetpts=N/SR/TB,aresample=48000,aformat=channel_layouts=stereo,"
                      f"afade=t=in:d=0.02,afade=t=out:st={max(L - 0.03, 0):.3f}:d=0.03,apad=whole_dur={L:.3f},atrim=0:{L:.3f}[p{k}]")
        elif p[0] == "silence":
            inputs += ["-f", "lavfi", "-t", f"{p[1]:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            fc.append(f"[{k}:a]atrim=0:{p[1]:.3f}[p{k}]")
        else:
            inputs += ["-i", os.path.join(d, p[1])]
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
    segs, audio, ov, total = build(r, d)
    name = os.path.splitext(os.path.basename(a.remix))[0]
    wav = f"_{name}_audio.wav"
    mix_audio(audio, d, os.path.join(d, wav))
    for s in segs:
        s["mute"] = True
    edl = dict(audio="mute", vo=wav, vo_start=0.0, bed_gain=0.0, segments=segs, overlays=ov, caption_y=r.get("caption_y", 1010),
               keywords=r.get("keywords", []), max_words=r.get("max_words", 4))
    if r.get("burned_captions"):
        edl["no_captions"] = [[0, 9999]]
    lj = os.path.join(d, f"_{name}_longform.json")
    json.dump(edl, open(lj, "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "longform.py"), lj, "--out", a.out], check=True)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2))))


if __name__ == "__main__":
    main()
