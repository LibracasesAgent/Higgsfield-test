#!/usr/bin/env python3
"""Tests of the strategist step (ideas.py): the sheet check, the sheet -> scripts conversion, the concept static layout.

  python3 pipeline/tests/test_ideas.py      # no network: the committed Black Friday sheet (B014) is the fixture
"""
import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import ideas  # noqa: E402

SHEET = os.path.join(HERE, "..", "recipes", "daily", "2026-10-21", "hobo-bag-b014", "ideas.json")


def sheet():
    return json.load(open(SHEET))


def without_own_batch():
    """The sheet's own batch (B014) is in the novelty log once uploaded: check it against the log as it was before that batch."""
    import novelty
    real = novelty.load

    def load(*a, **k):
        log = copy.deepcopy(real(*a, **k))
        for p_ in log["products"].values():
            p_["batches"] = [b for b in p_.get("batches") or [] if "B014" not in str(b.get("name") or "")]
        return log
    novelty.load = load
    return real


def test_the_committed_sheet_passes_its_own_check():
    import novelty
    real = without_own_batch()
    try:
        pr = ideas.product_of("Hobo Bag")
        P, W = ideas.check(sheet(), pr, 4, 20)
    finally:
        novelty.load = real
    assert not P, P


def test_check_stops_a_first_person_script_a_missing_picture_and_a_face():
    pr = ideas.product_of("Hobo Bag")
    s = sheet()
    s["projects"][0]["chapters"][0]["text"] = "I love how my bag keeps everything in one place. Nothing sinks to the bottom."
    s["projects"][1]["chapters"][1]["show"] = []
    s["statics"][0]["scene"]["prompt"] += " A smiling woman looks at the camera, her face in the light."
    s["projects"][2]["hooks"][0]["text"] = " ".join(["word"] * 16)
    P, _ = ideas.check(s, pr, 4, 20)
    txt = "\n".join(P)
    assert "first person" in txt and "show:" in txt and "S01" in txt and "H1: 16 words" in txt, txt
    s2 = sheet()
    s2["statics"][5]["scene"]["prompt"] = s2["statics"][5]["scene"]["prompt"]       # 'no head or face' negations are fine
    assert not any(x.startswith("S06") for x in ideas.check(s2, pr, 4, 20)[0])


def test_check_wants_the_offer_last_and_enough_words():
    pr = ideas.product_of("Hobo Bag")
    s = sheet()
    s["projects"][0]["chapters"][-1]["text"] = "Fifty percent off the Hobo Bag."
    s["projects"][1]["chapters"] = s["projects"][1]["chapters"][:5] + [s["projects"][1]["chapters"][-1]]
    P, _ = ideas.check(s, pr, 4, 20)
    txt = "\n".join(P)
    assert "Tap the link below" in txt and "words in all" in txt, txt


def test_scripts_are_what_make_batch_builds_boards_from():
    pr = ideas.product_of("Hobo Bag")
    sc = ideas.scripts(sheet(), pr, 4)
    assert [x["angle"] for x in sc] == ["packout", "behind", "giftcheck", "fivechecks"]
    s = sc[3]
    assert len(s["alt_hooks"]) == 3 and s["hook"]["text"].startswith("Do not buy a bag")
    assert [c["number"] for c in s["chapters"] if c["number"]] == [1, 2, 3, 4, 5]
    assert s["chapters"][-1]["kind"] == "offer" and s["offer"] and s["offer"]["word"] == "50"
    assert all(c["show"] and 2 <= len(c["shot_kw"]) <= 4 for c in s["chapters"]), [c["shot_kw"] for c in s["chapters"]]
    assert s["numbers"] == [5], s["numbers"]                                         # ('five things': a count the video shows)
    assert 170 <= s["words"] <= 285 and s["from_sheet"]


def test_concept_layout_puts_the_words_in_a_footer_never_on_the_photo():
    import brand_statics as bs
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:
        Image.new("RGB", (896, 1120), (120, 90, 70)).save(os.path.join(d, "s.png"))      # a plain scene: no face, nothing to find
        a = dict(layout="concept", photo="s.png", size=[1080, 1350], headline="Everything fits.", kicker="BLACK FRIDAY", pct=50)
        im = bs.render(a, d)
        assert im.size == (1080, 1350)
        top = im.crop((0, 0, 1080, 800)).resize((8, 8)).getpixel((4, 4))
        assert abs(top[0] - 120) < 25, top                                               # (the photo's own colour above the footer)
        red = lambda box: sum(1 for px in im.crop(box).getdata() if px[0] > 180 and px[1] < 60 and px[2] < 70)   # noqa: E731  (the offer pill)
        assert red((0, 0, 1080, 1040)) == 0 and red((0, 1040, 1080, 1350)) > 500        # (the words, the pill: only in the footer)
        a2 = dict(a, where="top")
        assert bs.render(a2, d).size == (1080, 1350)
        bare = dict(layout="concept", photo="s.png", size=[1080, 1350])
        assert bs.render(bare, d).size == (1080, 1350)                                   # no words: the photo alone


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
