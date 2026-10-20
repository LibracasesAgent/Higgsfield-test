#!/usr/bin/env python3
"""Tests of the batch numbering (ledger.py) and the names it makes (make_batch.ad_prefix / folder_name / ad_id / batch_repeats).

  python3 pipeline/tests/test_batches.py      # no network, no Drive: a temp ledger
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import ledger  # noqa: E402
import make_batch  # noqa: E402


def test_batch_ids():
    assert ledger.bid(45) == "B045" and ledger.bid(45, 2) == "B045r2" and ledger.bid(7, 1) == "B007"
    assert ledger.parse("B045") == (45, 1) and ledger.parse("b45") == (45, 1) and ledger.parse("45") == (45, 1)
    assert ledger.parse("B045r3") == (45, 3) and ledger.parse(None) == (None, 1) and ledger.parse("hello") == (None, 1)


def test_reserve_numbers_every_plan_once_and_a_redo_keeps_its_number():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "l.json")
        a = ledger.reserve("Hobo Bag", "Evergreen", "catalog", "x", 5, 3, 4, 1, "2026-10-20", p=p)
        b = ledger.reserve("Vintage Bag", "Evergreen", "catalog", "x", 5, 3, 4, 1, "2026-10-20", p=p)
        c = ledger.reserve("Hobo 2.0", "Evergreen", "catalog", "x", 5, 3, 4, 1, "2026-10-20", p=p)
        assert (a["n"], b["n"], c["n"]) == (1, 2, 3)                          # three plans of one request: three numbers
        r = ledger.reserve("Hobo Bag", "Evergreen", "catalog", "redo", 0, 1, 4, 2, "2026-10-21", number=1, p=p)
        assert r["n"] == 1 and r["rev"] == 2 and ledger.bid(r["n"], r["rev"]) == "B001r2"
        assert ledger.load(p)["next"] == 4 and len(ledger.load(p)["batches"]) == 3
        ledger.reserve("Hobo Bag", "Evergreen", "catalog", "x", 1, 0, 4, 1, "2026-10-21", number=9, p=p)    # an id from elsewhere: next moves past it
        assert ledger.load(p)["next"] == 10


def test_prefix_and_ad_id():
    pre = make_batch.ad_prefix("Hobo 2.0", "Evergreen", 1, 45)
    assert pre.endswith("_Hobo20_Evergreen_B045") and pre.startswith("LC_")
    assert make_batch.ad_prefix("Hobo Bag", "BlackFriday", 2, 45).endswith("_HoboBag_BlackFriday_B045r2")
    assert make_batch.ad_prefix("Hobo Bag", "Evergreen", 1, 0).endswith("_B000")
    assert make_batch.ad_id(pre + "_S02_studio") == "S02_studio" and make_batch.ad_id(pre + "r2_P01_H3_day") == "P01_H3_day"
    # a redo: the free revision skips the names Drive already has, never the batch number
    taken = [pre + "_S01_hero.png"]
    assert make_batch.free_rev({("Hobo 2.0", "Evergreen")}, 1, taken, 45) == 2
    assert make_batch.free_rev({("Hobo 2.0", "Evergreen")}, 1, taken, 46) == 1


def test_folder_name():
    p = dict(batch_id=dict(id="B045", n=45), created="2026-10-20", product="Hobo Bag", theme_name="Evergreen", statics=["a"] * 5,
             projects=[1, 2, 3], videos=[])
    assert make_batch.folder_name(p, "") == "B045 – 2026-10-20 – Hobo Bag – 5 statics + 3 projects"
    assert make_batch.folder_name(dict(p, theme_name="BlackFriday"), "") == "B045 – 2026-10-20 – Hobo Bag BlackFriday – 5 statics + 3 projects"
    assert make_batch.folder_name(dict(p, batch_id=dict(id="B045r2", n=45)), "redo of P02") == "B045r2 – 2026-10-20 – redo of P02"
    assert make_batch.folder_name(dict(p, projects=[], videos=[]), "") == "B045 – 2026-10-20 – Hobo Bag – 5 statics"            # no empty "0 videos"
    assert make_batch.folder_name(dict(p, statics=[], projects=[], videos=[1, 2]), "") == "B045 – 2026-10-20 – Hobo Bag – 2 videos"
    old = dict(p, batch_id=dict(id="B000", n=0), request="2 statics")
    assert make_batch.folder_name(old, "") == "2026-10-20 – 2 statics"                     # outside the ledger: the old dated name


def test_repeats_are_found_in_the_ledger_and_the_novelty_log():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "l.json")
        b = ledger.reserve("Hobo Bag", "Evergreen", "catalog", "x", 2, 1, 4, 1, "2026-10-14", p=p)
        s1 = dict(layout="native", photo="photos/frames/F_abc_0042.jpg", caption="Gold Side Zips.")
        ledger.uploaded(b["n"], "B001 – x", "https://x", [dict(name="n1", kind="static", fp=ledger.static_fp(s1), label="Gold Side Zips."),
                                                          dict(name="v1", kind="video", fp=ledger.video_fp("Watch what the Hobo Bag can do."), label="")], p=p)
        fps = {"S01": ledger.static_fp(dict(s1, photo="photos/frames/F_abc_0042.jpg")),                       # the same static again
               "S02": ledger.static_fp(dict(s1, caption="Hidden Back Pocket.")),                                # another caption: not a repeat
               "P01_H1": ledger.video_fp("watch what the hobo bag can do.", ["other body"]),                    # the same hook line, any body
               "P01_H2": ledger.video_fp("A new opening.")}
        hit = dict(ledger.repeats("Hobo Bag", fps, p=p))
        assert set(hit) == {"S01", "P01_H1"} and hit["S01"].startswith("B001"), hit
        assert ledger.repeats("Vintage Bag", fps, p=p) == []                                                      # another product: never
        assert ledger.repeats("Hobo Bag", fps, exclude=1, p=p) == []                                              # the batch itself is not its own repeat
        nov = [dict(date="2026-10-09", statics=[dict(layout="studio", photo="hobo_bag_colour_red.jpg", caption="The Hobo Bag.")],
                    videos=[dict(hook="Is your bag keeping up?")])]
        fps2 = {"S03": ledger.static_fp(dict(layout="studio", photo="site/hobo_bag_colour_red.jpg", caption="The Hobo Bag.")),
                "P02_H1": ledger.video_fp("is your bag keeping up?")}
        assert [n for n, _ in ledger.repeats("Hobo Bag", fps2, nov, p=p)] == ["S03", "P02_H1"]                  # batches from before the ledger


def test_table_lists_every_batch():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "l.json")
        ledger.reserve("Hobo Bag", "Evergreen", "catalog", "x", 5, 3, 4, 1, "2026-10-20", p=p)
        t = ledger.table(ledger.load(p))
        assert t.count("\n") == 3 and "| B001 | 2026-10-20 | Hobo Bag |" in t


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
