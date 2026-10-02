#!/usr/bin/env python3
"""Block-based 30-90 s ad (for longform.py): narration blocks over B-roll plus real clips with their own sound.

  python3 pipeline/storyboard.py board.json --out ad.mp4

board.json (paths relative to the JSON):
{
  "blocks": [
    {"vo": "n_vin1.mp3", "broll": [["vin_clasp_brown.mp4", 0.0], ["vin_details_brown.mp4", 3.5, 1.5]]},
                                   # [src, start, weight?]: the VO length is split over the clips by weight
    {"clip": "vin_becky_testimony.mp4", "range": [5.8, 14.4]},       # real clip with its own audio
    {"clip": "k_h2_brown.mp4", "range": [0, 5], "mute": true},        # silent visual (adds time, no sound)
  ],
  "pad": 0.25,                                       # silence after each VO block
  "overlays": [{"type": "tag", "text": "LOCKABLE ZIPPERS", "block": 0, "word": "lockable", "dur": 2.2},
               {"type": "review", "n": 11, "block": 2, "word": "sarah", "until_block_end": true},
               {"type": "label", "text": "REAL CUSTOMER", "block": 1, "at": 0.2, "dur": 2.0}],
  "offer": {"block": 4, "word": "50"},               # offer card at that word ("fifty" also matches)
  "end_title": "The Vintage Bag", "keywords": [...], "no_captions_blocks": [3]
}
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from remix import dur, mix_audio, words  # noqa: E402


def norm(w):
    return w.lower().strip(".,:;!?\"'")


def build(b, d):
    segs, audio, spans, t = [], [], [], 0.0
    pad = b.get("pad", 0.25)
    for blk in b["blocks"]:
        if "vo" in blk and "vo_range" in blk:     # slice of a longer VO file
            a, e = blk["vo_range"]
            L = e - a + blk.get("pad", pad)
            br = [x if len(x) > 2 else x + [1.0] for x in blk["broll"]]
            tot = sum(x[2] for x in br)
            for src, st, wgt, *ex in br:
                s = dict(src=src, start=st, dur=round(L * wgt / tot, 3), mute=True)
                if ex:
                    s.update(ex[0])
                segs.append(s)
            audio.append(("slice", blk["vo"], a, e))
            audio.append(("silence", blk.get("pad", pad)))
            spans.append((t, L, blk["vo"], a))
        elif "vo" in blk:
            L = dur(os.path.join(d, blk["vo"])) + blk.get("pad", pad)
            br = [x if len(x) > 2 else x + [1.0] for x in blk["broll"]]
            tot = sum(x[2] for x in br)
            for src, st, wgt, *ex in br:
                s = dict(src=src, start=st, dur=round(L * wgt / tot, 3), mute=True)
                if ex:
                    s.update(ex[0])
                segs.append(s)
            audio.append(("file", blk["vo"], L))
            spans.append((t, L, blk["vo"], 0.0))
        else:
            a, e = blk["range"]
            L = e - a
            cut = blk.get("cutaway")          # {"at": 2.8, "src": "...", "start": 3.6}: J-cut to B-roll, clip audio continues
            v = cut["at"] if cut else L
            s = dict(src=blk["clip"], start=a, dur=round(v, 3), mute=True)
            s.update(blk.get("seg", {}))
            segs.append(s)
            if cut:
                segs.append(dict(src=cut["src"], start=cut["start"], dur=round(L - v, 3), mute=True))
            if blk.get("mute"):
                audio.append(("silence", L))
            else:
                audio.append(("slice", blk["clip"], a, e))
            spans.append((t, L, None if blk.get("mute") else blk["clip"], a))
        t += L

    def word_time(k, w, nth=0):
        t0, L, src, off = spans[k]
        if not src:
            return None
        hits = [x["s"] - off for x in words(os.path.join(d, src)) if off <= x["s"] < off + L
                and (norm(x["w"]).startswith(w) or (w == "50" and norm(x["w"]).startswith("fifty")))]
        return t0 + hits[nth] if len(hits) > nth else None

    ov = []
    for o in b.get("overlays", []):
        o = dict(o)
        k = o.pop("block")
        t0, L = spans[k][0], spans[k][1]
        at = word_time(k, o.pop("word"), o.pop("nth", 0)) if "word" in o else t0 + o.pop("at", 0.1)
        if at is None:
            print("overlay anchor not found:", o, file=sys.stderr)
            continue
        if o.pop("until_block_end", False):
            o["dur"] = round(t0 + L - at - 0.1, 2)
        o["at"] = round(at - 0.05, 2)
        o.setdefault("dur", 2.2)
        o.setdefault("y", 330 if o["type"] == "review" else 300)
        ov.append(o)
    if b.get("offer"):
        at = word_time(b["offer"]["block"], b["offer"].get("word", "50"))
        if at is not None:
            ov.append(dict(type="offer", title="50% OFF", sub=b["offer"].get("sub", "+ FREE MATCHING WALLET"),
                           at=round(at - 0.2, 2), dur=3.2, y=420))
    ov.append(dict(type="end", title=b.get("end_title", "The Luxury Hobo Bag"), sub="Tap the link below",
                   at=round(t - 2.6, 2), dur=2.6))
    nocap = [[round(spans[k][0], 2), round(spans[k][0] + spans[k][1], 2)] for k in b.get("no_captions_blocks", [])]
    return segs, audio, ov, t, nocap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    b = json.load(open(a.board))
    d = os.path.dirname(os.path.abspath(a.board))
    segs, audio, ov, total, nocap = build(b, d)
    name = os.path.splitext(os.path.basename(a.board))[0]
    wav = f"_{name}_audio.wav"
    mix_audio(audio, d, os.path.join(d, wav))
    edl = dict(audio="mute", vo=wav, vo_start=0.0, bed_gain=0.0, segments=segs, overlays=ov,
               caption_y=b.get("caption_y", 1010), keywords=b.get("keywords", []), max_words=b.get("max_words", 4), caption_fix=b.get("caption_fix", []))
    if nocap:
        edl["no_captions"] = nocap
    lj = os.path.join(d, f"_{name}_longform.json")
    json.dump(edl, open(lj, "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "longform.py"), lj, "--out", a.out], check=True)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2))))


if __name__ == "__main__":
    main()
