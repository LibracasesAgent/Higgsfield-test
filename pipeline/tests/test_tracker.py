"""The ad tracker sync (tracker.py) keeps what people typed and adds new batches, with Drive and the sheet faked.
Run: python3 pipeline/tests/test_tracker.py"""
import datetime
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import tracker  # noqa: E402

FOLDER = tracker.FOLDER


class FakeDrive:
    """Outputs/{B030 – ..., Winners/B031 – ...} with a static and two videos each."""
    def __init__(self):
        self.kids = {
            "OUT": [dict(id="F30", name="B030 – 2026-11-02 – Vintage Bag BlackFriday – 1 statics + 1 projects", mimeType=FOLDER),
                    dict(id="WIN", name="Winners", mimeType=FOLDER)],
            "WIN": [dict(id="F31", name="B031 – 2026-11-03 – Hobo Bag BlackFriday – 0 statics + 1 projects", mimeType=FOLDER)],
            "F30": [dict(id="S30", name="Statics", mimeType=FOLDER), dict(id="V30", name="Videos", mimeType=FOLDER)],
            "S30": [dict(id="a", name="LC_261102_VintageBag_BlackFriday_B030_S01_studio.png", mimeType="image/png", createdTime="1")],
            "V30": [dict(id="P30", name="P01 – giftlist", mimeType=FOLDER)],
            "P30": [dict(id="b", name="LC_261102_VintageBag_BlackFriday_B030_P01_H1_giftlist.mp4", mimeType="video/mp4", createdTime="1"),
                    dict(id="c", name="LC_261102_VintageBag_BlackFriday_B030_P01_H1_giftlist_upd0922.mp4", mimeType="video/mp4",
                         createdTime="2")],
            "F31": [dict(id="d", name="LC_261103_HoboBag_BlackFriday_B031_P01_H1_remix94.mp4", mimeType="video/mp4", createdTime="1")],
        }

    def list_children(self, tok, fid):
        return [dict(f, webViewLink=f"https://drive.google.com/file/d/{f['id']}/view") for f in self.kids.get(fid, [])]

    def load_config(self):
        return {"drive": {"outputs_folder": "OUT"}}


def sheet_with_typed_values():
    """A tracker that already lists B030 (one ad), with a result typed, a column and a tab people added."""
    bhead = [h for h, _ in tracker.BATCH_COLS]
    ahead = [h for h, _ in tracker.AD_COLS]
    ahead.insert(ahead.index("Verdict"), "Placement")                       # a column people inserted in the middle
    brows = [{"Batch": "B030", "Delivered": datetime.date(2026, 11, 2), "Product": "Vintage Bag", "Notes": "our own note",
              "Status": "Launched", "Takeaways": "gift angle works"}]
    arows = [{"Batch": "B030", "Ad name": "LC_261102_VintageBag_BlackFriday_B030_S01_studio", "Type": "Static", "File": "",
              "Launched": "Yes", "Spend ($)": 120.5, "Purchases": 4, "Revenue ($)": 290, "Placement": "Reels", "Verdict": "Winner"}]
    wb = tracker.build(bhead, brows, ahead, arows, [("Julian", {(1, 1): "week 44", (2, 1): "=Ads!O2"})], "test")
    buf = io.BytesIO()
    wb.save(buf)
    import openpyxl
    return openpyxl.load_workbook(io.BytesIO(buf.getvalue()))


def run_sync():
    saved = {}
    fake = FakeDrive()
    old = (tracker.token, tracker.export, tracker.replace, tracker.load_cfg)
    tracker.token = lambda: (fake, "tok")
    tracker.export = lambda du, tok, sid: saved.get("wb") or sheet_with_typed_values()
    tracker.replace = lambda du, tok, sid, wb: saved.update(wb=_reload(wb))
    tracker.load_cfg = lambda: {"sheet_id": "S", "link": "L"}
    try:
        res = tracker.sync(["B030"], quiet=True)
    finally:
        tracker.token, tracker.export, tracker.replace, tracker.load_cfg = old
    return res, saved["wb"]


def _reload(wb):
    import openpyxl
    buf = io.BytesIO()
    wb.save(buf)
    return openpyxl.load_workbook(io.BytesIO(buf.getvalue()))


def test_sync_keeps_typed_values_and_adds_new_batches():
    res, wb = run_sync()
    assert res["batches_added"] == ["B031"] and res["ads_added"] == 2 and res["ads_refreshed"] == 1, res
    bhead, brows = tracker.read_tab(wb, "Batches", tracker.BATCH_COLS)
    ahead, arows = tracker.read_tab(wb, "Ads", tracker.AD_COLS)
    b30 = next(r for r in brows if r["Batch"] == "B030")
    assert b30["Status"] == "Launched" and b30["Takeaways"] == "gift angle works" and b30["Notes"] == "our own note"
    assert b30["Theme"] == "Black Friday" and "drive.google.com" in str(b30["Drive folder"])            # file details filled in
    b31 = next(r for r in brows if r["Batch"] == "B031")
    assert b31["Pipeline"] == "winners" and b31["Product"] == "Hobo Bag"
    s01 = next(r for r in arows if r["Ad name"].endswith("S01_studio"))
    assert (s01["Launched"], s01["Spend ($)"], s01["Placement"], s01["Verdict"]) == ("Yes", 120.5, "Reels", "Winner")
    assert ahead.index("Placement") == ahead.index("Verdict") - 1                                        # where people put it
    video = [r for r in arows if r["Ad name"].endswith("P01_H1_giftlist")]
    assert len(video) == 1 and "/c/" in str(video[0]["File"]) and video[0]["Angle / layout"] == "giftlist"   # newest copy only
    assert wb.sheetnames[:5] == list(tracker.OURS) and wb["Julian"]["A2"].value == "=Ads!O2"


def test_formulas_follow_the_columns_people_moved():
    _, wb = run_sync()
    ahead = [c.value for c in wb["Ads"][1]]
    from openpyxl.utils import get_column_letter as L
    spend, rev = L(ahead.index("Spend ($)") + 1), L(ahead.index("Revenue ($)") + 1)
    roas = wb["Ads"].cell(row=2, column=ahead.index("ROAS") + 1).value
    assert roas == f'=IF({spend}2=0,"",{L(ahead.index("Revenue ($)") + 1)}2/{spend}2)', roas
    verdict = L(ahead.index("Verdict") + 1)
    assert f"Ads!${verdict}:${verdict}" in wb["Batches"].cell(row=2, column=19).value


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
