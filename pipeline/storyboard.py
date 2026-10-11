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
  "offer": {"block": 4, "word": "50", "title": "50% OFF", "sub": "+ FREE MATCHING WALLET"},
                                                     # offer card at that word ("fifty" also matches); "" sub: title only
  "end_title": "The Vintage Bag", "end_sub": "Tap the link below", "keywords": [...], "no_captions_blocks": [3],
  "caption_top_blocks": [2],                         # captions in the upper area during these blocks (product detail low)
  "spare_broll": [[src, start], ...],                # unused shots: a VO shot that would run > 4 s is split onto them
  "music": {"seed": 3},                              # music bed (music.py: a client track, else a generated bed); false: none
}
A VO block may carry its script as "text" (else tts_said.json next to the board): captions show the script's words on the
voiceover's word timings, a clip's words from its committed transcript (no transcription of the final mix).
One voice per video: every "vo" block is the brand voice; real people speak only in their own "clip" blocks, each
introduced by the narrator in the block before ("Here's Becky with her new Vintage Bag.").
B-roll that would run past the end of its clip starts earlier (or plays slower), so picture and sound stay in sync.
Pacing: no B-roll shot runs longer than remix.MAX_SHOT (4 s): a longer one is split, its later parts on the block's own
"spare" shots, then the board's spare_broll, never a shot the video shows already (none left: it stays long). A clip block
longer than that (a customer talking) changes framing about every SHOT_TARGET s (wide / closer on the bag / closer on
her, the block's "frames" to override), cut on her pauses, its sound running on; one clip twice in a row gets a closer
framing the second time, so it reads as another shot.
Cadence: the hook block gets at least HOOK_PAD s after its line (the hook finishes before the body starts), the last
block at least END_PAD s (the last sentence finishes, remix.TAIL, before the end card ends the video), a narrator line
right after a customer's clip CLIP_PAD s after her last word (she finishes, a breath, then the next voice); a clip block
whose range starts or ends mid-sentence prints a 'cadence:' line (make_batch render counts it as a QA flag).
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from remix import (MAX_SHOT, STILL, TAIL, cadence, caption_opts, dur, fit, loc, mix_audio, script_words, vo_text,  # noqa: E402
                   words)


TENS = "_ ten twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_word(w):
    """First spoken word of a number: '50' -> 'fifty', '65' -> 'sixty', '15' -> 'fifteen'."""
    if not w.isdigit() or not 10 <= int(w) < 100:
        return None
    return "fifteen" if w == "15" else TENS[int(w) // 10]


def norm(w):
    return w.lower().strip(".,:;!?\"'")


HOOK_PAD = 0.35    # silence after the hook line before the body starts (>= remix.PAUSE with the mp3's own tail)
END_PAD = TAIL + 0.2   # silence after the last line: it finishes before the video ends
CLIP_PAD = 0.5     # silence between a real customer's last word and the narrator's next line (her sentence lands)
SHOT_TARGET = 3.2  # a long clip block (a customer talking) changes framing about this often (Julian: every 3-5 s)
FRAMES = [{}, {"zoom": [1.55, 1.6], "focus": [0.5, 0.74]}, {}, {"zoom": [1.22, 1.26], "focus": [0.5, 0.36]}]
#                 wide -> closer on her hands and the bag -> wide -> closer on her (9:16 talking clip: face above the bag)


def shot_key(x):
    return (str(x[0]), round(float(x[1]), 1))


def broll_segs(d, br, L, spare=None, used=None, own=()):
    """Segments for L s of VO over the picks br ([src, start, weight?, extra?]): L split by weight; a part longer than
    MAX_SHOT continues on spare shots (popped from `spare`, skipping any in `used`; the block's `own` spares, chosen for
    it, even when shown elsewhere once nothing else is left), so no shot runs longer."""
    out = []
    br = [x if len(x) > 2 else x + [1.0] for x in br]
    tot = sum(x[2] for x in br)
    spare, used = (spare if spare is not None else []), (used if used is not None else set())
    for src, st, wgt, *ex in br:
        sd = L * wgt / tot
        parts = [[src, st, ex]]
        while sd / len(parts) > MAX_SHOT + 0.05:
            nxt = next((x for x in spare if shot_key(x) not in used), None) or \
                next((x for x in spare if any(x is y for y in own)), None)
            if nxt is None:
                break
            spare.remove(nxt)
            used.add(shot_key(nxt))
            parts.append([nxt[0], nxt[1], nxt[3:4] if len(nxt) > 3 else []])
        for psrc, pst, pex in parts:
            pd = round(sd / len(parts), 3)
            if not str(psrc).lower().endswith(STILL):
                pst, sp = fit(d, psrc, pst, pd)
                if sp != 1.0:
                    pex = [dict(pex[0] if pex else {}, speed=sp)]
            elif not pex:
                pex = [{"zoom": [1.0, 1.06]}]
            s = dict(src=psrc, start=pst, dur=pd, mute=True)
            if pex:
                s.update(pex[0])
            out.append(s)
    return out


def cut_points(ws, a, e, target=SHOT_TARGET):
    """Picture cuts inside a long clip [a, e] (source seconds) about every `target` s, on a pause between two words
    when there is one near (the sound runs on: only the framing changes), never a piece under 1.6 s."""
    gaps = [(x["e"] + y["s"]) / 2 for x, y in zip(ws, ws[1:]) if a < x["e"] and y["s"] < e and y["s"] - x["e"] >= 0.12]
    cuts, cur = [], a
    while e - cur > MAX_SHOT + 0.1:
        want = target if e - cur >= target + 1.6 else (e - cur) / 2      # the last two pieces share what is left
        near = [g for g in gaps if cur + want - 0.9 <= g <= cur + want + 0.7 and g - cur >= 1.6 and e - g >= 1.6]
        c = min(near, key=lambda g: abs(g - cur - want)) if near else cur + want
        cuts.append(round(c, 3))
        cur = c
    return cuts


def frames_of(blk):
    """Framings a long clip block cycles through (recut zoom + focus): the block's 'frames', else wide -> closer on the
    hands and bag -> closer on the speaker (a 9:16 talking clip: face in the upper half, the bag below)."""
    return blk.get("frames") or FRAMES


def said_words(b, d, spans):
    """What the ad says, in ad seconds: each VO block's script (its 'text', else tts_said.json next to the spec) on the
    word timings of its voiceover file (remix.script_words), each clip block's committed / cached transcript. Words of
    a voiceover the script can't be found for keep the transcript's own."""
    out = []
    for k, blk in enumerate(b["blocks"]):
        t0, L, src, off = spans[k]
        if not src:
            continue
        ws = words(loc(d, src))
        if "vo" in blk:
            txt = blk.get("text") or vo_text(d, blk["vo"])
            if txt and "vo_range" not in blk:
                ws = script_words(txt, ws)
        for w in ws:
            if off - 0.02 <= w["s"] < off + L - 0.05:
                out.append(dict(w=w["w"], s=round(t0 + w["s"] - off, 3), e=round(t0 + min(w["e"], off + L) - off, 3),
                                **({"k": "script"} if w.get("k") == "script" else {})))
    return out


def build(b, d, info=None):
    """-> segs, audio, overlays, total, no-caption windows, block starts. info (a dict) also gets 'words': what is said,
    in ad seconds, with the script's own spelling and punctuation (longform's captions use it instead of transcribing the
    final mix): the VO script on its voiceover's word timings, a clip's committed transcript."""
    segs, audio, spans, leads, t = [], [], [], [], 0.0
    pad = b.get("pad", 0.25)
    used = {shot_key(x) for blk in b["blocks"] for x in blk.get("broll") or []}   # spares never repeat a shot shown
    spare_all = [x for x in b.get("spare_broll") or [] if shot_key(x) not in used]
    last = len(b["blocks"]) - 1
    top = set(b.get("caption_top_blocks") or [])
    clip_tail = None                              # silence after the last word of the clip block just before
    for k, blk in enumerate(b["blocks"]):
        n0 = len(segs)
        bp = blk.get("pad", pad)
        bp = max(bp, HOOK_PAD) if k == 0 and last > 0 else max(bp, END_PAD) if k == last else bp
        # the hook's extra shots come only from its own spares (its versions differ; the body must stay identical)
        own = list(blk.get("spare") or [])
        spare = own + ([] if k == 0 else spare_all)
        # a real customer hands back to the narrator: a breath first (her sentence lands before the next voice starts)
        lead = round(max(CLIP_PAD - clip_tail, 0.0), 2) if "vo" in blk and clip_tail is not None else 0.0
        if lead:
            audio.append(("silence", lead))
        if "vo" in blk and "vo_range" in blk:     # slice of a longer VO file
            a, e = blk["vo_range"]
            L = lead + e - a + bp
            segs += broll_segs(d, blk["broll"], L, spare, used, own)
            audio.append(("slice", blk["vo"], a, e))
            audio.append(("silence", bp))
            spans.append((t, L, blk["vo"], a - lead))
        elif "vo" in blk:
            L = lead + dur(loc(d, blk["vo"])) + bp
            segs += broll_segs(d, blk["broll"], L, spare, used, own)
            audio.append(("file", blk["vo"], L - lead))
            spans.append((t, L, blk["vo"], -lead))
        else:
            a, e = blk["range"]
            L = e - a
            ws_c = [] if blk.get("mute") else words(loc(d, blk["clip"]))
            if not blk.get("mute"):               # a real person's own words: whole sentences only
                for p in cadence(ws_c, a, e, f"block {k} clip"):
                    print("cadence:", p, file=sys.stderr)
            cut = blk.get("cutaway")          # {"at": 2.8, "src": "...", "start": 3.6}: J-cut to B-roll, clip audio continues
            v = cut["at"] if cut else L
            # Pacing (Julian: a new shot every 3-5 s): a long clip changes framing about every SHOT_TARGET s, cut on her
            # pauses; picture and sound stay in sync (each piece starts where the last one ended)
            pts = [] if cut or blk.get("seg") or v <= MAX_SHOT + 0.5 else cut_points(ws_c, a, a + v)
            fr = frames_of(blk)
            for j, (x0, x1) in enumerate(zip([a] + pts, pts + [a + v])):
                s = dict(src=blk["clip"], start=round(x0, 3), dur=round(x1 - x0, 3), mute=True)
                if pts and fr[j % len(fr)]:
                    s.update(fr[j % len(fr)])
                s.update(blk.get("seg", {}))
                segs.append(s)
            if cut:
                segs.append(dict(src=cut["src"], start=cut["start"], dur=round(L - v, 3), mute=True))
            if blk.get("mute"):
                audio.append(("silence", L))
            else:
                audio.append(("slice", blk["clip"], a, e))
            spans.append((t, L, None if blk.get("mute") else blk["clip"], a))
        leads.append(lead)
        clip_tail = None
        if "clip" in blk and not blk.get("mute"):
            heard = [w for w in words(loc(d, blk["clip"])) if blk["range"][0] < w["e"] and w["s"] < blk["range"][1]]
            clip_tail = max(blk["range"][1] - heard[-1]["e"], 0.0) if heard else CLIP_PAD
        if k in top:                              # longform.top_windows: captions up top while these segments play
            for s in segs[n0:]:
                s["caption_pos"] = "top"
        if k:                                     # spares the body used are gone for the next blocks
            spare_all[:] = [x for x in spare_all if shot_key(x) not in used]
        t += L
    for i in range(1, len(segs)):                 # one clip twice in a row (a feature's 2nd moment): a closer framing,
        p_, s_ = segs[i - 1], segs[i]             # so the cut reads as a new shot, not a jump in the same one
        if s_["src"] == p_["src"] and not str(s_["src"]).lower().endswith(STILL) and "zoom" not in s_ and \
                "zoom" not in p_ and "focus" not in s_:
            s_.update(zoom=[1.18, 1.24], focus=[0.5, 0.55])
    if info is not None:
        info["words"] = said_words(b, d, spans)
        info["leads"] = leads

    def word_time(k, w, nth=0):
        t0, L, src, off = spans[k]
        if not src:
            return None
        hits = [x["s"] - off for x in words(loc(d, src)) if off <= x["s"] < off + L
                and (norm(x["w"]).startswith(w) or (num_word(w) and norm(x["w"]).startswith(num_word(w))))]
        return t0 + hits[nth] if len(hits) > nth else None

    ov = []
    for o in b.get("overlays", []):
        o = dict(o)
        k = o.pop("block")
        t0, L = spans[k][0], spans[k][1]
        at = word_time(k, o.pop("word"), o.pop("nth", 0)) if "word" in o else t0 + leads[k] + o.pop("at", 0.1)
        if at is None:
            print("overlay anchor not found:", o, file=sys.stderr)
            continue
        if o.pop("until_block_end", False):
            o["dur"] = round(t0 + L - at - 0.1, 2)
        o["at"] = round(at - 0.05, 2)
        o.setdefault("dur", 2.2)
        o.setdefault("y", 330 if o["type"] == "review" else 300)
        ov.append(o)
    of = b.get("offer")
    if of and of.get("title", "50% OFF"):
        at = word_time(of["block"], str(of.get("word", "50")).lower())
        title, sub = of.get("title", "50% OFF"), of.get("sub", "+ FREE MATCHING WALLET")
        if at is None:
            print("overlay anchor not found: offer", of, file=sys.stderr)
        else:
            ov.append(dict(type="offer", title=title, sub=sub, at=round(at - 0.2, 2), dur=3.2, y=420) if sub else
                      dict(type="label", text=title, at=round(at - 0.2, 2), dur=3.2, y=470))
    ov.append(dict(type="end", title=b.get("end_title", "The Luxury Hobo Bag"), sub=b.get("end_sub", "Tap the link below"),
                   at=round(t - 2.6, 2), dur=2.6))
    nocap = [[round(spans[k][0], 2), round(spans[k][0] + spans[k][1], 2)] for k in b.get("no_captions_blocks", [])]
    return segs, audio, ov, t, nocap, [round(x[0], 2) for x in spans[1:]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    b = json.load(open(a.board))
    d = os.path.dirname(os.path.abspath(a.board))
    info = {}
    segs, audio, ov, total, nocap, breaks = build(b, d, info)
    name = os.path.splitext(os.path.basename(a.board))[0]
    wav = f"_{name}_audio.wav"
    import music
    bed = music.resolve(b.get("music"), d)          # the project's music bed under the voice (none: "music": false)
    mix_audio(audio, d, os.path.join(d, wav), bed)
    if bed:
        print(f"music: {bed['name']} ({bed['kind']}, {bed['gain_db']:.0f} dB under the voice, ducked while someone speaks)",
              file=sys.stderr)
    edl = dict(audio="mute", vo=wav, vo_start=0.0, bed_gain=0.0, segments=segs, overlays=ov, keywords=b.get("keywords", []),
               breaks=breaks, transcript=info.get("words") or [], **caption_opts(b))   # breaks: a caption never runs
    if nocap:                                                                            # across two blocks
        edl["no_captions"] = nocap
    lj = os.path.join(d, f"_{name}_longform.json")
    json.dump(edl, open(lj, "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "longform.py"), lj, "--out", a.out], check=True)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2))))


if __name__ == "__main__":
    main()
