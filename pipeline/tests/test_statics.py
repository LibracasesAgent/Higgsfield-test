#!/usr/bin/env python3
"""Tests of the clean statics (owner 2026-10-20): the studio layout, a text-free scene, the clean 20-static cycle.

  python3 pipeline/tests/test_statics.py      # no network, no Higgsfield: synthetic packshots in a temp folder
"""
import collections
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import brand_statics as bs  # noqa: E402
import make_batch  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def packshot(d, name, colour, backdrop=(255, 255, 255)):
    """A 800x800 'packshot': a bag-coloured rounded body with a strap on a studio-white (or other) backdrop."""
    im = Image.new("RGB", (800, 800), backdrop)
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([140, 430, 660, 700], radius=50, fill=colour)
    dr.arc([260, 120, 540, 640], 180, 360, fill=colour, width=26)
    im.save(os.path.join(d, name))
    return name


def test_studio_renders_and_keeps_the_bag_colour():
    with tempfile.TemporaryDirectory() as d:
        for name, col in (("red.jpg", (170, 30, 40)), ("black.jpg", (22, 22, 24)), ("beige.jpg", (222, 205, 178))):
            packshot(d, name, col)
            ad = dict(name="s", layout="studio", photo=name, headline="The Hobo Bag.", pct=50)
            im = bs.render(ad, d)
            assert im.size == (1080, 1350)
            # the backdrop is a calm tint, not the packshot's white, and the same on both sides (no box around the product)
            tl, tr = im.getpixel((20, 20)), im.getpixel((1060, 20))
            assert tl != (255, 255, 255) and all(abs(tl[i] - tr[i]) <= 8 for i in range(3)), (name, tl, tr)
            # the bag's own colour survives the tinted backdrop (the tint is divided out of the product's pixels)
            hits = sum(1 for x in range(0, 1080, 6) for y in range(0, 1350, 6)
                       if all(abs(im.getpixel((x, y))[i] - col[i]) <= 14 for i in range(3)))
            assert hits >= 200, (name, col, hits)


def test_studio_refuses_a_photo_that_is_not_a_white_packshot():
    with tempfile.TemporaryDirectory() as d:
        packshot(d, "grey.jpg", (120, 40, 40), backdrop=(150, 150, 150))
        try:
            bs.render(dict(name="s", layout="studio", photo="grey.jpg", headline="x"), d)
        except bs.LayoutError:
            raise AssertionError("a ValueError was expected, not a layout error")
        except ValueError as e:
            assert "white studio backdrop" in str(e)
        else:
            raise AssertionError("studio drew a non-packshot")


def test_studio_tint():
    warm = bs.studio_tint((20, 20, 20))
    assert warm == bs.studio_tint(None) and max(warm) - min(warm) < 25 and bs._luma(warm) > 215     # black / grey: warm neutral
    red = bs.studio_tint((170, 30, 40))
    assert bs._luma(red) > 200 and max(red) - min(red) < 40                                         # muted and very light
    beige = (222, 205, 178)
    assert abs(bs._luma(bs.studio_tint(beige)) - bs._luma(beige)) >= 30                             # a light bag stands out


def test_studio_line_and_pill_only():
    with tempfile.TemporaryDirectory() as d:
        packshot(d, "p.jpg", (90, 50, 30))
        for kw in (dict(headline="Sleek shape.", pct=50), dict(headline="Sleek shape."), dict(pct=50), dict()):
            im = bs.render(dict(name="s", layout="studio", photo="p.jpg", **kw), d)
            assert im.size == (1080, 1350)
        # no CTA button / badge in the spec: the layout never draws one
        bs.render(dict(name="s", layout="studio", photo="p.jpg", headline="x", cta="Shop now", badge={"big": "50%"}), d)


def test_scene_can_run_text_free():
    with tempfile.TemporaryDirectory() as d:
        Image.new("RGB", (896, 1120), (120, 150, 110)).save(os.path.join(d, "scene.png"))
        im = bs.render(dict(name="s", layout="scene", photo="scene.png"), d)
        assert im.size == (1080, 1350)
        flat = {im.getpixel((x, y)) for x in range(0, 1080, 90) for y in range(0, 1350, 90)}
        assert len(flat) <= 3, "a text-free scene is the photo alone"


def test_clean_cycle_composition():
    for flags in ((True, True, False), (True, False, True), (True, False, False)):
        seq = make_batch.static_cycle(*flags)
        c = collections.Counter(seq)
        assert len(seq) == 20, (flags, len(seq))
        assert c["studio"] == 4 and c["native"] + c["lifestyle"] >= 4, c
        for lay in ("compare", "bold", "checklist", "colours", "stars"):
            assert c[lay] <= 1, (flags, lay, c[lay])
        assert c["offer"] <= 2 and c["value"] <= 2 and c["quotes"] <= 3, c
        assert not {"hero", "promo", "review"} & set(c), c
    seq = make_batch.static_cycle(False, False, False)             # no clean packshots: the client's photos, no studio
    assert len(seq) == 20 and "studio" not in seq and collections.Counter(seq)["native"] >= 8


def test_classic_cycle_is_unchanged():
    assert make_batch.static_cycle(True, True, False, classic=True)[:3] == ["hero", "offer", "stars"]
    assert len(make_batch.static_cycle(True, True, False, classic=True)) == 12
    assert len(make_batch.static_cycle(True, False, True, classic=True)) == 12
    assert make_batch.static_cycle(True, False, False, classic=True)[:2] == ["hero", "promo"]
    assert make_batch.static_cycle(False, False, False, classic=True)[:2] == ["lifestyle", "bold"]
    for flags in ((True, True, False), (True, False, True), (True, False, False), (False, False, False)):
        assert "studio" not in make_batch.static_cycle(*flags, classic=True)


def test_scene_look_half_without_caption():
    looks = [make_batch.scene_look(n) for n in range(1, 9)]
    assert sum(1 for cap, _ in looks if not cap) == 4 and sum(1 for _, pill in looks if pill) == 4
    assert (False, False) in looks and (True, True) in looks          # a photo alone, a caption + pill: both exist


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
