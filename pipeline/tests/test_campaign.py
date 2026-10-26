"""The store-wide sale campaign (campaign.py, data/campaign.json): when it runs, what compliance accepts, the sale layouts;
and one look per batch for a product with two (make_batch.design_of / clip_ok, data/designs.json).
Run: python3 pipeline/tests/test_campaign.py"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import campaign  # noqa: E402
import compliance  # noqa: E402

BF = campaign.active("black friday", "2026-10-23")


def probs(text, product="Hobo Bag", camp=BF):
    compliance.use_campaign(camp)
    try:
        return [(p["category"], p["term"]) for p in compliance.check(text, product=product)]
    finally:
        compliance.use_campaign(None)


def test_the_campaign_runs_for_sale_themes_inside_its_dates_only():
    assert BF and BF["id"] == "bf2026" and BF["end_pill"] == "UP TO 60% OFF" and not BF["gifts"] and not BF["bundle_any"]
    assert campaign.active("cyber monday", "2026-11-30")
    assert campaign.active("black friday", "2026-10-22") is None
    assert campaign.active("black friday", "2026-12-01") is None
    assert campaign.active("christmas", "2026-11-10") is None
    assert campaign.active("default", "2026-11-10") is None


def test_compliance_accepts_the_sale_words():
    for t in ["Early Black Friday: up to 60% off.", "Black Friday: up to sixty percent off.", "Up to 60% off bundles.",
              "Get 60% off the 3-Piece Set.", "Early Black Friday: 50% off everything."]:
        assert probs(t) == [], (t, probs(t))


def test_compliance_catches_what_the_sale_no_longer_says():
    """Owner 2026-10-26: no free gifts, 60% only on bundles like the 3-Piece Set."""
    assert ("offer", "60% off") in probs("The Hobo Bag is 60% off.")             # one bag: its own 50%
    for t in ["Get 60% off when you buy 2 or 3 bags together.", "Buy two bags and get a free jewellery box.",
              "Black Friday Sale: up to 60% off + free gifts."]:
        assert any(c == "offer" for c, _ in probs(t)), (t, probs(t))
    assert any(c == "offer" for c, _ in probs("Up to 60% off.", product="Vintage Bag", camp=None))   # no campaign: not backed


def test_strip_keeps_what_is_not_the_sale():
    assert "60% off the Hobo Bag" in campaign.strip("60% off the Hobo Bag.", BF)
    assert "60%" not in campaign.strip("Early Black Friday: up to 60% off.", BF)
    assert "2 or 3 bags" in campaign.strip("60% off 2 or 3 bags", BF)


def test_no_gift_lines_any_more():
    assert campaign.gift_line(BF, 2) == "" and campaign.gift_line(BF, 3) == ""


def test_the_sale_layouts_render():
    import brand_statics as bs
    from PIL import Image
    d = tempfile.mkdtemp()
    bag = Image.new("RGB", (900, 1100), (255, 255, 255))
    from PIL import ImageDraw
    ImageDraw.Draw(bag).rounded_rectangle([200, 300, 700, 1000], radius=60, fill=(90, 50, 30))
    for n in ("a", "b"):
        bag.save(os.path.join(d, f"bag_{n}.jpg"))
    gifts = [dict(src=os.path.relpath(os.path.join(os.path.dirname(HERE), "assets", "gifts", f), d), label=lb)       # (the layouts stay
             for f, lb in (("jewellery_box.jpg", "FREE JEWELLERY BOX"), ("cosmetic_bag.jpg", "+ FREE COSMETIC BAG"))]   # for a later sale)
    for spec in (dict(name="g", layout="gifts", photo="bag_a.jpg", kicker="BLACK FRIDAY SALE", headline="Buy 2 bags, get a free gift.",
                      gifts=gifts, rows=["2 bags: a free mirrored jewellery box (worth $19.95)"], note="Only bags count", cta="Shop now"),
                 dict(name="b", layout="bundle", photos=["bag_a.jpg", "bag_b.jpg"], kicker="BLACK FRIDAY SALE",
                      headline="One for you, one for her.", pill="60% OFF 2 OR 3 BAGS", cta="Shop now")):
        im = bs.render(spec, d)
        assert im is not None and im.size == (1080, 1350), spec["layout"]


def test_no_returns_promise_while_the_sale_is_final_sale():
    assert BF["final_sale"] and "final sale" in " ".join(BF["facts"])
    for t in ["One-year warranty, easy returns. Tap the link below.", "Not sure it will suit? There is a one-year warranty and easy returns.",
              "Free returns on every order.", "Don't love it? Send it back."]:
        assert any(c == "claims" for c, _ in probs(t)), (t, probs(t))
    assert probs("It comes with a one-year warranty.") == []
    assert probs("Not sure it will suit? There is a one-year warranty and easy returns.", camp=None) == []    # outside the sale


def test_one_look_per_batch_for_a_two_look_product():
    """The guard (designs.json 'show'); the Hobo 2.0 was resolved on 2026-10-26 (one bag, two straps), so it has none now."""
    import make_batch as mb
    assert mb.design_of("Hobo 2.0") is None and mb.design_of("Hobo Bag") is None
    dz = dict(product="Hobo 2.0", site="slim", library="eyelet", bank_sections=["hobo_2_0"], designs={"slim": "", "eyelet": ""})
    keep = mb.DESIGN[0]
    try:
        mb.DESIGN[0] = dict(dz, show="eyelet")
        assert mb.clip_ok({"product": "Hobo 2.0"})                                   # untagged: the library's look
        assert not mb.clip_ok({"product": "Hobo 2.0", "design": "slim"})
        assert mb.clip_ok({"id": "x"}, "hobo_2_0") and mb.clip_ok({"product": "Hobo Bag", "design": "slim"})
        mb.DESIGN[0] = dict(dz, show="slim")
        assert not mb.clip_ok({"id": "x"}, "hobo_2_0") and not mb.clip_ok({"product": "Hobo 2.0"})
        assert mb.clip_ok({"product": "Hobo 2.0", "design": "slim"}) and mb.clip_ok({"id": "x"}, "hobo_bag")
        mb.DESIGN[0] = None
        assert mb.clip_ok({"product": "Hobo 2.0", "design": "slim"})
    finally:
        mb.DESIGN[0] = keep


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
