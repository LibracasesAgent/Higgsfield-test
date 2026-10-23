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
    assert BF and BF["id"] == "bf2026" and BF["end_pill"] == "UP TO 60% OFF + FREE GIFTS"
    assert campaign.active("cyber monday", "2026-11-30")
    assert campaign.active("black friday", "2026-10-22") is None
    assert campaign.active("black friday", "2026-12-01") is None
    assert campaign.active("christmas", "2026-11-10") is None
    assert campaign.active("default", "2026-11-10") is None


def test_compliance_accepts_the_sale_words():
    for t in ["Black Friday Sale: up to 60% off + free gifts.",
              "Black Friday: up to sixty percent off, plus free gifts.",
              "Buy two bags and you also get a free jewellery box, while stocks last.",
              "Get 60% off when you buy 2 or 3 bags together.",
              "60% OFF 2 OR 3 BAGS",
              "3+ bags: + a free cosmetic bag (together worth $44.90)",
              "2 bags: a free mirrored jewellery box (worth $19.95)"]:
        assert probs(t) == [], (t, probs(t))


def test_compliance_still_catches_what_the_sale_does_not_say():
    assert ("offer", "60% off") in probs("The Hobo Bag is 60% off.")             # one bag: its own 50%
    assert any(c == "numbers" for c, _ in probs("Free gifts worth $99."))
    assert probs("Black Friday Sale: up to 60% off + free gifts.", camp=None)   # no campaign: not backed
    assert any(c == "offer" for c, _ in probs("Up to 60% off + free gifts.", product="Vintage Bag", camp=None))


def test_strip_keeps_what_is_not_the_sale():
    assert "60% off the Hobo Bag" in campaign.strip("60% off the Hobo Bag.", BF)
    assert "60%" not in campaign.strip("Up to 60% off + free gifts.", BF)


def test_gift_lines():
    assert campaign.gift_line(BF, 2) == "a free mirrored jewellery box (worth $19.95)"
    assert "together worth $44.90" in campaign.gift_line(BF, 3)
    assert campaign.gift_line(BF, 1) == ""


def test_the_sale_layouts_render():
    import brand_statics as bs
    from PIL import Image
    d = tempfile.mkdtemp()
    bag = Image.new("RGB", (900, 1100), (255, 255, 255))
    from PIL import ImageDraw
    ImageDraw.Draw(bag).rounded_rectangle([200, 300, 700, 1000], radius=60, fill=(90, 50, 30))
    for n in ("a", "b"):
        bag.save(os.path.join(d, f"bag_{n}.jpg"))
    gifts = [dict(src=os.path.relpath(g["photo"], d), label="FREE " + g["short"].upper()) for g in BF["gifts"]]
    for spec in (dict(name="g", layout="gifts", photo="bag_a.jpg", kicker="BLACK FRIDAY SALE", headline="Buy 2 bags, get a free gift.",
                      gifts=gifts, rows=["2 bags: a free mirrored jewellery box (worth $19.95)"], note="Only bags count", cta="Shop now"),
                 dict(name="b", layout="bundle", photos=["bag_a.jpg", "bag_b.jpg"], kicker="BLACK FRIDAY SALE",
                      headline="One for you, one for her.", pill="60% OFF 2 OR 3 BAGS", cta="Shop now")):
        im = bs.render(spec, d)
        assert im is not None and im.size == (1080, 1350), spec["layout"]


def test_one_look_per_batch_for_a_two_look_product():
    import make_batch as mb
    dz = mb.design_of("Hobo 2.0")
    assert dz and dz["show"] in dz["designs"] and dz["site"] in dz["designs"] and dz["library"] in dz["designs"]
    assert mb.design_of("Hobo Bag") is None
    keep = mb.DESIGN[0]
    try:
        mb.DESIGN[0] = dict(dz, show="eyelet", library="eyelet")
        assert mb.clip_ok({"product": "Hobo 2.0"})                                   # untagged: the library's look
        assert not mb.clip_ok({"product": "Hobo 2.0", "design": "slim"})
        assert mb.clip_ok({"id": "x"}, "hobo_2_0") and mb.clip_ok({"product": "Hobo Bag", "design": "slim"})
        mb.DESIGN[0] = dict(dz, show="slim", library="eyelet")
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
