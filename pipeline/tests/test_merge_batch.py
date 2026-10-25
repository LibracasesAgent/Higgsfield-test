"""merge_batch.py merges a run's batch branch into the default branch, settling the ledger / novelty log / BATCHES.md clashes
and refusing branches that change more than batch output. A throwaway git repo, no remote.
Run: python3 pipeline/tests/test_merge_batch.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import merge_batch  # noqa: E402


def sh(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout


def write(repo, path, data):
    p = os.path.join(repo, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(data if isinstance(data, str) else json.dumps(data, indent=1) + "\n")


def batch(n, product):
    return dict(id=f"B{n:03d}", n=n, rev=1, date="2026-10-25", product=product, theme="BlackFriday", status="uploaded",
                folder=f"B{n:03d} – 2026-10-25 – {product}", link="", ads=[])


def repo_with_two_runs():
    """main has B001 and then B002; the branch 'run' was cut before B002 and made B003."""
    r = tempfile.mkdtemp(prefix="mb_test_")
    sh(r, "init", "-q", "-b", "main")
    sh(r, "config", "user.email", "t@t")
    sh(r, "config", "user.name", "t")
    write(r, merge_batch.LEDGER, {"batches": [batch(1, "Hobo Bag")], "next": 2})
    write(r, merge_batch.NOVELTY, {"products": {"hobo-bag": {"batches": [{"name": "B001 – Hobo Bag", "statics": []}]}}})
    write(r, merge_batch.BATCHES_MD, "# Batches (B-numbers)\n\nintro\n\n| Batch | Date |\n|---|---|\n| B001 | 2026-10-25 |\n")
    write(r, "pipeline/clip_index.json", "[]\n")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "-m", "base")
    sh(r, "checkout", "-q", "-b", "run")
    write(r, merge_batch.LEDGER, {"batches": [batch(1, "Hobo Bag"), batch(3, "Vintage Bag")], "next": 4})
    write(r, merge_batch.NOVELTY, {"products": {"hobo-bag": {"batches": [{"name": "B001 – Hobo Bag", "statics": []}]},
                                                "vintage-bag": {"batches": [{"name": "B003 – Vintage Bag", "statics": ["x"]}]}}})
    write(r, merge_batch.BATCHES_MD, "# Batches (B-numbers)\n\nintro\n\n| Batch | Date |\n|---|---|\n| B001 | 2026-10-25 |\n| B003 | x |\n")
    write(r, "pipeline/recipes/daily/2026-10-25/vintage/LC_261025_VintageBag_BlackFriday_B003_P01_H1_gift.json", {"a": 1})
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "-m", "B003")
    sh(r, "checkout", "-q", "main")
    write(r, merge_batch.LEDGER, {"batches": [batch(1, "Hobo Bag"), batch(2, "Hobo Bag")], "next": 3})
    write(r, merge_batch.NOVELTY, {"products": {"hobo-bag": {"batches": [{"name": "B001 – Hobo Bag", "statics": []},
                                                                         {"name": "B002 – Hobo Bag", "statics": []}]}}})
    write(r, merge_batch.BATCHES_MD, "# Batches (B-numbers)\n\nintro\n\n| Batch | Date |\n|---|---|\n| B001 | 2026-10-25 |\n| B002 | y |\n")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "-m", "B002")
    return r


def merged(r, res, path):
    return sh(r, "show", f"{res['commit']}:{path}")


def test_two_runs_merge_with_every_batch_kept():
    r = repo_with_two_runs()
    res = merge_batch.merge("run", repo=r, default="main", remote="", fetch=False, say=lambda *a: None)
    assert res["status"] == "merged" and res["batches"] == ["B003"], res
    led = json.loads(merged(r, res, merge_batch.LEDGER))
    assert [b["id"] for b in led["batches"]] == ["B001", "B002", "B003"] and led["next"] == 4
    nov = json.loads(merged(r, res, merge_batch.NOVELTY))["products"]
    assert [b["name"] for b in nov["hobo-bag"]["batches"]] == ["B001 – Hobo Bag", "B002 – Hobo Bag"]
    assert nov["vintage-bag"]["batches"][0]["statics"] == ["x"]
    md = merged(r, res, merge_batch.BATCHES_MD)
    assert "<<<<<<<" not in md and md.startswith("# Batches (B-numbers)\n\nintro") and all(f"| B00{n} |" in md for n in (1, 2, 3))
    assert "B003_P01_H1_gift" in sh(r, "show", "--name-only", "--format=", res["commit"]) or \
        merged(r, res, "pipeline/recipes/daily/2026-10-25/vintage/LC_261025_VintageBag_BlackFriday_B003_P01_H1_gift.json")
    assert merge_batch.merge("main", repo=r, default="main", remote="", fetch=False, say=lambda *a: None)["status"] == "already"


def test_a_branch_with_code_changes_is_left_for_a_person():
    r = repo_with_two_runs()
    sh(r, "checkout", "-q", "run")
    write(r, "pipeline/make_batch.py", "print('changed')\n")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "-m", "code")
    sh(r, "checkout", "-q", "main")
    res = merge_batch.merge("run", repo=r, default="main", remote="", fetch=False, say=lambda *a: None)
    assert res["status"] == "skipped" and res["outside"] == ["pipeline/make_batch.py"]


def test_a_clash_it_cannot_settle_stops_it():
    r = repo_with_two_runs()
    for br, val in (("run", "[1]\n"), ("main", "[2]\n")):
        sh(r, "checkout", "-q", br)
        write(r, "pipeline/data/clip_index.json", val)
        sh(r, "add", "-A")
        sh(r, "commit", "-q", "-m", f"clip index {br}")
    try:
        merge_batch.merge("run", repo=r, default="main", remote="", fetch=False, say=lambda *a: None)
        raise AssertionError("should have stopped")
    except merge_batch.Stop as e:
        assert "clip_index.json" in str(e)
    assert sh(r, "status", "--porcelain") == "" and len(sh(r, "worktree", "list").splitlines()) == 1     # nothing left behind


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
