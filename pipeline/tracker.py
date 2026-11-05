#!/usr/bin/env python3
"""The ad tracker: one Google Sheet in Drive (Ad Creative Pipeline / "Libra Cases – Ad Tracker", data/tracker.json), one simple tab
in the media buyer's own format (Julian 2026-11-04: "more like this, a bit more easy, not too many columns"):

  Date | Project | Holiday | Link | Drive | Script | Status | Launched (Meta) | Meta status | Insights

A blue banner row per batch, the newest on top ("B037 · 04 Nov · Hobo Bag · Black Friday · 25 statics"), then one row per static (its file) and one per
video project (its folder: the 4 hook versions of one body, the ad set Julian launches), a motion still's video its own row. We fill
Date to Script and set Status ("🔍 Review" for a new batch: both sides look at it before launch; "✅ Ready" when it may go live); Julian
fills Launched (Meta), Meta status and Insights. A hidden Key column (B037|<ad name> / B037|P01) finds each row again.

`make_batch.py upload` calls sync() at the end of every upload, so each Slack / Claude DM run adds its batch by itself. A sync also
adds every B-numbered batch folder in Drive Outputs (Winners/ and New Products/ too) the sheet does not list yet, and re-lists the
batches of the last 3 days (re-rendered videos, late uploads).

The pipeline's Google login has the Drive scope only (the Sheets API is off in its Cloud project), so a sync rewrites the whole
file: it exports the sheet, keeps every value people typed (Status, Launched, Meta status, Insights, columns they added, rows they
added by hand, their own tabs), refreshes the file details of the batches it syncs and replaces the file's content. The link stays
the same. Cell colours or comments people add by hand are not kept; an edit typed in the few seconds a sync runs can be lost. The
first sync of this format replaces the old detailed tabs (Read me, Batches, Ads, Summary, Data Sources: nobody had typed in them).

  python3 pipeline/tracker.py show                      the sheet's link and row counts
  python3 pipeline/tracker.py sync [--batch B026]      add / refresh that batch (+ every batch in Drive the sheet lacks)
  python3 pipeline/tracker.py sync --all               refresh the file details of every batch (slow: crawls every folder)
"""
import argparse
import contextlib
import datetime
import io
import json
import os
import re
import sys
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "data", "tracker.json")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FOLDER = "application/vnd.google-apps.folder"

TAB = "Tracker"
LEGACY = ("Read me", "Batches", "Ads", "Summary", "Data Sources")     # the old detailed tabs: replaced by TAB
# (header, kind): d = details we fill (refreshed from Drive / the ledger), in = typed by people (kept), k = the hidden row key
COLS = [("Date", "d"), ("Project", "d"), ("Holiday", "d"), ("Link", "d"), ("Drive", "d"), ("Script", "d"), ("Status", "in"),
        ("Launched (Meta)", "in"), ("Meta status", "in"), ("Insights", "in"), ("Key", "k")]
STATUS = {"✅ Ready": "D9EAD3", "🔍 Review": "FFF2CC", "🛠 Needs fix": "F4CCCC", "⛔ Skip": "E7E6E6"}
LAUNCHED = {"✅ Launched": "D9EAD3", "Not launched": "E7E6E6"}
META = {"✅ Winner": "D9EAD3", "⏸ Winner (paused)": "D9EAD3", "🔵 Promising": "CFE2F3", "▶ Running": "FFF2CC", "❌ No hit": "F4CCCC",
        "⚪ No delivery": "EFEFEF"}
REVIEW_FROM = "2026-11-05"      # batches delivered from this day start as Review (Julian 2026-11-04: a visual review before launch);
#                                 the earlier ones were launched already: Ready
EXTRA_ROWS = 200                # dropdowns and colours below the data, for rows typed by hand
RECENT_DAYS = 3                 # batches delivered this recently are re-listed at every sync (a re-render or a late upload lands too)
HAND = "Added by hand"
TOKEN_PRODUCT = {"HoboBag3PieceSet": "3-Piece Set", "HoboBag": "Hobo Bag", "Hobo20": "Hobo 2.0", "VintageBag": "Vintage Bag",
                 "SilhouetteBag": "Silhouette Bag", "SlouchySoft3PieceSet": "Slouchy Set"}
KEYWORDS = [("hobo2", "Hobo 2.0"), ("set3", "3-Piece Set"), ("3piece", "3-Piece Set"), ("slouchy", "Slouchy Set"),
            ("vintage", "Vintage Bag"), ("silhouette", "Silhouette Bag"), ("hobo", "Hobo Bag"), ("remix", "Hobo Bag")]
THEMES = {"BlackFriday": "Black Friday", "CyberMonday": "Cyber Monday", "CyberWeek": "Cyber Week", "Christmas": "Christmas",
          "Gift": "Gift", "MothersDay": "Mother's Day", "Travel": "Travel", "Evergreen": "Evergreen"}
BATCH_RE = re.compile(r"^(B\d{3}(?:r\d+)?)\s*–\s*(\d{4}-\d{2}-\d{2})\s*–\s*(.+?)\s*–\s*(.+)$")
BANNER_RE = re.compile(rf"^(B\d{{3}}(?:r\d+)?\b|{HAND})")


def load_cfg():
    return json.load(open(CFG, encoding="utf-8"))


def token():
    sys.path.insert(0, HERE)
    import drive_upload
    with contextlib.redirect_stdout(io.StringIO()):
        return drive_upload, drive_upload.access_token()


# ---------------------------------------------------------------- reading
def export(du, tok, sid):
    """The sheet as an openpyxl workbook (formulas kept as text)."""
    import openpyxl
    u = f"https://www.googleapis.com/drive/v3/files/{sid}/export?mimeType={XLSX}"
    with du.api("GET", u, tok) as r:
        return openpyxl.load_workbook(io.BytesIO(r.read()))


def read_tracker(wb):
    """(header, {key: row}, rows added by hand) of the Tracker tab; rows = dicts by header. Banner rows are skipped (rebuilt)."""
    if TAB not in wb.sheetnames:
        return [c for c, _ in COLS], {}, []
    ws = wb[TAB]
    head = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    while head and not head[-1]:
        head.pop()
    keyed, hand = {}, []
    for r in ws.iter_rows(min_row=2, max_col=len(head), values_only=True):
        row = {h: v for h, v in zip(head, r) if h}
        if row.get("Key"):
            keyed[str(row["Key"])] = row
            continue
        vals = [v for v in r if v not in (None, "")]
        if not vals or (len(vals) == 1 and r[0] == vals[0] and BANNER_RE.match(str(vals[0]))):
            continue
        hand.append(row)
    return head, keyed, hand


def link_of(v):
    m = re.search(r'HYPERLINK\("([^"]+)"', str(v or ""))
    return m.group(1) if m else (v if str(v or "").startswith("http") else "")


def drive_batches(du, tok, outputs):
    """Every B-numbered batch folder in Outputs, Outputs/Winners and Outputs/New Products -> {B019: {...}}."""
    found = {}
    tops = du.list_children(tok, outputs)
    subs = [(f["id"], f["name"]) for f in tops if f.get("mimeType") == FOLDER and f["name"] in ("Winners", "New Products")]
    for parent, where in [(outputs, "")] + subs:
        for f in (tops if parent == outputs else du.list_children(tok, parent)):
            m = BATCH_RE.match(f["name"]) if f.get("mimeType") == FOLDER else None
            if m:
                found.setdefault(m.group(1), dict(id=m.group(1), folder=f["id"], name=f["name"], date=m.group(2), what=m.group(3),
                                                  size=m.group(4), where=where,
                                                  link=f.get("webViewLink") or f"https://drive.google.com/drive/folders/{f['id']}"))
    return found


def crawl(du, tok, folder, skip=()):
    """A batch folder (recursive) -> (files, folders, script): its image and video files, the newest copy per ad name (re-uploads
    named ..._upd0922 count as the same ad) [{name, path, kind, link}], {folder path: link} and the link of its strategy sheet
    (the scripts) or ''."""
    folders, docs = {}, {}

    def walk(fid, path):
        out = []
        for f in du.list_children(tok, fid):
            p = f"{path}/{f['name']}" if path else f["name"]
            if f.get("mimeType") == FOLDER:
                if not any(p.startswith(s) for s in skip):
                    folders[p] = f.get("webViewLink") or f"https://drive.google.com/drive/folders/{f['id']}"
                    out += walk(f["id"], p)
            elif (f.get("mimeType") or "").split("/")[0] in ("image", "video"):
                out.append(dict(f, path=p))
            elif re.search(r"strategy_sheet\.(md|csv)$", f["name"]):
                docs[f["name"].rsplit(".", 1)[1]] = f.get("webViewLink") or f"https://drive.google.com/file/d/{f['id']}/view"
        return out
    newest = {}
    for f in walk(folder, ""):
        n = re.sub(r"_upd\d{4,6}$", "", os.path.splitext(f["name"])[0])     # a re-upload ('..._upd0922') is the same ad
        if n not in newest or (f.get("createdTime") or "") > (newest[n].get("createdTime") or ""):
            newest[n] = f
    files = [dict(name=n, path=f["path"], kind="Video" if f["mimeType"].startswith("video") else "Static",
                  link=f.get("webViewLink") or f"https://drive.google.com/file/d/{f['id']}/view")
             for n, f in sorted(newest.items(), key=lambda kv: (kv[1]["path"].count("/") > 1, kv[0]))]
    return files, folders, docs.get("md") or docs.get("csv") or ""


# ---------------------------------------------------------------- rows from the source
def product_of(name, batch_product):
    m = re.match(r"(?:[A-Z]+_)?LC_\d{6}_([A-Za-z0-9]+?)_", name)
    if m and m.group(1) in TOKEN_PRODUCT:
        return TOKEN_PRODUCT[m.group(1)]
    if batch_product and batch_product != "Mixed":
        return batch_product
    return next((p for k, p in KEYWORDS if k in name.lower()), "Mixed")


def theme_of(name, batch_theme=""):
    m = re.match(r"LC_\d{6}_[A-Za-z0-9]+_([A-Za-z]+)_", name)
    t = m.group(1) if m else (batch_theme or "")
    return THEMES.get(t, t)


def angle_of(name, path, kind):
    proj = re.search(r"Videos/P\d+ – ([^/]+)/", path)
    if kind == "Video" and proj:
        return proj.group(1)
    m = re.search(r"_(?:S|V)\d+_(.+)$", name) or re.search(r"^(?:S|V)\d+_(.+)$", name) or re.search(r"_H\d_(.+)$", name)
    return m.group(1).replace("_", " ") if m else ""


def batch_meta(bid, led, dfolder):
    """A batch's details from the ledger entry and / or its Drive folder name."""
    b = led.get(bid) or {}
    what, theme = (dfolder or {}).get("what", ""), ""
    for k, v in THEMES.items():               # 'Hobo Bag BlackFriday' -> product 'Hobo Bag', theme 'Black Friday'
        if what.endswith(" " + k):
            what, theme = what[: -len(k) - 1], v
    day = b.get("date") or (dfolder or {}).get("date")
    return {"Batch": bid, "Delivered": datetime.date.fromisoformat(day) if day else None,
            "Product": b.get("product") or what or "", "Theme": theme_of("", b.get("theme")) or theme,
            "Size": (dfolder or {}).get("size") or "", "Drive folder": (dfolder or {}).get("link") or b.get("link") or ""}


def banner(meta):
    """'B037 · 04 Nov · Hobo Bag · Black Friday · 25 statics'."""
    d = meta.get("Delivered")
    th = meta.get("Theme") if meta.get("Theme") not in ("", None, "Evergreen") else ""
    return " · ".join(x for x in (meta["Batch"], d.strftime("%d %b") if d else "", meta.get("Product") or "", th or "",
                                  meta.get("Size") or "") if x)


def hlink(url, label):
    return f'=HYPERLINK("{url}","{str(label).replace(chr(34), chr(39))}")' if url else ""


def rows_of(bid, meta, files, folders, script, labels):
    """The Tracker rows of one batch: a static (or a motion still's video) per file, a video project per P-number (its versions'
    folder), a single video (V01 ...) per file -> {key: row}."""
    out, projects = {}, {}
    holiday = meta.get("Theme") if meta.get("Theme") not in ("", None, "Evergreen") else ""
    base = {"Date": meta.get("Delivered"), "Holiday": holiday, "Drive": hlink(meta.get("Drive folder"), f"📁 {bid}")}
    for f in files:
        n, kind = f["name"], f["kind"]
        pm = re.search(r"_P(\d+)_H\d", n)
        if kind == "Video" and pm:
            projects.setdefault(f"P{pm.group(1)}", []).append(f)
            continue
        sm = re.search(r"(?:^|_)([SV]\d+)_", n)
        what = angle_of(n, f["path"], kind)
        motion = kind == "Video" and n.endswith("_motion")
        if motion:
            what = re.sub(r"\s*motion$", "", what) + " · motion video"
        out[f"{bid}|{n}"] = dict(base, Project=f"{bid} {sm.group(1)} · {what}" if sm else f"{bid} · {n}", Link=hlink(f["link"], "Open"),
                                 Script=labels.get(n) or labels.get(re.sub(r"_motion$", "", n)) or "")
    for pid, fs in projects.items():
        fs = sorted(fs, key=lambda x: x["name"])
        d = os.path.dirname(fs[0]["path"])
        link = folders.get(d) if d and os.path.basename(d).startswith(pid) else fs[0]["link"]
        what = angle_of(fs[0]["name"], fs[0]["path"], "Video")
        out[f"{bid}|{pid}"] = dict(base, Project=f"{bid} {pid} · {what} · {len(fs)} hook{'s' * (len(fs) > 1)}",
                                   Link=hlink(link, "Open"), Script=hlink(script, f"Script ({pid})") if script else labels.get(fs[0]["name"], ""))
    return out


def order(key):
    """Rows of a batch: statics (a motion video under its still), then the video projects and single videos."""
    k = key.split("|", 1)[1]
    m = re.search(r"(?:^|_)([SPV])(\d+)(?:_|$)", k)
    if not m:
        return (3, 0, 0, k)
    return (0 if m.group(1) == "S" else 1, int(m.group(2)), k.endswith("_motion"), k)


def batch_order(bid):
    m = re.match(r"B(\d+)(?:r(\d+))?", bid)
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (10 ** 6, 0)


# ---------------------------------------------------------------- writing
def build(head, groups, hand, other_tabs, synced_at):
    """The workbook: the Tracker tab (banner row per batch, its rows; then the rows added by hand) + people's own tabs.
    groups = [(banner text, [row, ...]), ...]."""
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    F = "Arial"
    side = Side(style="thin", color="D0D0D0")
    border = Border(left=side, right=side, top=side, bottom=side)
    body, link_font = Font(name=F, size=10), Font(name=F, size=10, color="1155CC", underline="single")
    centre = Alignment(horizontal="center", vertical="center", wrap_text=True)
    wb = Workbook()
    ws = wb.active
    ws.title = TAB
    L = {h: get_column_letter(i) for i, h in enumerate(head, 1)}
    visible = [h for h in head if h != "Key"]
    for i, h in enumerate(head, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill = PatternFill("solid", fgColor="3C4043")
        c.font = Font(name=F, bold=True, color="FFFFFF", size=10)
        c.alignment, c.border = centre, border
    ws.row_dimensions[1].height = 30
    ws["B1"].comment = Comment(
        "One row per static and per video project (its 4 hook versions), under its batch. We fill Date to Script and Status "
        "(🔍 Review = look at it first, ✅ Ready = may go live, 🛠 Needs fix, ⛔ Skip). You fill Launched (Meta), Meta status and Insights: "
        f"kept at every update. Updated by the pipeline (tracker.py) at each batch upload; last update {synced_at}.", "Claude")
    r = 2
    for title, rows in list(groups) + ([(HAND, hand)] if hand else []):
        c = ws.cell(row=r, column=1, value=title)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(visible))
        c.fill = PatternFill("solid", fgColor="DCE6F1")
        c.font = Font(name=F, bold=True, size=10)
        c.alignment = centre
        ws.row_dimensions[r].height = 22
        r += 1
        for row in rows:
            for i, h in enumerate(head, 1):
                v = row.get(h)
                c = ws.cell(row=r, column=i, value=v if v not in ("",) else None)
                c.font = link_font if isinstance(v, str) and v.startswith("=HYPERLINK") else body
                c.border = border
                c.alignment = Alignment(horizontal="left" if h in ("Project", "Script", "Insights") else "center",
                                        vertical="center", wrap_text=h in ("Project", "Script", "Insights"))
                if isinstance(v, (datetime.date, datetime.datetime)):
                    c.number_format = "mm/dd"
            ws.row_dimensions[r].height = 30
            r += 1
    last = r + EXTRA_ROWS
    for h, opts in (("Status", STATUS), ("Launched (Meta)", LAUNCHED), ("Meta status", META)):
        if h not in L:
            continue
        dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=True, showErrorMessage=False)
        ws.add_data_validation(dv)
        dv.add(f"{L[h]}2:{L[h]}{last}")
        for val, col in opts.items():
            ws.conditional_formatting.add(f"{L[h]}2:{L[h]}{last}", CellIsRule(operator="equal", formula=[f'"{val}"'],
                                                                            fill=PatternFill("solid", fgColor=col)))
    widths = {"Date": 9, "Project": 36, "Holiday": 13, "Link": 9, "Drive": 11, "Script": 44, "Status": 14, "Launched (Meta)": 15,
              "Meta status": 19, "Insights": 48}
    for h in head:
        ws.column_dimensions[L[h]].width = widths.get(h, 16)
    if "Key" in L:
        ws.column_dimensions[L["Key"]].hidden = True
    ws.freeze_panes = "C2"
    for title, cells in other_tabs:        # people's own tabs: their values and formulas, as they were
        o = wb.create_sheet(title)
        for (rr, cc), v in cells.items():
            o.cell(row=rr, column=cc, value=v)
    return wb


def replace(du, tok, sid, wb):
    buf = io.BytesIO()
    wb.save(buf)
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{{}}\r\n--{b}\r\nContent-Type: {XLSX}\r\n\r\n").encode() \
        + buf.getvalue() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://www.googleapis.com/upload/drive/v3/files/{sid}?uploadType=multipart&supportsAllDrives=true"
                                 f"&fields=id,modifiedTime", data=body, method="PATCH",
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": f"multipart/related; boundary={b}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


# ---------------------------------------------------------------- sync
def sync(batches=(), refresh_all=False, notes=None, dry=False, quiet=False):
    """Add / refresh the given batch ids (and every batch folder in Drive the sheet lacks) -> summary dict. (notes: accepted for
    the callers of the old format; the run report carries them.)"""
    say = (lambda *x: None) if quiet else (lambda *x: print(*x, file=sys.stderr))
    cfg = load_cfg()
    du, tok = token()
    sid = cfg["sheet_id"]
    outputs = du.load_config()["drive"]["outputs_folder"]
    wb = export(du, tok, sid)
    first = TAB not in wb.sheetnames
    head, keyed, hand = read_tracker(wb)
    missing = [h for h, _ in COLS if h not in head and h != "Key"]       # our columns people deleted come back; Key stays last
    head = [x for x in head if x != "Key"] + missing + ["Key"]
    other = [(ws.title, {(c.row, c.column): c.value for row in ws.iter_rows() for c in row if c.value is not None})
             for ws in wb.worksheets if ws.title not in (TAB,) + LEGACY]

    sys.path.insert(0, HERE)
    import ledger
    led = {ledger.bid(b["n"], b.get("rev")): b for b in ledger.load()["batches"]}
    labels = {a["name"]: a.get("label") or "" for b in led.values() for a in b.get("ads") or []}
    dfold = drive_batches(du, tok, outputs)
    have = {k.split("|", 1)[0] for k in keyed}
    today = datetime.date.today()
    recent = {b for b, f in dfold.items() if 0 <= (today - datetime.date.fromisoformat(f["date"])).days <= RECENT_DAYS}
    todo = {b for b in batches if b} | {b for b in dfold if b not in have} | recent    # (recent: re-renders and late uploads)
    if refresh_all or first:
        todo |= have | set(dfold) | {b for b in led if (led[b].get("link") or "")}
    say(f"tracker: syncing {', '.join(sorted(todo, key=batch_order)) or 'nothing new'}")
    kind = dict(COLS)
    added_b, added, refreshed = [], 0, 0
    overrides = cfg.get("folder_overrides") or {}
    metas = {}
    for bid in sorted(todo, key=batch_order):
        df = dfold.get(bid)
        folder = overrides.get(bid) or (df or {}).get("folder")
        if not folder:
            m = re.search(r"folders/([A-Za-z0-9_-]+)", (led.get(bid) or {}).get("link") or "")
            folder = m.group(1) if m else None
        if not folder:
            say(f"tracker: {bid} has no Drive folder: skipped")
            continue
        meta = metas[bid] = batch_meta(bid, led, df)
        if overrides.get(bid):
            meta["Drive folder"] = f"https://drive.google.com/drive/folders/{folder}"
        files, folders, script = crawl(du, tok, folder, skip=tuple(cfg.get("skip_paths", {}).get(bid, [])))
        new = rows_of(bid, meta, files, folders, script, labels)
        if new and bid not in have:
            added_b.append(bid)
        day = meta.get("Delivered")
        for k, x in new.items():
            o = keyed.get(k)
            if o is None:
                keyed[k] = dict(x, Key=k, Status="🔍 Review" if day and day.isoformat() >= REVIEW_FROM else "✅ Ready")
                added += 1
            else:
                for h, v in x.items():
                    if kind.get(h) == "d" and v not in (None, ""):
                        o[h] = v
                refreshed += 1
    groups = []
    for bid in sorted({k.split("|", 1)[0] for k in keyed}, key=batch_order, reverse=True):     # the newest batch on top
        meta = metas.get(bid) or batch_meta(bid, led, dfold.get(bid))
        rows = [keyed[k] for k in sorted((k for k in keyed if k.split("|", 1)[0] == bid), key=order)]
        groups.append((banner(meta), rows))
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    res = dict(link=cfg.get("link"), batches_added=added_b, ads_added=added, ads_refreshed=refreshed, batches=len(groups),
               ads=len(keyed))
    if dry:
        return dict(res, dry_run=True)
    out = build(head, groups, hand, other, now)
    replace(du, tok, sid, out)
    _, k2, _ = read_tracker(export(du, tok, sid))      # verify: every row is there after the rewrite
    res.update(verified=len(k2) >= len(keyed))
    say(f"tracker: {len(added_b)} batch(es) and {added} row(s) added, {refreshed} refreshed: {cfg.get('link')}")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--batch", action="append", default=[], help="a batch id to add / refresh (repeatable)")
    s.add_argument("--all", action="store_true", help="refresh the file details of every batch")
    s.add_argument("--dry-run", action="store_true")
    sub.add_parser("show")
    a = ap.parse_args()
    if a.cmd == "show":
        cfg = load_cfg()
        du, tok = token()
        wb = export(du, tok, cfg["sheet_id"])
        _, keyed, hand = read_tracker(wb)
        print(json.dumps(dict(link=cfg["link"], batches=len({k.split("|", 1)[0] for k in keyed}), rows=len(keyed), by_hand=len(hand),
                              tabs=wb.sheetnames), indent=1))
        return 0
    print(json.dumps(sync([x.upper() for x in a.batch], refresh_all=a.all, dry=a.dry_run), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
