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
        "words": ad("S01", "bold_poster", ["HALF PRICE TODAY ON THE EVERYDAY BAG", "Early Black Friday, the sale is now on"]),
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
    P = static_problems([ad("S01", "magazine_cover", ["LIBRA", "Last stop."]), ad("S02", "flat_lay", ["Everything fits."]),
                         ad("S03", "window_box", ["Zipped."], **dict(OWN, format_name="Window box"))], last)
    assert any("Last stop" in p and "earlier batch" in p for p in P), P
    P = static_problems([ad("S01", "magazine_cover", ["LIBRA", "HALF PRICE."]), ad("S02", "flat_lay", ["Everything fits."]),
                         ad("S03", "window_box", ["Zipped."], **dict(OWN, format_name="Window box"))], last)
    assert not any("HALF PRICE" in p and "earlier batch" in p for p in P), P      # (the offer repeats by design: Wouter 2026-11-04)
    redo = static_problems([ad("S01", "bold_poster", ["HALF PRICE."]), ad("S02", "film_still", ["Last stop."], **OWN),
                            ad("S03", "magazine_cover", ["LIBRA", "THE ZIP ISSUE"])], last, exclude="B030")
    assert not [p for p in redo if "last batch" in p or "earlier batch" in p or "of your own" in p], redo   # a redo of B030 itself


def test_a_statics_only_sheet_needs_no_project():
    import novelty
    stats = [dict(ad("S01", "bold_poster", ["HALF PRICE."]), project=None), dict(ad("S02", "film_still", ["Last stop."], **OWN), project=None),
             dict(id="S03", layout="studio", idea="The real packshot large on a calm backdrop.", headline="The Hobo Bag.")]
    sheet = dict(product="Hobo Bag", theme="black friday", date="2026-11-03", research=["a statics-only batch"], projects=[], statics=stats)
    real = novelty.load
    novelty.load = lambda *a, **k: {"products": {}}
    try:
        P, _ = ideas.check(sheet, pr(), n_projects=0, n_statics=3)
    finally:
        novelty.load = real
    assert not [p for p in P if "not in the sheet" in p], P
    md = ideas.sheet_md(sheet)
    assert "## Statics" in md and "S01" in md and "S03" in md, md
    sheet["projects"], stats[0]["project"] = [], "P07"
    novelty.load = lambda *a, **k: {"products": {}}
    try:
        P, _ = ideas.check(sheet, pr(), n_projects=0, n_statics=3)
    finally:
        novelty.load = real
    assert any("S01: project 'P07' is not in the sheet" in p for p in P), P


def test_every_static_shows_the_offer_from_2026_11_04():
    import novelty
    base = dict(product="Hobo Bag", theme="black friday", research=["offer test"], projects=[])
    no_offer = [ad("S01", "giant_numerals", ["The everyday hobo."]), ad("S02", "film_still", ["Last stop. 50% off."], **OWN),
                dict(id="S03", layout="concept", idea="The bag on a cafe table by the window.", headline="Coffee first.",
                     scene=dict(kind="object", colour="Black", prompt="The bag on a round marble cafe table by a tall window."))]
    real = novelty.load
    novelty.load = lambda *a, **k: {"products": {}}
    try:
        P, _ = ideas.check(dict(base, date="2026-11-04", statics=copy.deepcopy(no_offer)), pr(), n_projects=0, n_statics=3)
        assert any(p.startswith("S01: no offer") for p in P) and any(p.startswith("S03: no offer") for p in P), P
        assert not any(p.startswith("S02: no offer") for p in P), P
        fixed = copy.deepcopy(no_offer)
        fixed[0]["words"], fixed[2]["pill"] = ["50%", "OFF", "Early Black Friday"], True
        P, _ = ideas.check(dict(base, date="2026-11-04", statics=fixed), pr(), n_projects=0, n_statics=3)
        assert not [p for p in P if "no offer" in p], P
        P, _ = ideas.check(dict(base, date="2026-11-03", statics=copy.deepcopy(no_offer)), pr(), n_projects=0, n_statics=3)
        assert not [p for p in P if "no offer" in p], P          # (an older sheet keeps its own day's rules)
    finally:
        novelty.load = real
    lib = ai_gen.library()
    p = ai_gen.build_ad_prompt(lib, ideas.formats()["formats"]["giant_numerals"], ad("S01", "giant_numerals", ["50%", "OFF"]), "handbag", None)
    assert 'The offer "50%" is the boldest' in p


def test_every_static_tells_a_story_from_2026_11_04():
    """The team 2026-11-04 on the 9 offer-led samples: 'story is not enough': the offer AND one line that says why to buy."""
    import novelty
    base = dict(product="Hobo Bag", theme="black friday", research=["story test"], projects=[])
    cafe = dict(kind="object", colour="Black", prompt="The bag on a round marble cafe table by a tall window, the bottom of the frame calm and empty.")
    bare = [ad("S01", "giant_numerals", ["50%", "OFF", "Early Black Friday"]), ad("S02", "sticker_burst", ["The everyday hobo.", "50% OFF"]),
            ad("S03", "film_still", ["Last stop. 50% off."], **OWN),
            dict(id="S04", layout="concept", idea="The bag on a cafe table by the window.", headline="Coffee first. Zipped always.", pill=True, scene=cafe),
            dict(id="S05", layout="offer", idea="The offer card."), dict(id="S06", layout="colours", idea="The colours side by side.")]
    told = lambda P: [p for p in P if "story" in p or "feature" in p]   # noqa: E731
    real = novelty.load
    novelty.load = lambda *a, **k: {"products": {}}
    try:
        P = told(ideas.check(dict(base, date="2026-11-04", statics=copy.deepcopy(bare)), pr(), n_projects=0, n_statics=6)[0])
        assert any(p.startswith("S01: no story line") for p in P) and any(p.startswith("S02: no story line") for p in P), P
        assert not any(p.startswith("S03: no story line") for p in P) and any(p.startswith("S03: story:") for p in P), P
        assert any("S05, S06 show the offer / the colours alone" in p for p in P), P
        fixed = copy.deepcopy(bare)
        fixed[0].update(words=["50%", "OFF", "Cards stay on your side."], story="moment", feature="HIDDEN BACK POCKET")
        fixed[1].update(words=["Two gold side zips for your keys.", "50% OFF"], story="problem_fix", feature="GOLD SIDE ZIPS")
        fixed[2].update(story="moment", feature="3 WAYS TO WEAR")
        fixed[3].update(story="gift")
        fixed[5] = dict(id="S06", layout="quotes", idea="One verbatim review by the packshot.")
        P, W = ideas.check(dict(base, date="2026-11-04", statics=fixed), pr(), n_projects=0, n_statics=6)
        assert told(P) == [], told(P)
        assert not [w for w in W if "feature" in w], W
        assert told(ideas.check(dict(base, date="2026-11-03", statics=copy.deepcopy(bare)), pr(), n_projects=0, n_statics=6)[0]) == []
        same = copy.deepcopy(fixed)                  # one story type everywhere / one feature on half the batch
        for x in same[:4]:
            x.update(story="problem_fix", feature="GOLD SIDE ZIPS")
        P = told(ideas.check(dict(base, date="2026-11-04", statics=same), pr(), n_projects=0, n_statics=6)[0])
        assert any("the problem_fix story on 4 of 5" in p for p in P) and any("tell the GOLD SIDE ZIPS story" in p for p in P), P
        assert any("story type(s)" in p for p in P), P
    finally:
        novelty.load = real
    assert ideas.story_line(dict(layout="ad", words=["LIBRA", "50% OFF", "Packed train. Cards on your side."])) == "Packed train. Cards on your side."
    assert ideas.story_line(dict(layout="ad", words=["60% OFF", "3 bags. 1 set."])) == "3 bags. 1 set."
    assert ideas.story_line(dict(layout="ad", words=["50% OFF", "The hidden-pocket hobo"])) is None
    assert ideas.story_line(dict(layout="ad", words=["Morning · Desk · Dinner", "One bag, all day.", "50% OFF"])) == "One bag, all day."
    assert ideas.story_caption(dict(layout="ad", words=["Keys at the bottom again?", "Two gold side zips.", "50% OFF"])) == \
        "Keys at the bottom again? Two gold side zips."              # (the real stand-in's caption when the AI picture fails)
    p = ai_gen.build_ad_prompt(ai_gen.library(), ideas.formats()["formats"]["sticker_burst"],
                               ad("S01", "sticker_burst", ["Two gold side zips for your keys.", "50% OFF"]), "handbag", None)
    assert 'The offer "50% OFF" is the boldest' in p and 'The line "Two gold side zips for your keys." is the second voice' in p and "answer" not in p
    md = ideas.sheet_md(dict(base, date="2026-11-04", statics=fixed))
    assert "problem_fix: GOLD SIDE ZIPS" in md and "| proof |" in md, md


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
