#!/usr/bin/env python3
"""Tests of ai_gen.py (AI scene stills / clips plan, budget, apply fallback) and novelty.py (the novelty log).

  python3 pipeline/tests/test_ai_gen.py      # no network, no Higgsfield: plans and files in a temp folder (ffmpeg not needed)
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import ai_gen  # noqa: E402
import novelty  # noqa: E402


def packshots(d, n=3):
    from PIL import Image
    out = []
    for i in range(n):
        p = os.path.join(d, f"pack{i}.jpg")
        im = Image.new("RGB", (400, 400), "white")
        im.paste((90, 50, 30), (100, 150, 300, 260))
        im.save(p)
        out.append(dict(file=p, colour=["Coffee", "Black", "Beige"][i]))
    return out


def plan(d, log, **kw):
    return ai_gen.plan_ai(name="Test Bag", slug="test-bag", refs=packshots(d), n_statics=20, n_clips=8, tts_est=22, seed=1,
                          out=d, log_path=log, **kw)


def test_budget_and_shape():
    with tempfile.TemporaryDirectory() as d:
        p = plan(d, os.path.join(d, "none.json"))
        assert p["est_credits"] <= 100 - 22 - ai_gen.RESERVE + 1e-6, p["est_credits"]
        assert len([s for s in p["stills"] if s["use"] == "static"]) == 8
        assert len(p["clips"]) == 8
        assert all(c["start"] in {s["id"] for s in p["stills"]} for c in p["clips"])
        assert os.path.exists(os.path.join(d, "ai_needed.json"))
        tight = ai_gen.plan_ai(name="Test Bag", slug="test-bag", refs=packshots(d), n_statics=20, n_clips=8, tts_est=22, seed=1,
                               out=d, log_path=os.path.join(d, "none.json"), cap=50)
        assert tight["est_credits"] <= 50 - 22 - ai_gen.RESERVE + 1e-6 and len(tight["clips"]) < 8, tight["budget"]


def test_scenes_rotate_between_batches():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "log.json")
        first = plan(d, log)
        scenes1 = {s["scene"] for s in first["stills"]}
        novelty.record("test-bag", dict(date="2026-10-20", name="a", statics=[dict(scene=x) for x in scenes1], clips=[], videos=[]), log)
        second = plan(d, log)
        scenes2 = {s["scene"] for s in second["stills"]}
        assert len(scenes1 & scenes2) <= 2, scenes1 & scenes2    # 42 scenes, ~16 per batch: two batches share (almost) none
        cols1 = [s["colour"] for s in first["stills"][:3]]
        assert cols1[0] == "Coffee"


def test_no_face_in_prompts_of_worn_scenes():
    lib = ai_gen.library()
    for sc in lib["scenes"]:
        pr = ai_gen.build_prompt(lib, sc, "handbag", "Black", False)
        assert "exact handbag" in pr and "same colour (black)" in pr
        if sc["kind"] != "object":
            assert "no face at all" in pr, sc["id"]


def test_apply_falls_back():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "ai", "clips"))
        need = dict(stills=[dict(id="AS01", use="static", scene="x", kind="object"), dict(id="AV01", use="clip", scene="y", kind="object")],
                    clips=[dict(id="AC01", start="AV01", scene="y", kind="object", tags=[], file="ai/clips/AC01.mp4")], est_credits=1)
        json.dump(need, open(os.path.join(d, "ai_needed.json"), "w"))
        real = {"name": "X_S01_native", "layout": "native", "photo": "photos/a.jpg", "caption": "Real."}
        ai = {"name": "X_S01_scene", "layout": "scene", "photo": "ai/AS01.png", "ai": {"id": "AS01"}, "fallback": real}
        json.dump({"ads": [ai]}, open(os.path.join(d, "statics.json"), "w"))
        json.dump({"statics": ["X_S01_scene"]}, open(os.path.join(d, "plan.json"), "w"))
        spec = {"mode": "ugc", "blocks": [{"vo": "a.mp3", "broll": [["photos/a.jpg", 0, 1.0], ["ai/clips/AC01_c.mp4", 0.0, 1.0], ["clips/b.mp4", 2, 1.0]],
                                           "spare": [["clips/c.mp4", 1, 1.0], ["ai/clips/AC01_c.mp4", 0.0, 1.0]]}], "spare_broll": []}
        json.dump(spec, open(os.path.join(d, "V.json"), "w"))
        rep = ai_gen.apply(d)                               # nothing generated: everything falls back
        st = json.load(open(os.path.join(d, "statics.json")))["ads"]
        assert st[0]["name"] == "X_S01_native" and "ai" not in st[0], st
        assert json.load(open(os.path.join(d, "plan.json")))["statics"] == ["X_S01_native"]
        sp = json.load(open(os.path.join(d, "V.json")))
        assert "AC01" not in json.dumps(sp) and sp["blocks"][0]["broll"][1][0] == "clips/c.mp4", sp
        assert rep["clips_swapped"] == 1 and rep["statics_back"]
        # now the assets pass: a re-apply restores them from the pristine copies
        from PIL import Image
        Image.new("RGB", (50, 50)).save(os.path.join(d, "ai", "AS01.png"))
        open(os.path.join(d, "ai", "clips", "AC01_c.mp4"), "wb").write(b"x")
        ai_gen.save_gate(d, {"stills": {"AS01": {"ok": True}}, "clips": {"AC01": {"ok": True}}})
        rep = ai_gen.apply(d)
        assert json.load(open(os.path.join(d, "statics.json")))["ads"][0]["name"] == "X_S01_scene"
        assert json.load(open(os.path.join(d, "plan.json")))["statics"] == ["X_S01_scene"]
        assert "ai/clips/AC01_c.mp4" in json.dumps(json.load(open(os.path.join(d, "V.json")))) and not rep["clips_swapped"]


def test_novelty_log():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "log.json")
        for i in range(5):
            novelty.record("Hobo Bag", dict(date=f"2026-10-1{i}", name=f"n{i}", statics=[dict(photo=f"p{i}.jpg", scene=f"s{i}")],
                                            clips=[], videos=[dict(hook=f"h{i}")]), log)
        assert novelty.recent("Hobo Bag", "scene", log=novelty.load(log)) == ["s4", "s3", "s2"]     # the last 3 batches
        novelty.record("Hobo Bag", dict(date="2026-10-14", name="n4", statics=[], clips=[], videos=[dict(hook="h4b")]), log)   # same run, later upload
        b = novelty.batches("Hobo Bag", path=log)
        assert len(b) == 5 and len(b[-1]["statics"]) == 1 and len(b[-1]["videos"]) == 2


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for k, f in tests:
        try:
            f()
            print("ok  ", k)
        except Exception as e:  # noqa: BLE001
            fails += 1
            import traceback
            traceback.print_exc()
            print("FAIL", k, type(e).__name__, e)
    print("all passed" if not fails else f"{fails} failed", f"({len(tests) - fails}/{len(tests)})")
    sys.exit(1 if fails else 0)
