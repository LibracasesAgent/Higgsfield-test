#!/usr/bin/env python3
"""Story statics (layout 'story', 2026-11-04 "good but very basic and not top tier"): the five looks render with every layer and
nothing overlapping, the review is always verbatim, the sheet check refuses what would break the anatomy or the rules.
Run: python3 pipeline/tests/test_story_statics.py"""
import copy
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ai_gen  # noqa: E402
import brand_statics as bs  # noqa: E402
import ideas  # noqa: E402

PR = []


def pr():
    if not PR:
        PR.append(ideas.product_of("Hobo Bag"))
    return PR[0]


def photo(d):
    """A calm photo-like test picture (a warm gradient with a dark block where a bag would be)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (896, 1120))
    px = ImageDraw.Draw(im)
    for y in range(1120):
        px.line([(0, y), (896, y)], fill=(200 - y // 12, 170 - y // 14, 140 - y // 16))
    px.rounded_rectangle([280, 360, 640, 760], radius=60, fill=(70, 40, 30))
    os.makedirs(os.path.join(d, "ai"), exist_ok=True)
    im.save(os.path.join(d, "ai", "AS01.png"))
    return "ai/AS01.png"


LOOKS = {
    "hook": dict(kicker="EARLY BLACK FRIDAY", hook="Keys at the bottom of your bag again?", highlight=["Keys"],
                 sub="Two gold side zips keep them in reach.", review=10),
    "quote": dict(kicker="Christmas, sorted", review=9, review_text="Got this bag for my daughter for Christmas and she adores it."),
    "list": dict(hook="3 reasons it goes everywhere with you", highlight=["everywhere"], review=7,
                 points=["A hidden pocket that sits flat against you", "Two gold side zips for keys and phone",
                         "Two straps: shoulder, hand or crossbody"]),
    "versus": dict(hook="Your old tote vs the Hobo Bag", highlight=["Hobo", "Bag"], them="Open tote", us="Hobo Bag", review=12,
                   rows=[["Open top", "Zips shut"], ["Everything sinks", "Smart compartments"], ["One way to carry", "3 ways to wear"]]),
    "stack": dict(hook="Everything you get for half price", highlight=["half", "price"], review=8,
                  points=["The Hobo Bag", "Matching pouch wallet, free", "Free US shipping", "1-year warranty"]),
}


def test_every_look_renders_with_every_layer():
    d = tempfile.mkdtemp()
    try:
        ph = photo(d)
        for look, kw in LOOKS.items():
            a = dict(name=f"t_{look}", layout="story", look=look, photo=ph, pct=50, gift="free pouch wallet", **kw)
            im = bs.render(copy.deepcopy(a), d)
            assert im.size == (1080, 1350), (look, im.size)
            bs.TRACK[0] = True                 # (what one render draws: the sticker, the proof and the hook are all there)
            try:
                bs.DRAWN.clear()
                bs.LAYOUTS["story"](copy.deepcopy(a), d)
                labels = " | ".join(str(e["label"]) for e in bs.DRAWN)
            finally:
                bs.TRACK[0] = False
                bs.DRAWN.clear()
            assert "50%" in labels and "+ FREE POUCH WALLET" in labels or look == "stack", (look, labels)
            assert "stars" in labels, (look, labels)
            if look != "quote":
                assert any(w in labels for w in kw["hook"].split()[:2]), (look, labels)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_the_review_is_verbatim_and_required():
    d = tempfile.mkdtemp()
    try:
        ph = photo(d)
        for bad, want in ((dict(look="quote", review=None), "needs a review"),
                          (dict(look="quote", review=9, review_text="Best gift ever, she cried."), "verbatim"),
                          (dict(look="list", hook=None, points=["a", "b", "c"], review=7), "needs a hook")):
            a = dict(name="t", layout="story", photo=ph, pct=50, **{k: v for k, v in bad.items() if v is not None})
            try:
                bs.render(a, d, tries=1)
                raise AssertionError(f"rendered: {bad}")
            except Exception as e:  # noqa: BLE001
                assert want in str(e), (bad, e)
        a = dict(name="t", layout="story", look="hook", photo=ph, hook="Keys at the bottom of your bag again?", review=10)
        assert bs.render(a, d).size == (1080, 1350)          # (no offer given: no sticker, nothing made up)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def story_sheet(stats):
    return dict(product="Hobo Bag", theme="black friday", date="2026-11-04", research=["story test"], projects=[], statics=stats)


def problems(stats):
    import novelty
    real = novelty.load
    novelty.load = lambda *a, **k: {"products": {}}
    try:
        P, W = ideas.check(copy.deepcopy(story_sheet(stats)), pr(), n_projects=0, n_statics=len(stats))
    finally:
        novelty.load = real
    return P, W


def good():
    return [dict(id="S01", layout="story", look="hook", story="problem_fix", feature="GOLD SIDE ZIPS", idea="The keys at the side zip.",
                 **LOOKS["hook"]),
            dict(id="S02", layout="story", look="quote", story="gift", idea="Her Christmas story.", **LOOKS["quote"]),
            dict(id="S03", layout="story", look="list", story="proof", feature="HIDDEN BACK POCKET", idea="A numbered list.",
                 scene=dict(kind="worn", colour="Galaxy Black", prompt="A woman cropped at the shoulders walking through a bright "
                                                                       "station concourse, the black bag on her shoulder."),
                 **LOOKS["list"])]


def test_the_sheet_check():
    P, W = problems(good())
    assert P == [], P
    assert ideas.story_line(good()[1]).startswith("Got this bag")
    assert [i for i, _ in ideas.concept_scenes(story_sheet(good()))] == [2]       # (only the one with a scene is an AI still)
    cases = {"look": dict(look="poster"), "hook": dict(hook="Keys"), "highlight": dict(highlight=["wallet"]),
             "review": dict(review=11), "verbatim": dict(review=10, review_text="It holds everything and more."),
             "brand": dict(look="versus", them="Michael Kors", rows=[["Open top", "Zips shut"]] * 3, hook="Your old tote vs ours"),
             "first": dict(hook="I love how my keys stay in reach")}
    want = {"look": "look 'poster'", "hook": "hook:", "highlight": "highlight 'wallet'", "review": "not one of Hobo Bag's reviews",
            "verbatim": "not a verbatim part", "brand": "real brand", "first": "first person"}
    for k, ch in cases.items():
        s = dict(good()[0], **ch)
        P, _ = problems([s] + good()[1:])
        assert any(want[k] in p for p in P), (k, P)


def test_hero_and_colours_show_the_offer():
    """(Wouter 2026-11-04 'Don't have the offer on it': a hero / colours static that stands in for a real slot draws the %.)"""
    d = tempfile.mkdtemp()
    try:
        ph = photo(d)
        for a in (dict(name="t_hero", layout="hero", photo=ph, headline="Cards and cash, in the matching pouch.", pct=60),
                  dict(name="t_col", layout="colours", headline="Which colour are you?", pct=60,
                       photos=[dict(src=ph, name="Red"), dict(src=ph, name="Blue")])):
            assert bs.render(copy.deepcopy(a), d).size == (1080, 1350), a["layout"]
            bs.TRACK[0] = True
            try:
                bs.DRAWN.clear()
                bs.LAYOUTS[a["layout"]](copy.deepcopy(a), d)
                labels = " | ".join(str(e["label"]) for e in bs.DRAWN)
            finally:
                bs.TRACK[0] = False
                bs.DRAWN.clear()
            assert "60%" in labels, (a["layout"], labels)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_the_scene_asks_for_its_composition():
    assert "top third is calm" in ai_gen.STORY_COMPOSE["hook"] and "bottom 40%" in ai_gen.STORY_COMPOSE["quote"]
    assert all(k in ai_gen.STORY_COMPOSE for k in ideas.STORY_LOOKS) and set(ideas.STORY_LOOKS) == set(bs.STORY_LOOKS)


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
