#!/usr/bin/env python3
"""Tests of the real-footage work (owner 2026-10-20: use the footage we have): footage_index.py (notes, verdicts, the frame bank's
clip pool), the static cycle with footage frames, and the 'day' story angle of ugc_script.py.

  python3 pipeline/tests/test_footage.py      # no network, no Drive: temp files only
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import footage_index as fi  # noqa: E402
import make_batch  # noqa: E402
import ugc_script  # noqa: E402


def test_note_and_colour_come_from_the_clients_names():
    p = "Raw files/Hobo Bag/Black hobo - stairs / pouch lip stick / open zips/IMG_6849.MOV"
    assert fi.note_of("Hobo Bag", p) == "Black hobo - stairs / pouch lip stick / open zips"
    assert fi.colour_of(p) == "black"
    assert fi.colour_of("Hobo Bag/Brown - coffeeshop") == "brown"
    assert fi.colour_of("Hobo Bag/clip") == ""


def frame(faces=0, sharp=200.0, bright=120.0):
    return dict(faces=faces, sharp=sharp, bright=bright)


def test_verdict():
    ok = dict(width=2160, height=3840, duration=12.0, frames=[frame()] * 4)
    assert fi.verdict(ok) == ("none", "yes", "")
    assert fi.verdict(dict(ok, frames=[frame(faces=1)] + [frame()] * 3))[:2] == ("partial", "no")
    assert fi.verdict(dict(ok, frames=[frame(faces=1)] * 3 + [frame()]))[:2] == ("full", "no")
    assert fi.verdict(dict(ok, width=640, height=360))[1:] == ("no", "under 720p")
    assert fi.verdict(dict(ok, duration=1.2))[1:] == ("no", "under 2.5 s")
    assert fi.verdict(dict(ok, frames=[frame(sharp=5)] * 4))[1] == "no"
    assert fi.verdict(dict(ok, frames=[frame(bright=10)] * 4))[1] == "no"
    assert fi.verdict(dict(ok, error="no duration", frames=[]))[1] == "no"


def test_bank_rows_take_only_clean_vertical_clips():
    rows = [
        dict(id="A" * 22, product="Hobo Bag", usable="yes", faces="none", text="none", width=2160, height=3840, duration=9, path="Hobo Bag/a"),
        dict(id="B" * 22, product="Hobo Bag", usable="yes", faces="none", text="none", width=3840, height=2160, duration=9, path="Hobo Bag/b"),
        dict(id="C" * 22, product="Hobo Bag", usable="yes", faces="partial", text="none", width=2160, height=3840, duration=9, path="Hobo Bag/c"),
        dict(id="D" * 22, product="Hobo Bag", usable="yes", faces="none", text="none", width=720, height=1280, duration=9, path="Hobo Bag/d"),
        dict(id="E" * 22, product="Hobo Bag", usable="yes", faces="none", text="none", width=2160, height=3840, duration=9,
             path="ACH Creative Delivery/Concept 113/RAW/e"),
        dict(id="F" * 22, product="Hobo 2.0", usable="yes", faces="none", text="none", width=2160, height=3840, duration=9, path="Hobo 2.0/f"),
    ]
    with tempfile.TemporaryDirectory() as d:
        old = fi.INDEX
        fi.INDEX = os.path.join(d, "idx.json")
        json.dump(rows, open(fi.INDEX, "w"))
        try:
            assert [r["id"][0] for r in fi.bank_rows("Hobo Bag")] == ["A"]          # vertical, no face, 1080+, not a winner's RAW
            assert fi.bank_rows("Hobo Bag", avoid=["A" * 22]) == []
        finally:
            fi.INDEX = old


def test_static_cycle_with_frames():
    seq = make_batch.static_cycle(True, True, False, False, 9)
    assert len(seq) == 20 and seq.count("native") == 8 and seq.count("studio") == 4, seq
    assert seq.count("bold") + seq.count("compare") + seq.count("promo") == 0                  # the text-heavy ones are gone
    assert make_batch.static_cycle(True, True, False, False, 0) != seq                         # no frames: the earlier clean cycle
    classic = make_batch.static_cycle(True, True, False, True, 9)
    assert classic == make_batch.static_cycle(True, True, False, True, 0)                      # --classic: unchanged


def test_media_cache_is_trimmed_oldest_first_and_keeps_what_is_in_use():
    import time
    import recut
    with tempfile.TemporaryDirectory() as d:
        old_dir = recut.MEDIA_CACHE
        recut.MEDIA_CACHE = d
        try:
            now = time.time()
            ids = [chr(ord("A") + i) * 22 for i in range(4)]
            for k, n in enumerate(ids):                 # A oldest ... D newest: 1 MB each, A-C an hour old or more, D just now
                f = os.path.join(d, n)
                open(f, "wb").write(b"x" * 2**20)
                os.utime(f, (now - 7200 + k * 600, now - 7200 + k * 600) if k < 3 else (now, now))
            open(os.path.join(d, "voice.mp3"), "wb").write(b"x" * 2**20)       # not a Drive id: never dropped
            gone = recut.trim_cache(cap=2.5 * 2**20)
            left = sorted(os.listdir(d))
            assert gone == 2 and left == [ids[2], ids[3], "voice.mp3"], (gone, left)
            assert recut.trim_cache(cap=0) == 1 and os.path.exists(os.path.join(d, ids[3])) is True     # D is in use (just now): stays
        finally:
            recut.MEDIA_CACHE = old_dir


def product(name):
    M = ugc_script.mb()
    files = M.product_files(M.products_dir())
    w = []
    return M.honest(M.product(M.pick_product(name, files), files, w), w)


def test_day_angle_is_a_story_that_follows_the_footage():
    pr = product("Hobo Bag")
    sc = [s for s in ugc_script.scripts(pr, n=6, seed=1) if s["angle"] == "day"]
    assert sc, "a batch of 6 has the day story"
    s = sc[0]
    beats = [c for c in s["chapters"] if c["kind"] == "point"]
    assert len(beats) >= 4
    moments = {w for b in ugc_script.data("ugc_arcs.json")["day"] for w in b["when"]}
    assert all(any(b["text"].startswith(m) for m in moments) for b in beats), [b["text"] for b in beats]   # each opens on its moment
    assert all(set(c["shot_kw"]) & {"door", "room", "walk", "outside", "strap", "cafe", "coffee", "table", "chair", "stairs", "zip",
                                    "inside", "hand", "hanging", "hero", "shoulder"} for c in beats)       # footage words of that place
    ctx = ugc_script.context(pr)
    assert not ugc_script.lint(s, pr, ctx), ugc_script.lint(s, pr, ctx)


def test_last_batchs_angles_go_to_the_end_of_the_cycle():
    pr = product("Hobo Bag")
    first = [s["angle"] for s in ugc_script.scripts(pr, n=5, seed=1)]
    second = [s["angle"] for s in ugc_script.scripts(pr, n=5, seed=1, avoid=dict(angles=first))]
    assert first[0] == "day" and len(set(first)) == 5
    assert set(second) != set(first), (first, second)           # 5 of 6 angles each time: the one left out comes in


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
