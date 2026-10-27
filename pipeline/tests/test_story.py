#!/usr/bin/env python3
"""The videos are stories (owner 2026-10-27): the story structure library, the sheet check's story rules (at most 3 features, a
different lead feature per project, the price only at the end, hooks that open on four different pictures of the bag doing something,
a proof shot, people in the footage, one presenter per batch of 2+, structures new every batch) and the sheet -> scripts fields.
Run: python3 pipeline/tests/test_story.py   (fixture: tests/story_sheet.json; the novelty log is replaced by an empty one)"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ideas  # noqa: E402
import novelty  # noqa: E402

SHEET = os.path.join(HERE, "story_sheet.json")
PR = []


def pr():
    if not PR:
        PR.append(ideas.product_of("Hobo Bag"))
    return PR[0]


def sheet():
    return json.load(open(SHEET))


def problems(s, log=None, day="2026-10-27"):
    real = novelty.load
    novelty.load = lambda *a, **k: copy.deepcopy(log or {"products": {}})
    try:
        P, _ = ideas.check(s, pr(), day=day)
    finally:
        novelty.load = real
    return P


def has(P, *words):
    return any(all(w in p for w in words) for p in P)


def test_the_library_and_the_fixture():
    sl = ideas.structures()
    assert len(sl["structures"]) >= 8 and sl["rules"]
    for x in sl["structures"].values():
        ids = [b["id"] for b in x["beats"]]
        assert ids[-1] == "offer" and any(b.get("proof") for b in x["beats"]) and len(x["shape"]) >= 60, x["id"]
    assert problems(sheet()) == [], problems(sheet())


def test_a_feature_list_is_refused():
    s = sheet()
    c = s["projects"][0]["chapters"]
    c.insert(5, dict(kind="point", beat="second_move", text="Inside, divided compartments, and soft leather that only gets better.",
                     tag="SMART COMPARTMENTS", show=["inside", "worn"]))
    assert has(problems(s), "features", "at most 3")


def test_the_price_only_at_the_end_and_one_price_hook():
    s = sheet()
    s["projects"][0]["chapters"][1]["text"] += " And it is fifty percent off."
    s["projects"][0]["hooks"][0].update(text="Half price, and your card is out of sight.", type="price")
    P = problems(s)
    assert has(P, "c2", "only in the last chapter") and has(P, "H1", "H4", "one price hook"), P


def test_hooks_open_on_four_different_pictures_of_the_bag_doing_something():
    s = sheet()
    h = s["projects"][0]["hooks"]
    h[1]["show"] = ["hero"]
    h[2]["show"] = ["pocket"]
    P = problems(s)
    assert has(P, "H2", "opens on 'hero'") and has(P, "same picture"), P


def test_a_proof_shot_and_people():
    s = sheet()
    for c in s["projects"][0]["chapters"]:
        c.pop("proof_shot", None)
        c["show"] = [t for t in c["show"] if t not in ("worn", "walking")] or ["home"]
    P = problems(s)
    assert has(P, "0 proof shots") and has(P, "on a person"), P
    s = sheet()
    s["projects"][0]["chapters"][2]["show"] = ["home", "worn"]
    assert has(problems(s), "needs a movement")


def test_beats_follow_the_structure():
    s = sheet()
    s["projects"][0]["chapters"][0]["beat"] = "climax"
    assert has(problems(s), "'climax' is not one of")
    s = sheet()
    c = s["projects"][0]["chapters"]
    c[0]["beat"], c[2]["beat"] = c[2]["beat"], c[0]["beat"]
    assert has(problems(s), "out of")
    s = sheet()
    s["projects"][0]["structure"] = "unknown_thing"
    assert has(problems(s), "structure: one of")
    s["projects"][0].update(structure_name="Late train", shape="A single late train told from the platform to the door, one small worry "
                                                                 "solved at each stop on the way home.")
    assert not has(problems(s), "structure: one of")


def test_a_batch_of_two():
    s = sheet()
    p2 = copy.deepcopy(s["projects"][0])
    p2.update(id="P02", slug="platform2", title="Another platform story", big_idea="A different story entirely about an evening out at dinner.")
    s["projects"].append(p2)
    P = problems(s)
    assert has(P, "'one_moment' is used 2 times") and has(P, "lead with HIDDEN BACK POCKET") and has(P, "carries the presenter"), P
    s["no_presenter"] = "the request says: no presenter"
    assert not has(problems(s), "carries the presenter")


def test_new_structures_every_batch_and_old_sheets_keep_their_rules():
    last = {"products": {"hobo-bag": {"batches": [{"date": "2026-10-26", "name": "B030", "videos": [{"structure": "one_moment"}]}]}}}
    assert has(problems(sheet(), last), "was in Hobo Bag's last batch")
    s = sheet()
    for c in s["projects"][0]["chapters"]:
        c.pop("proof_shot", None)
    assert not has(problems(s, day="2026-10-26"), "proof shot")


def test_scripts_carry_the_structure_the_proof_and_the_pace():
    sc = ideas.scripts(sheet(), pr(), 4)[0]
    chs = sc["chapters"]
    assert sc["structure"] == "one_moment"
    assert chs[2].get("proof") and not chs[1].get("proof")
    assert chs[0].get("pace") == "slow" and chs[3].get("pace") == "fast" and "pace" not in chs[1]


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
