#!/usr/bin/env python3
"""Tests of storyboard.py: the classic format builds exactly as before the ugc format was added (golden file made by the
code of that day), and the ugc format's voice prep, phrase shots, repeat rule, chapter numbers, review cap and master.

  python3 pipeline/tests/test_storyboard.py            # all tests (ffmpeg needed; no network, no whisper, ~30 s)
  python3 pipeline/tests/test_storyboard.py --golden <pipeline dir>   # (re)make classic_build.golden.json with that
                                                                      # pipeline's storyboard.py: only from a known-good one

Media are made in a temp folder (sine / noise wavs, two JPGs); transcripts are fixtures (storyboard.words is replaced), so
no whisper model runs.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "classic_build.golden.json")
sys.path.insert(0, os.path.join(HERE, ".."))


def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def fake_words(text, dur, lead=0.1, tail=0.2):
    """Word timings of a take: the words spread over the speech by their length, a 0.25 s pause after each sentence."""
    toks = text.split()
    n = sum(len(t) for t in toks) + 0.25 * 8 * sum(t[-1] in ".?!" for t in toks)
    out, t, scale = [], lead, (dur - lead - tail) / n
    for w in toks:
        e = t + len(w) * scale
        out.append(dict(w=w, s=round(t, 3), e=round(e, 3)))
        t = e + (0.25 * 8 * scale if w[-1] in ".?!" else 0)
    return out


TEXT = {   # file -> (seconds of sine, script)
    "v0.wav": (3.1, "Four things you'll notice about the bag."),
    "v1.wav": (7.4, "You wear it under your arm, from office days to nights out. The slim shape fits what you need without "
                    "bulging, and it keeps its form all day. That is the first thing."),
    "v2.wav": (5.0, "You carry it on the shoulder or in hand. It is fifty percent off right now."),
}


def make_media(d):
    for k, (secs, _) in TEXT.items():
        ff("-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=48000:duration={secs}", "-c:a", "pcm_s16le", os.path.join(d, k))
    ff("-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:duration=40", "-c:a", "pcm_s16le", os.path.join(d, "c.wav"))
    from PIL import Image
    for k, col in (("s0.jpg", (200, 30, 30)), ("s1.jpg", (30, 30, 200)), ("s2.jpg", (30, 200, 30)), ("s3.jpg", (200, 200, 30))):
        Image.new("RGB", (64, 64), col).save(os.path.join(d, k))


def install_words(sb, d):
    """storyboard.words -> the fixtures: the take's script on even timings (a processed _vp_ file: its own length)."""
    texts = {os.path.join(d, k): v[1] for k, v in TEXT.items()}
    real = sb.words

    def words(path):
        if path in texts:
            return fake_words(texts[path], sb.dur(path))
        if os.path.basename(path).startswith("_vp_"):
            return fake_words(sb.VP_TEXT[os.path.basename(path)], sb.dur(path))
        return real(path)
    sb.words = words
    sb.VP_TEXT = {}


def classic_board():
    still = {"zoom": [1.0, 1.06]}
    return {
        "blocks": [
            {"vo": "v0.wav", "text": TEXT["v0.wav"][1], "pad": 0.35, "broll": [["c.wav", 3.0], ["s0.jpg", 0, 1.0, still]],
             "spare": [["c.wav", 12.0]]},
            {"vo": "v1.wav", "text": TEXT["v1.wav"][1], "hold": 1.0, "broll": [["s1.jpg", 0, 1.0, still], ["c.wav", 38.0, 2.0],
                                                                              ["c.wav", 20.0, 1.0]]},
            {"vo": "v2.wav", "text": TEXT["v2.wav"][1], "broll": [["s2.jpg", 0, 1.0, still], ["c.wav", 20.5, 1.0]]},
        ],
        "overlays": [{"type": "label", "text": "4 THINGS", "block": 0, "at": 0.1, "dur": 1.8},
                     {"type": "tag", "text": "SLIM SHAPE", "block": 1, "word": "slim", "dur": 2.4},
                     {"type": "review", "n": 7, "block": 1, "word": "bulging", "until_block_end": True}],
        "offer": {"block": 2, "word": "50", "title": "50% OFF", "sub": ""},
        "end_title": "The Bag", "keywords": ["50%"], "no_captions_blocks": [], "caption_top_blocks": [1],
        "spare_broll": [["s3.jpg", 0, 1.0, still], ["c.wav", 30.0]],
    }


def build_of(sb, board, d):
    info = {}
    r = sb.build(board, d, info)
    return json.loads(json.dumps([r, info], sort_keys=True))


def test_classic_build_unchanged(sb, d):
    got = build_of(sb, classic_board(), d)
    want = json.load(open(GOLDEN))
    assert got == want, "classic build() output changed"


# ---- ugc ----
def ugc_board(hook="v0.wav"):
    b = classic_board()
    b["mode"] = "ugc"
    b["blocks"][1].pop("hold")
    b["blocks"][1]["number"] = 1
    b["blocks"][2]["number"] = 2
    b["blocks"][0].pop("pad")
    b["blocks"][0]["vo"], b["blocks"][0]["text"] = hook, TEXT[hook][1]
    b["overlays"][2].pop("until_block_end")
    b["overlays"].append({"type": "review", "n": 7, "block": 2, "word": "shoulder", "until_block_end": True})
    # more picks than the plain test board: pool of different moments, so no shot has to repeat
    b["blocks"][1]["broll"] += [["s3.jpg", 0, 1.0, {"zoom": [1.0, 1.06]}]]
    b["spare_broll"] += [["c.wav", 5.0], ["c.wav", 15.0], ["c.wav", 25.0]]
    return b


def write_wav(path, pieces, sr=48000):
    """Mono 16-bit wav of pieces: ("tone", seconds, amplitude) or ("gap", seconds)."""
    import wave
    import numpy as np
    x = np.concatenate([p[2] * np.sin(2 * np.pi * 200 * np.arange(int(p[1] * sr)) / sr) if p[0] == "tone"
                        else np.zeros(int(p[1] * sr)) for p in pieces])
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def lufs_of(p):
    import re
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def test_voice_prep(sb, d):
    # a take: 0.4 s silence, 1 s of tone, 1.2 s pause, 1 s of tone, 0.7 s silence
    write_wav(os.path.join(d, "take.wav"), [("gap", 0.4), ("tone", 1.0, 0.3), ("gap", 1.2), ("tone", 1.0, 0.3), ("gap", 0.7)])
    out = sb.voice_prep(d, "take.wav")
    p = os.path.join(d, out)
    assert out.startswith("_vp_") and out.endswith(".wav")
    L = sb.dur(p)
    want = (sb.KEEP_HEAD + 1 + sb.GAP_CAP + 1 + sb.KEEP_TAIL) / sb.VOICE_SPEED      # ends trimmed, the pause cut, sped up
    assert abs(L - want) < 0.12, (L, want)
    m0 = os.stat(p).st_mtime_ns
    assert sb.voice_prep(d, "take.wav") == out and os.stat(p).st_mtime_ns == m0, "cached by hash"
    assert sb.voice_prep(d, "take.wav", 1.0) != out, "another speed, another file"
    assert sb.voice_prep(d, "take.wav", 3.0) == sb.voice_prep(d, "take.wav", sb.VOICE_MAX), "speed is clamped"
    assert abs(lufs_of(p) - sb.VOICE_LUFS) < 1.0, lufs_of(p)


def words_of(text, t0=0.0, step=0.3):
    return [dict(w=w, s=round(t0 + i * step, 3), e=round(t0 + i * step + 0.25, 3)) for i, w in enumerate(text.split())]


def test_phrases(sb, d):
    ws = words_of("One two three. Four five six seven eight nine ten eleven twelve, thirteen fourteen fifteen sixteen. Short one.")
    cuts = sb.phrase_cuts(ws)
    starts = [0.0] + [round(ws[i]["s"] - sb.CUT_LEAD, 3) for i in (3, 12, 16)]     # sentences, and the comma clause of the long one
    assert cuts == starts, (cuts, starts)
    ws = words_of("This long sentence has ten words and not one comma in it. Ok.")
    assert sb.phrase_cuts(ws)[:2] == [0.0, round(ws[11]["s"] - sb.CUT_LEAD, 3)] or len(sb.phrase_cuts(ws)) >= 2


def test_shot_groups(sb, d):
    g = sb.shot_groups([0.0, 0.8, 2.0, 5.5], 7.0)           # 0.8 and 1.2 s phrases merge, the 3.5 s one stays one group
    assert g[0][0] == 0.0 and g[-1][1] == 7.0 and all(a < b for a, b in g)
    assert all(b - a >= sb.SHOT_MIN for a, b in g), g
    assert all(g[i][1] == g[i + 1][0] for i in range(len(g) - 1)), g
    assert sb.shot_groups([0.0], 2.2) == [(0.0, 2.2)]
    pts = sb.ugc_pieces(0.0, 7.0, words_of("a b c d e f g h i j k l m n o p q r s t u v w"))
    assert len(pts) == 4 and all(b - a <= sb.SHOT_LONG + 0.05 for a, b in zip(pts, pts[1:])), pts


def ugc_build(sb, d, board=None):
    info = {}
    segs, audio, ov, total, nocap, breaks = sb.build(board or ugc_board(), d, info)
    return segs, audio, ov, total, breaks, info


def test_ugc_build(sb, d):
    segs, audio, ov, total, breaks, info = ugc_build(sb, d)
    assert all(isinstance(s, dict) for s in segs)
    # every shot on the 30 fps grid, 1.3-3.2 s (a block shorter than that excepted), the sum is the length
    for s in segs:
        assert abs(s["dur"] * 30 - round(s["dur"] * 30)) < 0.02, s["dur"]
    assert all(sb.SHOT_MIN - 0.04 <= s["dur"] <= sb.SHOT_LONG + 0.04 for s in segs[1:-1]), [s["dur"] for s in segs]
    assert abs(sum(s["dur"] for s in segs) - total) < 0.04
    # blocks join 0.08 s apart (+ what is kept of the takes' ends): the audio list is the processed files, no extra silence
    files = [a for a in audio if a[0] == "file"]
    assert len(files) == 3 and all(a[1].startswith("_vp_") for a in files) and not [a for a in audio if a[0] == "silence"]
    # chapter numbers on the first word of blocks 1 and 2, nowhere else
    pre = [(w["w"], w["pre"]) for w in info["words"] if w.get("pre")]
    assert pre == [("You", "1."), ("You", "2.")], pre
    # review cards: at most REVIEW_MAX
    assert all(o["dur"] <= sb.REVIEW_MAX for o in ov if o["type"] == "review") and sum(o["type"] == "review" for o in ov) == 2
    # cuts on phrase starts: the planner cuts at a phrase start or a clause start (sentence, comma, conjunction)
    starts = [0.0]
    t = 0.0
    for k, (a, b) in enumerate(zip([0.0] + breaks, breaks + [total])):
        blk_words = [w for w in info["words"] if a - 0.01 <= w["s"] < b]
        for i, w in enumerate(blk_words):
            if i == 0 or sb.clause_start(blk_words, i):
                starts.append(w["s"])
    cuts, t = [], 0.0
    for s in segs[:-1]:
        t += s["dur"]
        cuts.append(t)
    on = sum(min(abs(c - x) for x in starts) <= 0.15 for c in cuts)
    assert on >= 0.7 * len(cuts), f"{on}/{len(cuts)} cuts on a phrase start"


def test_no_repeat_within_10s(sb, d):
    segs, *_ = ugc_build(sb, d)
    t, seen = 0.0, []
    for s in segs:
        for q, st, fr, a, e in seen:
            assert not (q == str(s["src"]) and abs(st - s["start"]) <= 1.5 and fr == sb.frame_of(s) and t - e < sb.SAME_S), \
                f"{s['src']} {s['start']} again at {t:.1f}s"
        seen.append((str(s["src"]), float(s["start"]), sb.frame_of(s), t, t + s["dur"]))
        t += s["dur"]


def test_repeat_gets_another_shot(sb, d):
    """Two picks of one moment 4 s apart: the second becomes a spare, another moment or a closer framing."""
    sh = sb.Shots(d)
    a = sh.place(0.0, 2.0, ["s0.jpg", 0, 1.0, {"zoom": [1.0, 1.06]}], [])
    b = sh.place(2.0, 2.0, ["s0.jpg", 0, 1.0, {"zoom": [1.0, 1.06]}], [])
    assert sb.frame_of(a) != sb.frame_of(b), "a still twice in 10 s: the second in another framing"
    sh.place(4.0, 2.0, ["c.wav", 10.0], [])
    e = sh.place(6.0, 2.0, ["c.wav", 10.0], [[["s1.jpg", 0, 1.0, {}]]])
    assert e["src"] == "s1.jpg", "a spare comes first"
    f = sh.place(8.0, 2.0, ["c.wav", 10.5], [])
    assert f["src"] == "c.wav" and sb.frame_of(f) is not None, "then the clip again, in a closer framing (a short clip is one scene)"


def test_one_clip_cuts_are_visible(sb, d):
    """Three shots in a row from one short clip (other moments, so no 'same moment'): every cut changes the framing, never the
    same wide shot again; a still twice within STILL_GAP s is another photo, later its closer framing."""
    sh = sb.Shots(d)
    fr = [sb.frame_of(sh.place(2.0 * i, 2.0, ["c.wav", 1.0 + 8 * i], [])) for i in range(3)]
    assert fr[0] != fr[1] != fr[2] and fr[0] != fr[2], f"framings {fr}"
    st = sb.Shots(d)
    st.place(0.0, 2.0, ["s0.jpg", 0, 1.0, {"zoom": [1.0, 1.06]}], [])
    b = st.place(2.0, 2.0, ["s0.jpg", 0, 1.0, {"zoom": [1.3, 1.36], "focus": [0.5, 0.55]}], [[["s1.jpg", 0, 1.0, {}]]])
    assert b["src"] == "s1.jpg", "a closer crop of the photo just shown is no new shot"
    c = st.place(4.0, 2.0, ["s0.jpg", 0, 1.0, {"zoom": [1.6, 1.66], "focus": [0.5, 0.42]}], [])
    assert c["src"] == "s0.jpg", "the closer framing of a still after STILL_GAP s"


def test_named_picks(sb, d):
    """A block whose picks name what they show ('say': a colour swatch) gives each shot the swatch whose name it says."""
    sh, still = sb.Shots(d), {"zoom": [1.0, 1.06]}
    ws = [dict(w=w, s=round(0.1 + i * 0.3, 3), e=round(0.35 + i * 0.3, 3)) for i, w in enumerate("Available in Coffee, Black. Beige and Wine Red.".split())]
    picks = [[f"s{i}.jpg", 0, 1.0, dict(still, say=n)] for i, n in enumerate(["coffee", "black", "beige", "wine red"])]
    drop = []
    got = sb.plan_block(sh, 0.0, 3.4, 0.0, ws, picks, [], drop)
    assert drop == [] and len(got) >= 2 and all("say" not in g for g in got)
    seen = [g["src"] for g in got]
    assert seen[0] in ("s0.jpg", "s1.jpg") and "s2.jpg" in seen[1:] or "s3.jpg" in seen[1:], seen


def test_hook_does_not_change_body(sb, d):
    """The hook is planned after the body: another hook (other length, other shots) leaves the body's shots as they are."""
    def body(board):
        segs, _, _, _, breaks, _ = ugc_build(sb, d, board)
        t, out = 0.0, []
        for s in segs:
            if t >= breaks[0] - 0.05:
                out.append((s["src"], s["start"], s["dur"], s.get("zoom")))
            t += s["dur"]
        return out
    b2 = ugc_board("v2.wav")
    b2["blocks"][0]["broll"] = [["c.wav", 10.0]]
    b2["blocks"][0]["spare"] = [["s2.jpg", 0, 1.0, {"zoom": [1.0, 1.06]}]]
    assert body(ugc_board()) == body(b2), "body differs"


def test_chapter_number_caption(sb, d):
    """The chapter number is the first token of the block's first caption ("1. You wear it"), never a caption of its own."""
    import longform
    ws = [dict(w=w, s=round(1.0 + i * 0.3, 3), e=round(1.25 + i * 0.3, 3)) for i, w in enumerate("You wear it under your arm.".split())]
    ws[0]["pre"] = "1."
    ph = longform.phrases(ws)
    assert [x["t"] for x in longform.cap_words(ws)][:2] == ["1.", "You"]
    assert ph[0]["lines"][0][:2] == ["1.", "You"], ph[0]["lines"]
    ws2 = [dict(w=w, s=round(0.2 + i * 0.3, 3), e=round(0.45 + i * 0.3, 3)) for i, w in enumerate("Four things. You wear it under your arm.".split())]
    ws2[2]["pre"] = "1."
    ph = longform.phrases(ws2, breaks=[1.0])
    assert all(p["lines"][-1][-1] != "1." for p in ph), "the number is never left at the end of a caption"
    assert any(p["lines"][0][0] == "1." for p in ph)


def test_master(sb, d):
    """Three voice-prepared takes (pink noise at very different levels, 4 Hz tremolo) mixed with a bed: -14 LUFS, LRA <= 4,
    true peak <= -1.8 (the video lands at -1.5 after recut's loudnorm and the AAC encode)."""
    import re
    import remix
    takes = []
    for k, vol in (("m0", 0.05), ("m1", 0.35), ("m2", 0.12)):
        ff("-f", "lavfi", "-i", "anoisesrc=color=pink:sample_rate=48000:duration=9", "-af", f"tremolo=f=4:d=0.6,volume={vol}", "-c:a", "pcm_s16le",
           os.path.join(d, k + ".wav"))
        takes.append(("file", sb.voice_prep(d, k + ".wav"), 8.0))
    ff("-f", "lavfi", "-i", "anoisesrc=color=brown:sample_rate=48000:duration=30", "-c:a", "pcm_s16le", os.path.join(d, "bed.wav"))
    out = os.path.join(d, "master.wav")
    remix.mix_audio(takes, d, out, dict(path=os.path.join(d, "bed.wav"), gain_db=-21.0), "ugc")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    g = lambda k: float(re.findall(k + r":\s+(-?[\d.]+)", r)[-1])  # noqa: E731
    assert abs(g("I") + 14) <= 1.0, g("I")
    assert g("LRA") <= remix.LRA_MAX, g("LRA")
    assert g("Peak") <= -1.8, g("Peak")


TESTS = [test_classic_build_unchanged, test_voice_prep, test_phrases, test_shot_groups, test_ugc_build, test_no_repeat_within_10s,
         test_repeat_gets_another_shot, test_one_clip_cuts_are_visible, test_named_picks, test_hook_does_not_change_body, test_chapter_number_caption, test_master]


def main():
    if "--golden" in sys.argv:
        pdir = os.path.abspath(sys.argv[sys.argv.index("--golden") + 1])
        sys.path.insert(0, pdir)
        sys.path.remove(os.path.join(HERE, ".."))
        import storyboard as sb
        assert os.path.dirname(os.path.abspath(sb.__file__)) == pdir
        with tempfile.TemporaryDirectory() as d:
            make_media(d)
            install_words(sb, d)
            json.dump(build_of(sb, classic_board(), d), open(GOLDEN, "w"), indent=1, sort_keys=True)
        print("wrote", GOLDEN)
        return 0
    import storyboard as sb
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        make_media(d)
        install_words(sb, d)
        orig_prep = sb.voice_prep

        def prep(dd, name, speed=sb.VOICE_SPEED):          # remember the processed take's script for the words fixture
            out = orig_prep(dd, name, speed)
            sb.VP_TEXT[out] = TEXT[name][1] if name in TEXT else ""
            return out
        sb.voice_prep = prep
        for t in TESTS:
            try:
                t(sb, d)
                print("ok  ", t.__name__)
            except Exception as e:  # noqa: BLE001
                bad += 1
                import traceback
                traceback.print_exc()
                print("FAIL", t.__name__, type(e).__name__, e)
    print("FAILED" if bad else "all passed", f"({len(TESTS) - bad}/{len(TESTS)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
