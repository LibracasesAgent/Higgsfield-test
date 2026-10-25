"""Two runs started at the same time never take the same batch number (batch_lock.py, Drive faked), and a merge refuses two new
batches with one number (merge_batch.py). Run: python3 pipeline/tests/test_batch_lock.py"""
import contextlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import batch_lock  # noqa: E402
import ledger  # noqa: E402
import merge_batch  # noqa: E402


class FakeDrive:
    """Outputs with batch folders B019, B020, B025; the claims folder CL. `rival`: a claim another run writes the moment we write ours
    (with an earlier time: it got there first)."""
    def __init__(self, claims=(), rival=None):
        self.t = 100
        self.files = {"OUT": [dict(id=f"o{n}", name=f"B{n:03d} – 2026-10-25 – Hobo Bag", mimeType="application/vnd.google-apps.folder")
                              for n in (19, 20, 25)],
                      "CL": [dict(id=f"c{i}", name=n, createdTime=f"2026-10-25T08:{i:02d}:00Z") for i, n in enumerate(claims)]}
        self.rival = rival

    def list_children(self, tok, fid):
        return list(self.files.get(fid, []))

    def load_config(self):
        return {"drive": {"outputs_folder": "OUT"}}

    def api(self, method, url, tok, data=None, headers=None):
        body = json.loads(data or b"{}")
        if method == "POST":
            self.t += 1
            if self.rival:
                self.files["CL"].append(dict(id="rival", name=self.rival, createdTime=f"2026-10-25T09:00:{self.t - 1:02d}Z"))
                self.rival = None
            f = dict(id=f"m{self.t}", name=body["name"], createdTime=f"2026-10-25T09:00:{self.t:02d}Z")
            self.files["CL"].append(f)
        else:
            fid = url.split("/files/")[1].split("?")[0]
            f = next(x for x in self.files["CL"] if x["id"] == fid)
            f["name"] = body["name"]
        return contextlib.closing(io.BytesIO(json.dumps(f).encode()))


def claim(fake, local_next=21, product="Vintage Bag"):
    old = batch_lock.folder_id
    batch_lock.folder_id = lambda: "CL"
    try:
        return batch_lock.claim(local_next, product, "4 videos", du=fake, tok="t", settle=0)
    finally:
        batch_lock.folder_id = old


def test_the_next_number_after_everything_drive_knows():
    fake = FakeDrive()
    assert claim(fake) == 26                                    # after B025's folder, though this run's ledger says 21
    assert fake.files["CL"][-1]["name"].startswith("B026 – Vintage Bag")


def test_a_run_that_loses_the_race_takes_the_next_number():
    fake = FakeDrive(rival="B026 – Hobo Bag – 2026-10-25 – other-run")
    assert claim(fake) == 27 and batch_lock.LAST["lost"] == [26]
    names = [f["name"] for f in fake.files["CL"]]
    assert any(n.startswith("LOST B026 – Vintage Bag") for n in names) and any(n.startswith("B027 – Vintage Bag") for n in names)


def test_claims_not_in_drive_yet_count_and_show_as_running():
    fake = FakeDrive(claims=["B030 – Vintage Bag – 2026-10-25 – a", "LOST B031 – Hobo Bag – 2026-10-25 – b"])
    import datetime
    now = datetime.datetime(2026, 10, 25, 9, 30, tzinfo=datetime.timezone.utc)
    run = batch_lock.running(fake, "t", "CL", {19, 20, 25}, now=now)
    assert [r["n"] for r in run] == [30]                        # a LOST claim is not a batch being made
    assert claim(fake) == 32


def test_the_ledger_takes_the_claimed_number():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "ledger.json")
        b = ledger.reserve("Vintage Bag", "BlackFriday", "catalog", "x", 10, 4, 4, 1, "2026-10-25", p=p, claim=lambda nxt: 27)
        assert b["id"] == "B027" and ledger.load(p)["next"] == 28
        b = ledger.reserve("Hobo Bag", "BlackFriday", "catalog", "y", 10, 4, 4, 1, "2026-10-25", p=p, claim=lambda nxt: nxt)
        assert b["id"] == "B028"


def test_a_merge_refuses_two_new_batches_with_one_number():
    base = {"batches": [], "next": 26}
    ours = {"batches": [dict(n=26, rev=1, product="Hobo Bag", request="a")], "next": 27}
    theirs = {"batches": [dict(n=26, rev=1, product="Vintage Bag", request="b")], "next": 27}
    try:
        merge_batch.merge_ledger(base, ours, theirs)
        raise AssertionError("should have stopped")
    except merge_batch.Stop as e:
        assert "B026" in str(e)
    same = merge_batch.merge_ledger(base, ours, {"batches": [dict(ours["batches"][0], status="uploaded")], "next": 27})
    assert same["batches"][0]["status"] == "uploaded"           # the same batch, updated on the branch: fine


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
