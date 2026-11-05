"""The ad tracker sync (tracker.py, the simple one-tab format of 2026-11-05) builds a banner row per batch and a row per static /
video project, keeps what people typed and adds new batches, with Drive and the sheet faked.
Run: python3 pipeline/tests/test_tracker.py"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import tracker  # noqa: E402

FOLDER = tracker.FOLDER


class FakeDrive:
    """Outputs/{B030 – ..., Winners/B031 – ...}: B030 = a static, its motion video, a project of 2 hooks (one re-uploaded) and the
    strategy sheet; B031 = a winner video at the folder's top."""
    def __init__(self):
        self.kids = {
            "OUT": [dict(id="F30", name="B030 – 2026-11-02 – Vintage Bag BlackFriday – 1 statics + 1 projects", mimeType=FOLDER),
                    dict(id="WIN", name="Winners", mimeType=FOLDER)],
            "WIN": [dict(id="F31", name="B031 – 2026-11-06 – Hobo Bag – 0 statics + 1 projects", mimeType=FOLDER)],
            "F30": [dict(id="S30", name="Statics", mimeType=FOLDER), dict(id="V30", name="Videos", mimeType=FOLDER),
                    dict(id="sh", name="LC_261102_VintageBag_BlackFriday_B030_strategy_sheet.md", mimeType="text/markdown")],
            "S30": [dict(id="a", name="LC_261102_VintageBag_BlackFriday_B030_S01_studio.png", mimeType="image/png", createdTime="1"),
                    dict(id="m", name="LC_261102_VintageBag_BlackFriday_B030_S01_studio_motion.mp4", mimeType="video/mp4",
                         createdTime="1")],
            "V30": [dict(id="P30", name="P01 – giftlist", mimeType=FOLDER)],
            "P30": [dict(id="b", name="LC_261102_VintageBag_BlackFriday_B030_P01_H1_giftlist.mp4", mimeType="video/mp4", createdTime="1"),
                    dict(id="c", name="LC_261102_VintageBag_BlackFriday_B030_P01_H1_giftlist_upd0922.mp4", mimeType="video/mp4",
                         createdTime="2"),
                    dict(id="e", name="LC_261102_VintageBag_BlackFriday_B030_P01_H2_giftlist.mp4", mimeType="video/mp4", createdTime="1")],
            "F31": [dict(id="d", name="LC_261106_HoboBag_Evergreen_B031_P01_H1_remix94.mp4", mimeType="video/mp4", createdTime="1")],
        }

    def list_children(self, tok, fid):
        return [dict(f, webViewLink=f"https://drive.google.com/{'drive/folders' if f['mimeType'] == FOLDER else 'file/d'}/{f['id']}/view")
                for f in self.kids.get(fid, [])]

    def load_config(self):
        return {"drive": {"outputs_folder": "OUT"}}


def old_format_sheet():
    """The sheet as it was before 2026-11-05: the detailed tabs (nothing typed) + a tab people added."""
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.title = "Read me"
    for t in ("Batches", "Ads", "Summary", "Data Sources"):
        wb.create_sheet(t)
    j = wb.create_sheet("Julian")
    j["A1"], j["A2"] = "week 44", "=1+1"
    return _reload(wb)


def run_sync(start, batches=("B030",)):
    saved = {}
    fake = FakeDrive()
    import ledger
    old = (tracker.token, tracker.export, tracker.replace, tracker.load_cfg, ledger.load)
    ledger.load = lambda *a, **k: {"batches": [{"n": 30, "ads": [{"name": "LC_261102_VintageBag_BlackFriday_B030_S01_studio",
                                                                   "label": "Pick your colour."}]}]}
    tracker.token = lambda: (fake, "tok")
    tracker.export = lambda du, tok, sid: saved.get("wb") or start
    tracker.replace = lambda du, tok, sid, wb: saved.update(wb=_reload(wb))
    tracker.load_cfg = lambda: {"sheet_id": "S", "link": "L"}
    try:
        res = tracker.sync(list(batches), quiet=True)
    finally:
        tracker.token, tracker.export, tracker.replace, tracker.load_cfg, ledger.load = old
    return res, saved["wb"]


def _reload(wb):
    import openpyxl
    buf = io.BytesIO()
    wb.save(buf)
    return openpyxl.load_workbook(io.BytesIO(buf.getvalue()))


def rows(wb):
    ws = wb[tracker.TAB]
    head = [c.value for c in ws[1]]
    return head, [dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True) if any(v not in (None, "") for v in r)]


def test_first_sync_builds_the_simple_tab():
    res, wb = run_sync(old_format_sheet())
    assert wb.sheetnames == [tracker.TAB, "Julian"] and wb["Julian"]["A2"].value == "=1+1", wb.sheetnames     # old tabs gone, theirs kept
    head, rs = rows(wb)
    assert head == [h for h, _ in tracker.COLS], head
    banners = [r["Date"] for r in rs if not r["Key"]]
    assert banners == ["B031 · 06 Nov · Hobo Bag · 0 statics + 1 projects",                  # the newest batch on top
                       "B030 · 02 Nov · Vintage Bag · Black Friday · 1 statics + 1 projects"], banners
    s01 = next(r for r in rs if r["Key"] == "B030|LC_261102_VintageBag_BlackFriday_B030_S01_studio")
    assert s01["Project"] == "B030 S01 · studio" and s01["Holiday"] == "Black Friday" and s01["Script"] == "Pick your colour."
    assert '"Open"' in s01["Link"] and "/a/" in s01["Link"] and "📁 B030" in s01["Drive"] and s01["Status"] == "✅ Ready"
    mo = next(r for r in rs if (r["Key"] or "").endswith("_motion"))
    assert mo["Project"] == "B030 S01 · studio · motion video" and mo["Script"] == "Pick your colour."
    p01 = next(r for r in rs if r["Key"] == "B030|P01")
    assert p01["Project"] == "B030 P01 · giftlist · 2 hooks" and "folders/P30" in p01["Link"] and '"Script (P01)"' in p01["Script"]
    order = [r["Key"] or r["Date"] for r in rs]
    assert order.index(s01["Key"]) < order.index(mo["Key"]) < order.index("B030|P01"), order          # statics, motion, projects
    b31 = next(r for r in rs if r["Key"] == "B031|P01")
    assert b31["Status"] == "🔍 Review" and b31["Holiday"] is None and "/d/" in b31["Link"]    # new batch: review first; no folder
    assert res["batches_added"] == ["B030", "B031"] and res["ads"] == 4, res


def test_typed_values_and_hand_rows_are_kept():
    _, wb = run_sync(old_format_sheet())
    ws = wb[tracker.TAB]
    head = [c.value for c in ws[1]]
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=head.index("Key") + 1).value == "B030|P01":
            ws.cell(row=r, column=head.index("Launched (Meta)") + 1, value="✅ Launched")
            ws.cell(row=r, column=head.index("Meta status") + 1, value="🔵 Promising")
            ws.cell(row=r, column=head.index("Insights") + 1, value="hook rate 32%: try new hooks")
            ws.cell(row=r, column=head.index("Status") + 1, value="✅ Ready")
    ws.cell(row=ws.max_row + 2, column=2, value="Julian's own test")      # a row people added by hand
    res, wb2 = run_sync(_reload(wb))
    _, rs = rows(wb2)
    p01 = next(r for r in rs if r["Key"] == "B030|P01")
    assert (p01["Launched (Meta)"], p01["Meta status"], p01["Insights"]) == ("✅ Launched", "🔵 Promising", "hook rate 32%: try new hooks")
    assert any(r["Project"] == "Julian's own test" for r in rs) and any(r["Date"] == tracker.HAND for r in rs)
    assert res["ads_added"] == 0 and res["batches_added"] == [], res


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
