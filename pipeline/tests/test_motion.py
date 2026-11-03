#!/usr/bin/env python3
"""Motion stills (owner 2026-11-03): a concept static that also ships as a 5 s silent loop. The sheet's rules (concept object
scenes only, the motion line never names the bag, nobody moves, at most 6), the render (our footer stays pixel-still, only the photo
moves), the gate (frozen / an open loop fail) and apply (a failed clip: the still static ships alone).
Run: python3 pipeline/tests/test_motion.py   (needs ffmpeg)"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ai_gen  # noqa: E402
import ideas  # noqa: E402

PR = []


def pr():
    if not PR:
        PR.append(ideas.product_of("Hobo Bag"))
    return PR[0]


def concept(sid, motion=None, **kw):
    s = dict(id=sid, layout="concept", idea="The bag on a cafe table by the window, a latte beside it.", kicker="EARLY BLACK FRIDAY",
             headline="Coffee first. Zipped always.", pill=True,
             scene=dict(kind="object", colour="Black", prompt="The bag on a round marble cafe table by a tall window, a latte beside it."))
    if motion is not None:
        s["motion"] = motion
    s.update(kw)
    return s


def static_problems(stats):
    import novelty
    sheet = dict(product="Hobo Bag", theme="black friday", date="2026-11-03", research=["motion test"], projects=[], statics=stats)
    real = novelty.load
    novelty.load = lambda *a, **k: {"products": {}}
    try:
        P, W = ideas.check(copy.deepcopy(sheet), pr(), n_projects=0, n_statics=len(stats))
    finally:
        novelty.load = real
    return [p for p in P if "motion" in p], W


def test_the_sheet_rules():
    ok = "steam curls up from the latte, sunlight flickers softly through the window"
    P, W = static_problems([concept("S01", ok)])
    assert P == [] and any("motion stills" in w for w in W), (P, W)
    cases = {"an ad": dict(id="S01", layout="ad", format="bold_poster", idea="an idea of one sentence", words=["HALF PRICE."],
                           scene=dict(colour="Black", prompt="The bag on a calm backdrop."), motion=ok),
             "the bag": concept("S01", "the bag sways gently while steam rises from the latte"),
             "a person": concept("S01", "a woman's hand reaches for the cup while steam rises"),
             "too short": concept("S01", "steam"),
             "overlay": concept("S01", ok, style="overlay")}
    want = {"an ad": "only a concept", "the bag": "without naming the bag", "a person": "nobody", "too short": "in a sentence",
            "overlay": "footer"}
    for k, s in cases.items():
        P, _ = static_problems([s])
        assert any(want[k] in p for p in P), (k, P)
    P, _ = static_problems([concept(f"S{k:02d}", ok, headline=f"Line number {k}.") for k in range(1, 8)])
    assert any("at most 6" in p for p in P), P


def _clip(path, seconds=3, still=False, loop=True):
    """A square test clip: a moving gradient (or a still frame), whose last frame is its first when loop."""
    src = "color=c=0x806040:s=540x540:d=%d" % seconds if still else "testsrc2=s=540x540:d=%d:r=24" % seconds
    vf = "format=yuv420p" if still or not loop else "format=yuv420p,reverse"   # (testsrc2 reversed still moves; the seam test uses
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-vf", vf, "-c:v", "libx264", path], check=True)  # its own clip)
    return path


def test_the_render_keeps_the_footer_still():
    import brand_statics as bs
    from PIL import Image
    import numpy as np
    d = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(d, "ai", "clips"))
        Image.new("RGB", (1024, 1024), (120, 90, 60)).save(os.path.join(d, "ai", "AS01.png"))
        _clip(os.path.join(d, "ai", "clips", "AM01_c.mp4"))
        ad = dict(name="x", layout="concept", photo="ai/AS01.png", kicker="EARLY BLACK FRIDAY", headline="Coffee first. Zipped always.",
                  pct=50, motion=dict(id="AM01", file="ai/clips/AM01_c.mp4", seconds=3))
        dest = os.path.join(d, "x_motion.mp4")
        bs.render_motion(dict(ad), d, os.path.join(d, "ai", "clips", "AM01_c.mp4"), dest, 3)
        info = ai_gen.ffprobe(dest)
        assert info and abs(info["dur"] - 3) < 0.2, info
        fr = ai_gen.grab(dest, [0.2, 1.4, 2.6], os.path.join(d, "f"), "m")
        ims = [np.asarray(Image.open(f).convert("L"), dtype=float) for f in fr]
        assert ims[0].shape == (1350, 1080), ims[0].shape
        g = dict(ad)
        bs.render(g, d)
        top = g["_geom"]["ph_h"] - 80                                   # (the photo part, above its melt into the footer)
        assert np.abs(ims[0][:top] - ims[1][:top]).mean() > 3, "the photo part does not move"
        foot = g["_geom"]["ph_h"] + 10
        assert np.abs(ims[0][foot:] - ims[2][foot:]).mean() < 1.0, "the footer moves"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_the_gate_and_apply():
    d = tempfile.mkdtemp()
    try:
        r = ai_gen.gate_motion(_clip(os.path.join(d, "still.mp4"), 4, still=True), os.path.join(d, "t"))
        assert "frozen (no motion)" in r["problems"], r
        r = ai_gen.gate_motion(_clip(os.path.join(d, "open.mp4"), 4, loop=False), os.path.join(d, "t"))
        assert any("loop does not close" in p for p in r["problems"]), r
        # apply: a failed motion clip leaves its still static alone
        os.makedirs(os.path.join(d, "ai", "clips"))
        open(os.path.join(d, "ai", "AS01.png"), "wb").write(b"x")
        st = dict(ads=[dict(name="LC_x_S01_concept", layout="concept", photo="ai/AS01.png", ai=dict(id="AS01"),
                            motion=dict(id="AM01", file="ai/clips/AM01_c.mp4"), fallback=dict(name="LC_x_S01_native", layout="native"))])
        json.dump(st, open(os.path.join(d, "statics.json"), "w"))
        json.dump(dict(statics=["LC_x_S01_concept"], videos=[]), open(os.path.join(d, "plan.json"), "w"))
        json.dump(dict(stills=[dict(id="AS01", use="static")], clips=[dict(id="AM01", use="motion", start="AS01")]),
                  open(os.path.join(d, "ai_needed.json"), "w"))
        json.dump(dict(stills=dict(AS01=dict(ok=True)), clips=dict(AM01=dict(ok=False, problems=["frozen (no motion)"]))),
                  open(ai_gen.gate_path(d), "w"))
        rep = ai_gen.apply(d)
        ad = json.load(open(os.path.join(d, "statics.json")))["ads"][0]
        assert ad["name"] == "LC_x_S01_concept" and "motion" not in ad and rep["motion_dropped"] == ["LC_x_S01_concept"], (ad, rep)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_the_prompt_names_only_what_moves():
    p = ai_gen.motion_still_prompt("steam curls up from the latte.", "handbag")
    assert "steam curls up from the latte." in p and "handbag stays perfectly still" in p and "No people" in p
    assert ai_gen.MOTION["params"]["aspect_ratio"] == "1:1" and ai_gen.MOTION["cost"] < 10


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print("ok  ", name)
        except Exception as e:  # noqa: BLE001
            fails += 1
            print("FAIL", name, type(e).__name__, e)
    print(("all passed (%d/%d)" % (len(tests), len(tests))) if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)
