"""Presenter (talking host) checks: the words of a take against its script, the prompts' skin wording, the host's files.
Run: python3 pipeline/tests/test_presenter.py"""
import difflib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import presenter  # noqa: E402


def match(script, heard):
    a, b = presenter.norm_words(script), presenter.norm_words(heard)
    return max(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(),
               difflib.SequenceMatcher(None, "".join(a), "".join(b), autojunk=False).ratio())


def test_a_transcript_that_spells_numbers_differently_still_matches():
    assert match("Retire the old one this Black Friday: fifty percent off the Hobo Bag.",
                 "Retire the old one this Black Friday 50 % off the Habo bag.") >= presenter.MATCH
    assert match("Myth two: side zips are just decoration.", "Myth 2, side zips are just decoration.") >= presenter.MATCH
    assert match("The leather is soft, water-resistant and expensive-looking, and there is a one-year warranty.",
                 "The leather is soft water resistant and expensive looking and there is a one -year warranty") >= presenter.MATCH
    assert match("free US shipping", "free U .S. shipping") >= presenter.MATCH


def test_other_words_do_not_match():
    assert match("Three people on your list, one gift that suits all of them.",
                 "This bag cures everything and ships to the moon in a day.") < presenter.MATCH


def test_take_seconds_stay_in_klings_range():
    assert presenter.take_seconds("Hi.") == presenter.MIN_D
    assert presenter.take_seconds("word " * 100) == presenter.MAX_D
    assert presenter.MIN_D <= presenter.take_seconds("Two straps let you carry it your way: on the shoulder, in your hand, or across your body.") <= presenter.MAX_D


def test_prompts_never_ask_for_pores_wrinkles_or_unretouched_skin():
    """Owner 2026-10-21: the first host looked fake (etched wrinkles, orange shiny skin) because the prompts asked for pores / fine lines / unretouched."""
    host = presenter.hosts()["maya"]
    sc = dict(where="She sits at a cafe table.", outfit="She wears a denim shirt.", ambience="Quiet cafe ambience")
    text = presenter.still_prompt(host, sc, "brown") + " " + presenter.take_prompt(host, sc, "Hello there.")
    low = text.lower()
    for bad in ("visible pores", "unretouched", "fine lines", "real skin texture", "real unretouched"):
        assert bad not in low, bad
    # (it may still say "no exaggerated pores": the wording that is banned is asking FOR them)
    assert "soft" in low and "natural" in low


def test_the_host_has_her_master_picture_and_voice():
    host = presenter.hosts()["maya"]
    assert os.path.exists(os.path.join(presenter.HERE, host["master"]))
    assert host["look"] and host["voice"] and host["soul_job"]


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
