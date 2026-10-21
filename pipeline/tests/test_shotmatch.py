#!/usr/bin/env python3
"""Tests of shotmatch.py (what a phrase asks the picture for, what a labelled moment shows) and the labels merge.

  python3 pipeline/tests/test_shotmatch.py      # no network: temp files only
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import footage_index as fi  # noqa: E402
import shotmatch as sm  # noqa: E402


def test_phrase_wants():
    w = sm.wants("Snap the clasp shut with one hand.")
    assert w == {"snap": 5}, w
    w = sm.wants("Keys go in one gold side zip, phone in the other.")
    assert {"side_zip", "zip", "packing"} <= set(w) and "leather" not in w, w          # ('gold' is the zip here, not the leather)
    assert "snap" not in sm.wants("Open it, close it, move on.")                       # ('close' alone is not the clasp)
    assert "zip_hand" not in sm.wants("Open the app.")                                  # 'open' counts only with a zip / snap / pocket word
    w = sm.wants("Out the door in a hurry?", feature="HIDDEN BACK POCKET")
    assert w["pocket"] == 4 * sm.CHAPTER_SHARE and w["door"] == 2, w                    # the chapter's feature rides along at a share
    assert sm.wants("Anything.", show=["snap"])["snap"] == 5 * sm.CHAPTER_SHARE        # a strategist's own cue


def test_score_prefers_what_is_said():
    want = sm.wants("Snap the clasp shut with one hand.")
    clasp, strap = {"snap", "handheld"}, {"strap", "worn"}
    assert sm.score(clasp, want) > sm.score(strap, want)
    assert sm.score(strap, want) < 0                                                    # a specific line and a shot that shows none of it
    assert sm.score(clasp, want, "weak") < sm.score(clasp, want, "good")
    assert sm.score(strap, {}) == 0.0                                                   # nothing asked: any good shot


def test_label_merge_writes_moments_with_frame_times():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "out"))
        idx = os.path.join(d, "idx.json")
        json.dump([dict(id="A" * 22, product="Hobo Bag", duration=8.0, usable="yes")], open(idx, "w"))
        json.dump(dict(sheets=[], clips={"c001": dict(id="A" * 22, product="Hobo Bag", path="x", duration=8.0)}), open(os.path.join(d, "manifest.json"), "w"))
        fr = [dict(k=k, tags=["snap", "not_a_tag"], q="good" if k < 3 else "weird", desc="d") for k in range(4)]
        open(os.path.join(d, "out", "a1.jsonl"), "w").write(json.dumps(dict(key="c001", frames=fr)) + "\n")
        old = fi.INDEX
        fi.INDEX = idx
        try:
            class A:
                pass
            a = A()
            a.dir = d
            fi.cmd_label_merge(a)
            m = json.load(open(idx))[0]["moments"]
        finally:
            fi.INDEX = old
        assert [x["t"] for x in m] == [1.0, 3.0, 5.0, 7.0], m                           # 12.5 / 37.5 / 62.5 / 87.5 % of 8 s
        assert m[0]["tags"] == ["snap"] and m[3]["q"] == "weak"                         # (only the vocabulary; an odd quality is weak)


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
