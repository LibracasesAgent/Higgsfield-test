#!/usr/bin/env python3
"""The rulebook (owner 2026-11-05): the playbook checker on hooks / lines / ad copy, the footage / caption blocker (shotmatch.verify,
shotmatch.audit, storyboard.match_pick), the presenter count per batch and the weekly review (ingest, report, add, set).

  python3 pipeline/tests/test_playbook.py      # no network: temp files only; the real rulebook is read, never written
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import ideas  # noqa: E402
import playbook_check as pc  # noqa: E402
import shotmatch as sm  # noqa: E402


def ids(msgs):
    return {m[len("playbook "):].split(":")[0] for m in msgs}


def lint1(t, role="hook", **k):
    return pc.lint([dict(where="x", text=t, role=role, type=k.pop("type", None))], **k)


def test_hooks():
    P, W = lint1("Meet the bag everyone is talking about")
    assert {"meet_intro", "social_proof_invented", "hook_generic"} <= ids(P), P
    P, W = lint1("Still digging for your keys at the front door?", type="question")
    assert not P, P
    P, _ = lint1("Selling out fast, so grab yours.")
    assert "scarcity_invented" in ids(P)
    P, _ = lint1("Three reasons your keys sink to the bottom.", numbered=0)
    assert "count_delivered" in ids(P), P
    P, _ = lint1("Three reasons your keys sink to the bottom.", numbered=3)
    assert "count_delivered" not in ids(P)
    P, _ = lint1("Your keys have their own pocket now", type="question")
    assert "hook_type" in ids(P)
    P, _ = lint1("Where do your keys go when you pack tonight?", old_hooks=["Where do your keys go on a long day?"])
    assert "opener_reuse" in ids(P), P
    _, W = lint1("Her keys are at the bottom of the bag again.")
    assert "hook_third_person" in ids(W)


def test_lines_and_copy():
    P, _ = lint1("Sarah carried hers through Rome all summer.", role="chapter")
    assert "invented_customer" in ids(P)
    P, _ = lint1("If you've been pickpocketed before, this is for you.", role="chapter")
    assert "personal_attribute" in ids(P)
    P, _ = lint1("Now only $54.95 for the Hobo Bag", role="headline")
    assert "price_figure" in ids(P), P
    P, _ = lint1("The Hobo Bag with the hidden back pocket, now half price", role="headline")
    assert "copy_length" in ids(P), P
    P, _ = lint1("A verbatim review: best bag ever, selling out!", role="review")
    assert not P                                         # (a customer's own words: compliance.py judges them)


def test_claim_words_need_facts():
    import compliance
    v = compliance.context(ideas.product_of("Vintage Bag"))
    h2 = compliance.context(ideas.product_of("Hobo 2.0"))
    P, _ = lint1("Lockable zips keep your phone safe.", role="chapter", ctx=v)
    assert "claim_lockable" in ids(P), P
    P, _ = lint1("Lockable zips keep your phone safe.", role="chapter", ctx=h2)
    assert "claim_lockable" not in ids(P), P
    P, _ = lint1("The RFID lining blocks card scanners.", role="chapter", ctx=v)
    assert "claim_rfid" in ids(P)


def test_the_rulebook_reads_and_every_regex_compiles():
    R = pc.rules()
    assert R["_banned"] and R["_formulas"] and R["_claims"]
    assert R["kpi"]["hook_rate"]["target"][0] == 0.40 and R["kpi"]["roas"]["good"] >= 2.0
    for f in R["_formulas"]:
        assert pc.formula_of(f["example"]), f"the example of formula {f['id']} does not match it: {f['example']}"
    assert "Hook formulas" in pc.packet_section()


def test_presenters_per_batch():
    assert [ideas.presenters_wanted(n, "2026-11-05") for n in (1, 2, 3, 4, 5)] == [0, 1, 2, 2, 3]
    assert ideas.presenters_wanted(5, "2026-10-30") == 1              # an older sheet keeps its day's rule


def test_verify_and_audit():
    idx = {"CLIPA": [(2.0, {"strap", "worn"}, "good"), (9.0, {"snap", "handheld"}, "good")]}
    assert sm.verify(sm.shows("CLIPA", 1.0, 2.0, idx=idx), "One hand on the clasp, and it snaps shut.")[0] == "mismatch"
    assert sm.verify(sm.shows("CLIPA", 8.5, 2.0, idx=idx), "One hand on the clasp, and it snaps shut.")[0] == "ok"
    assert sm.verify(sm.shows("CLIPA", 1.0, 2.0, idx=idx), "Out the door on a sunny morning.")[0] == "ok"      # nothing specific
    assert sm.verify(sm.shows("photo.jpg", 0, 2.0, idx=idx), "The clasp snaps shut.")[0] == "unverified"
    assert sm.verify({"pocket", "zip_hand"}, "Smart compartments keep it all in place.")[0] == "ok"          # (ALSO: inside ~ pocket)
    assert "snap" not in sm.wants("Mid-morning, a coffee in one hand.")
    lf = dict(segments=[dict(src="CLIPA", start=1.0, dur=2.0), dict(src="CLIPA", start=8.5, dur=2.0), dict(src="talk/P01_c1.mp4", start=0, dur=2)],
              transcript=[dict(w="The", s=0.1, e=0.3), dict(w="clasp", s=0.3, e=0.8), dict(w="snaps", s=0.9, e=1.4), dict(w="shut.", s=1.4, e=1.9),
                          dict(w="Snap", s=2.2, e=2.6), dict(w="it", s=2.6, e=2.8), dict(w="shut.", s=2.8, e=3.4), dict(w="clasp", s=4.2, e=4.6)])
    rows = sm.audit(lf, idx=idx)
    assert [r["verdict"] for r in rows] == ["mismatch", "ok"], rows                # (the presenter's take is never judged)
    bad, _ = sm.audit_lines(rows)
    assert bad and bad[0].startswith("shot mismatch: 0.0s")


def test_render_swaps_a_pick_that_does_not_show_its_words():
    import storyboard as sb
    real = sm.moment_index
    sm.moment_index = lambda path=None: {"A": [(2.0, {"strap"}, "good")], "B": [(5.0, {"snap"}, "good")]}
    try:
        gp, spare = ["A", 1.0, 1.0], ["B", 4.0, 1.0]
        alt, lst = sb.match_pick(gp, "The clasp snaps shut with one hand.", 2.0, [[spare]])
        assert alt is spare and lst is not None
        alt, lst = sb.match_pick(gp, "Out the door in the morning.", 2.0, [[spare]])
        assert alt is gp and lst is None
    finally:
        sm.moment_index = real


def test_weekly_review_round_trip():
    import weekly_review as wr
    d = tempfile.mkdtemp()
    real = (wr.PERF, wr.RULEBOOK, wr.REVIEWS)
    try:
        wr.PERF, wr.RULEBOOK, wr.REVIEWS = os.path.join(d, "perf.json"), os.path.join(d, "rb.json"), os.path.join(d, "reviews")
        shutil.copy(pc.RULEBOOK, wr.RULEBOOK)
        f = os.path.join(d, "meta.csv")
        open(f, "w").write("Ad name,Amount spent (USD),Impressions,3-second video plays,ThruPlays,Link clicks,Purchases,Purchases conversion value\n"
                           "LC_261102_HoboBag_BlackFriday_B030_P01_H2_packtonight,50,4000,1800,400,160,2,190\n"
                           "LC_261102_HoboBag_BlackFriday_B030_P01_H3_packtonight,40,3000,600,90,60,0,0\n"
                           "Someone else's ad,10,900,10,1,1,0,0\n")
        rows = wr.ingest(f, "2026-11-02")
        assert len(rows) == 2 and rows[0]["hook_rate"] == 0.45 and rows[0]["hold_rate"] == 0.1 and rows[0]["hook"] == "H2" and rows[0]["batch"] == "B030"
        md = wr.report("2026-11-02")
        assert "hook WINS" in md and "hook loses" in md and os.path.exists(os.path.join(wr.REVIEWS, "2026-11-02.md"))
        wr.add("ban", "treat yourself", why="test", level="soft")
        wr.set_value("kpi.hook_rate.good", "0.42", why="test")
        R = json.load(open(wr.RULEBOOK))
        assert R["kpi"]["hook_rate"]["good"] == 0.42 and R["banned"]["rules"][-1]["id"] == "treat_yourself" and len(R["changelog"]) >= 3
    finally:
        wr.PERF, wr.RULEBOOK, wr.REVIEWS = real
        shutil.rmtree(d, ignore_errors=True)


TESTS = [test_hooks, test_lines_and_copy, test_claim_words_need_facts, test_the_rulebook_reads_and_every_regex_compiles,
         test_presenters_per_batch, test_verify_and_audit, test_render_swaps_a_pick_that_does_not_show_its_words, test_weekly_review_round_trip]


def main():
    bad = 0
    for t in TESTS:
        try:
            t()
            print("ok  ", t.__name__)
        except Exception as e:  # noqa: BLE001
            bad += 1
            print("FAIL", t.__name__, type(e).__name__, e)
    print(f"all passed ({len(TESTS)}/{len(TESTS)})" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
