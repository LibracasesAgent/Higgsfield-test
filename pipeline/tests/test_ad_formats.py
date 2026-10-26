#!/usr/bin/env python3
"""The AI-designed statics (layout 'ad', owner 2026-10-26): the format library, the sheet check (Meta's rules, new formats every
batch), the prompt, the words read back, the render. Run: python3 pipeline/tests/test_ad_formats.py"""
import copy
import os
import shutil
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


def ad(sid, fmt, words, prompt="The bag on a calm warm backdrop, soft light from the left, a gentle shadow, nothing else in the frame.", **kw):
    return dict(id=sid, project="P01", layout="ad", format=fmt, idea="an idea of one sentence", words=words,
                scene=dict(colour="Black", prompt=prompt), **kw)


OWN = dict(format_name="Film still with subtitle", people="behind",
           art="A cinematic widescreen film still: black letterbox bars, a moody 35mm frame, real grain, one white subtitle line in the bar.")


def static_problems(stats, log=None, exclude=None):
    """The sheet check's problems about the statics only (the project part of the sheet is the committed B014 one)."""
    import json
    import novelty
    sheet = json.load(open(os.path.join(HERE, "..", "recipes", "daily", "2026-10-21", "hobo-bag-b014", "ideas.json")))
    sheet["statics"] = stats
    real = novelty.load
    novelty.load = lambda *a, **k: copy.deepcopy(log) if log is not None else real(*a, **k)
    try:
        P, _ = ideas.check(sheet, pr(), exclude=exclude)
    finally:
        novelty.load = real
    return [p for p in P if p.startswith(("S0", "statics", "compliance")) and " c" not in p.split(":")[0]]


def test_the_library_holds_the_liked_formats():
    f = ideas.formats()
    liked = sorted(x["liked"] for x in f["formats"].values() if x.get("liked"))
    assert liked == [2, 3, 4, 6, 7, 8], liked
    for x in f["formats"].values():
        assert x["people"] in ideas.AD_PEOPLE and len(x["art"]) >= 60 and x["words"] > 0 and x["tag"].isalnum(), x["id"]
    assert any("interface" in m for m in f["meta"])


def test_a_clean_ad_set_passes():
    empty = {"products": {}}
    stats = [ad("S01", "magazine_cover", ["LIBRA", "THE ZIP-TOP ISSUE", "EARLY BLACK FRIDAY: 50% OFF"]),
             ad("S02", "bold_poster", ["HALF PRICE.", "Early Black Friday"]),
             ad("S03", "film_still", ["Last train. Phone in the side zip."], **OWN)]
    P = [p for p in static_problems(stats, empty) if not p.startswith("compliance")]
    assert P == [], P


def test_the_check_refuses_what_meta_or_the_bag_would_not_allow():
    empty = {"products": {}}
    cases = {
        "fake interface": ad("S01", "bold_poster", ["HALF PRICE."], prompt="A big red play button in the middle of the frame, the bag below it, calm."),
        "publication": ad("S01", "magazine_cover", ["VOGUE", "THE ZIP ISSUE"]),
        "closed": ad("S01", "flat_lay", ["Everything fits."], prompt="Top-down on oak, the bag unzipped with a wallet and keys inside the bag."),
        "prices": ad("S01", "bold_poster", ["Only $52.50"]),
        "face": ad("S01", "pov_behind", ["POV: zipped"], prompt="A woman smiling at the camera on a busy street at dusk, the bag on her shoulder."),
        "words": ad("S01", "bold_poster", ["HALF PRICE TODAY ON THE BAG", "Early Black Friday"]),
        "format": ad("S01", "my_idea", ["Zipped."]),
    }
    want = {"fake interface": "fake interface", "publication": "publication", "closed": "closed", "prices": "prices", "face": "face",
            "words": "at most", "format": "format of your own"}
    for k, s in cases.items():
        P = static_problems([s, ad("S02", "film_still", ["Last stop."], **OWN)], empty)
        assert any(want[k] in p for p in P), (k, P)


def test_every_batch_new_formats():
    empty = {"products": {}}
    twice = [ad("S01", "bold_poster", ["HALF PRICE."]), ad("S02", "bold_poster", ["Zipped all day."]), ad("S03", "film_still", ["Last stop."], **OWN)]
    assert any("used 2 times" in p for p in static_problems(twice, empty))
    library_only = [ad("S01", "bold_poster", ["HALF PRICE."]), ad("S02", "magazine_cover", ["LIBRA", "THE ZIP ISSUE"]),
                    ad("S03", "flat_lay", ["Everything fits."])]
    assert any("of your own" in p for p in static_problems(library_only, empty))
    last = {"products": {"hobo-bag": {"batches": [{"date": "2026-10-25", "name": "B030", "statics": [
        {"layout": "ad", "format": "bold_poster", "caption": "HALF PRICE."}, {"layout": "ad", "format": "film_still", "caption": "Last stop."}]}]}}}
    P = static_problems([ad("S01", "bold_poster", ["Zipped all day."]), ad("S02", "magazine_cover", ["LIBRA", "THE ZIP ISSUE"]),
                         ad("S03", "film_still", ["Last train home."], **OWN)], last)
    assert any("S01" in p and "last batch" in p for p in P), P
    assert any("of your own" in p for p in P), P                     # (film_still was invented last batch: not new any more)
    P = static_problems([ad("S01", "magazine_cover", ["LIBRA", "HALF PRICE."]), ad("S02", "flat_lay", ["Everything fits."]),
                         ad("S03", "window_box", ["Zipped."], **dict(OWN, format_name="Window box"))], last)
    assert any("HALF PRICE" in p and "earlier batch" in p for p in P), P
    redo = static_problems([ad("S01", "bold_poster", ["HALF PRICE."]), ad("S02", "film_still", ["Last stop."], **OWN),
                            ad("S03", "magazine_cover", ["LIBRA", "THE ZIP ISSUE"])], last, exclude="B030")
    assert not [p for p in redo if "last batch" in p or "earlier batch" in p or "of your own" in p], redo   # a redo of B030 itself


def test_the_prompt_carries_the_words_and_the_rules():
    lib = ai_gen.library()
    f = ideas.formats()["formats"]["pov_behind"]
    p = ai_gen.build_ad_prompt(lib, f, ad("S01", "pov_behind", ["POV: zipped all the way home"], prompt="A wet street at dusk."), "handbag", "Black")
    assert '"POV: zipped all the way home"' in p and "No other text anywhere" in p and "seen only from behind" in p
    assert p.count("seen only from behind") == 1 and "closed and zipped" in p and "(black)" in p and "A wet street at dusk." in p
    assert ai_gen.ad_kind(f) == "behind" and ai_gen.ad_kind(ideas.formats()["formats"]["gift_unbox"]) == "hand"
    own = ai_gen.build_ad_prompt(lib, ideas.ad_format(ad("S02", "film_still", ["Last stop."], **OWN)), ad("S02", "film_still", ["Last stop."]),
                                 "handbag", None)
    assert own.startswith("A cinematic widescreen film still") and "seen only from behind" in own


def test_a_wrong_percent_in_the_picture_fails_the_gate():
    if not shutil.which("tesseract"):
        print("     (no tesseract: skipped)")
        return
    from PIL import Image, ImageDraw, ImageFont
    d = tempfile.mkdtemp()
    im = Image.new("RGB", (1200, 1500), (250, 246, 240))
    try:
        fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
    except OSError:
        fnt = ImageFont.load_default()
    ImageDraw.Draw(im).text((80, 200), "EARLY BLACK FRIDAY", fill=(20, 20, 20), font=fnt)
    ImageDraw.Draw(im).text((80, 400), "70% OFF", fill=(20, 20, 20), font=fnt)
    f = os.path.join(d, "a.png")
    im.save(f)
    r = ai_gen.text_check(f, ["EARLY BLACK FRIDAY", "50% OFF"])
    assert any("70%" in p and not p.startswith("look") for p in r["problems"]), r
    r = ai_gen.text_check(f, ["EARLY BLACK FRIDAY", "70% OFF"])
    assert not [p for p in r["problems"] if not p.startswith("look")], r


def test_the_ad_layout_renders_the_picture_as_it_is():
    import brand_statics as bs
    from PIL import Image
    d = tempfile.mkdtemp()
    Image.new("RGB", (1792, 2240), (120, 40, 50)).save(os.path.join(d, "AS01.png"))
    im = bs.render(dict(name="x", layout="ad", photo="AS01.png", words=["LIBRA"]), d)
    assert im.size == (1080, 1350) and im.getpixel((540, 675)) == (120, 40, 50)


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
