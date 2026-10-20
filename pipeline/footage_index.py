#!/usr/bin/env python3
"""Index the client's whole raw footage library automatically (owner 2026-10-20: "there is so much footage, use it").

clip_index.json had 87 hand-tagged clips; the Drive library holds ~1,400 raw bag clips (4K among them). This reads only
the file header and 4 single frames per clip over HTTP range requests (nothing is downloaded whole), checks every frame
for faces (YuNet), sharpness and brightness, and tags the clip from the folder / file names the client wrote
("Black hobo - stairs / pouch lip stick / open zips"), then merges the clips that pass into pipeline/data/clip_index.json
(`"auto": true`; hand-tagged rows are never touched). make_batch's shot pool (index_clips) and the statics' frame bank read it.

  python3 pipeline/footage_index.py select                 # which library files are raw bag footage (a count per product)
  python3 pipeline/footage_index.py scan [--limit N]       # probe + 4 frames + checks, resumable (pipeline/cache/footage/scan.json)
  python3 pipeline/footage_index.py merge                  # passing clips -> pipeline/data/clip_index.json
  python3 pipeline/footage_index.py sheets --product "Hobo Bag" --n 40 --out DIR   # contact sheets to look at (a sample)
  python3 pipeline/footage_index.py stats                  # what the scan found
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import statistics
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from index_library import CACHE, direct_url  # noqa: E402

OUTDIR = os.path.join(os.path.dirname(CACHE), "footage")
SCAN = os.path.join(OUTDIR, "scan.json")
INDEX = os.path.join(HERE, "data", "clip_index.json")
FRAMES = 4
LONG = 960                                   # analysis frames: this many px on the long side

# (clip_index product name, library path regex). Winner RAWs / finished ads (ACH Creative Delivery, Kate Creatives) are not b-roll.
FOLDERS = [
    ("Hobo Bag", r"^Raw files/Hobo Bag/"),
    ("Hobo 2.0", r"^Raw files/HOBO 2\.0/"),
    ("Vintage Bag", r"^Raw files/Vintage Bag/"),
    ("Slouchy", r"^Raw files/Slouchy/"),
    ("Hobo 3-Piece Set", r"^Raw files/Hobo Bag 3 Piece Set"),
    ("2in1 Backpack", r"^Raw files/2in1 Backpack/"),
]
SKIP = re.compile(r"\bRAW\b|Concept \d|Creative Delivery|hook|caption|subtitle|testimon|review", re.I)   # edits / people talking
COLOURS = [("black", r"black|noir"), ("brown", r"brown|choco|coffee|ginger"), ("blue", r"blue|navy"), ("beige", r"beige|cream|tan\b"),
           ("red", r"\bred\b|wine|burgundy"), ("grey", r"grey|gray"), ("green", r"green"), ("white", r"white")]
MIN_SIDE, MIN_DUR, MIN_SHARP = 720, 2.5, 25.0

_lock = threading.Lock()
_cv_lock = threading.Lock()      # OpenCV's DNN net is shared (new_product.detectors) and not thread-safe


def library_files():
    items = json.load(open(CACHE))["items"]
    return [i for i in items if i["kind"] == "file" and (i.get("mime") or "").startswith("video")]


def selected():
    """[(product, library item)] of the raw bag footage."""
    out = []
    for i in library_files():
        for product, rx in FOLDERS:
            if re.search(rx, i["path"], re.I):
                if not SKIP.search(i["path"][len("Raw files/"):]):
                    out.append((product, i))
                break
    return out


def note_of(product, path):
    """The client's own words for the shot: the folder names under the product folder + the file name, cleaned."""
    parts = path[len("Raw files/"):].split("/")[1:]
    if parts:
        parts[-1] = re.sub(r"\.(mp4|mov|m4v)$", "", parts[-1], flags=re.I)
    words = " / ".join(p.strip() for p in parts if p.strip())
    words = re.sub(r"\b(IMG|MVI|DSC|VID|PXL)[_ -]?\d+\b", "", words, flags=re.I)
    words = re.sub(r"[_]+", " ", words)
    return re.sub(r"\s+", " ", words).strip(" /-")


def colour_of(path):
    low = path.lower()
    hits = [c for c, rx in COLOURS if re.search(rx, low)]
    return hits[0] if len(hits) == 1 else "/".join(hits[:2]) if hits else ""


def probe(fid):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration,size:stream=codec_type,width,height,r_frame_rate:stream_tags=rotate",
                        "-of", "json", direct_url(fid)], capture_output=True, text=True, timeout=150)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    w, h = v.get("width"), v.get("height")
    if str(v.get("tags", {}).get("rotate", "0")) in ("90", "270", "-90") and w and h:
        w, h = h, w
    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    return dict(duration=round(float(d.get("format", {}).get("duration", 0) or 0), 2), width=w, height=h,
                fps=round(int(num) / max(int(den), 1), 2), size_mb=round(int(d.get("format", {}).get("size", 0) or 0) / 2**20, 1),
                audio=any(s.get("codec_type") == "audio" for s in d.get("streams", [])))


def grab(fid, t, path):
    vf = f"scale='if(gt(iw,ih),{LONG},-2)':'if(gt(iw,ih),-2,{LONG})'"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", direct_url(fid), "-frames:v", "1",
                    "-vf", vf, "-q:v", "3", "-y", path], timeout=240)
    return os.path.exists(path) and os.path.getsize(path) > 2000


def analyse(paths):
    """Per frame: faces (YuNet), sharpness, brightness; plus the mean difference between frames (a locked-off shot is ~0)."""
    import cv2
    import numpy as np
    import ai_gen
    import new_product
    rows, grays = [], []
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        grays.append(cv2.resize(g, (96, 96)).astype("float32"))
        with _cv_lock:
            nf = int(new_product.count_faces(p, strict=False) or 0)
        rows.append(dict(faces=nf, sharp=round(ai_gen.sharpness(p), 1), bright=round(float(g.mean()), 1)))
    diff = round(float(np.mean([abs(a - b).mean() for a, b in zip(grays, grays[1:])])), 1) if len(grays) > 1 else 0.0
    return rows, diff


def scan_one(product, item, sheets):
    fid = item["id"]
    r = dict(id=fid, path=item["path"][len("Raw files/"):], product=product)
    try:
        r.update(probe(fid))
        if not r.get("duration") or r["duration"] < 0.5:
            r["error"] = "no duration"
            return r
        paths = []
        for k in range(FRAMES):
            p = os.path.join(sheets, f"{fid}_{k}.jpg")
            if grab(fid, r["duration"] * (k + 0.5) / FRAMES, p):
                paths.append(p)
        rows, diff = analyse(paths)
        r.update(frames=rows, diff=diff)
    except Exception as e:  # noqa: BLE001  (a clip that cannot be read is marked, the scan goes on)
        r["error"] = str(e)[:160]
    return r


def load_scan():
    try:
        return {x["id"]: x for x in json.load(open(SCAN))}
    except (OSError, ValueError):
        return {}


def cmd_select(_):
    sel = selected()
    by = {}
    for p, _i in sel:
        by[p] = by.get(p, 0) + 1
    print(json.dumps(by, indent=1), "total", len(sel), "(already scanned:", len(load_scan()), ")")


def cmd_scan(a):
    os.makedirs(OUTDIR, exist_ok=True)
    sheets = os.path.join(OUTDIR, "frames")
    os.makedirs(sheets, exist_ok=True)
    done = load_scan()
    todo = [(p, i) for p, i in selected() if i["id"] not in done or done[i["id"]].get("error")]
    if a.product:
        todo = [(p, i) for p, i in todo if p.lower() == a.product.lower()]
    todo = todo[: a.limit] if a.limit else todo
    print(f"scanning {len(todo)} clips ({len(done)} done)", flush=True)

    def work(x):
        r = scan_one(x[0], x[1], sheets)
        with _lock:
            done[r["id"]] = r
            if len(done) % 25 == 0:
                json.dump(list(done.values()), open(SCAN, "w"))
                print(f"  {len(done)} scanned", flush=True)
        return r
    with cf.ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(work, todo))
    json.dump(list(done.values()), open(SCAN, "w"))
    print(f"scan done: {len(done)} clips, {sum(1 for x in done.values() if x.get('error'))} errors")


def verdict(r):
    """(faces none|partial|full, usable yes|no, reason): the checks the shot pool needs."""
    fr = r.get("frames") or []
    if r.get("error") or not fr:
        return "unknown", "no", r.get("error") or "no frames"
    n = sum(1 for f in fr if f["faces"])
    faces = "none" if n == 0 else "partial" if n <= 1 else "full"
    sharp = statistics.median(f["sharp"] for f in fr)
    bright = statistics.median(f["bright"] for f in fr)
    if min(r.get("width") or 0, r.get("height") or 0) < MIN_SIDE:
        return faces, "no", "under 720p"
    if (r.get("duration") or 0) < MIN_DUR:
        return faces, "no", "under 2.5 s"
    if faces != "none":
        return faces, "no", "face"
    if sharp < MIN_SHARP:
        return faces, "no", f"soft ({sharp:.0f})"
    if bright < 28 or bright > 235:
        return faces, "no", "too dark / bright"
    return faces, "yes", ""


def cmd_merge(_):
    scan = load_scan()
    rows = json.load(open(INDEX))
    have = {r["id"] for r in rows}
    n = max([r.get("n", 0) for r in rows] + [0])
    added = 0
    for r in scan.values():
        if r["id"] in have:
            continue
        faces, usable, why = verdict(r)
        n += 1
        rows.append(dict(n=n, id=r["id"], path=r["path"], duration=r.get("duration"), width=r.get("width"), height=r.get("height"),
                         audio=r.get("audio", False), rights_ok="unknown", product=r["product"], colour=colour_of(r["path"]),
                         faces=faces, usable=usable, note=note_of(r["product"], "Raw files/" + r["path"]), text="none",
                         auto=True, fps=r.get("fps"), diff=r.get("diff"),
                         sharp=round(statistics.median(f["sharp"] for f in r["frames"]), 1) if r.get("frames") else None,
                         **({"why_not": why} if why else {})))
        added += 1
    json.dump(rows, open(INDEX, "w"), indent=1, ensure_ascii=False)
    print(f"merged {added} new rows ({len(rows)} total); usable now:", summary(rows))


def summary(rows):
    out = {}
    for r in rows:
        if r.get("usable") == "yes" and r.get("faces") == "none":
            k = r["product"]
            out[k] = out.get(k, 0) + 1
    return out


def cmd_stats(_):
    scan = load_scan()
    by = {}
    for r in scan.values():
        faces, usable, why = verdict(r)
        b = by.setdefault(r["product"], dict(clips=0, usable=0, minutes=0.0, k4=0, face=0, soft=0, small=0, short=0, err=0))
        b["clips"] += 1
        b["err"] += bool(r.get("error"))
        if usable == "yes":
            b["usable"] += 1
            b["minutes"] += (r.get("duration") or 0) / 60
            b["k4"] += max(r.get("width") or 0, r.get("height") or 0) >= 3840
        b["face"] += why == "face"
        b["soft"] += why.startswith("soft")
        b["small"] += why == "under 720p"
        b["short"] += why == "under 2.5 s"
    for k, b in by.items():
        b["minutes"] = round(b["minutes"], 1)
    print(json.dumps(by, indent=1))


def cmd_sheets(a):
    import clip_index
    scan = [r for r in load_scan().values() if r["product"].lower() == a.product.lower() and verdict(r)[1] == "yes"]
    scan.sort(key=lambda r: r["path"])
    step = max(1, len(scan) // a.n)
    pick = scan[::step][: a.n]
    for n, c in enumerate(pick, 1):
        c["n"] = n
    os.makedirs(a.out, exist_ok=True)
    for c in pick:                                # clip_index.sheet reads <outdir>/<id>_<k>.jpg
        for k in range(FRAMES):
            src = os.path.join(OUTDIR, "frames", f"{c['id']}_{k}.jpg")
            if os.path.exists(src):
                dst = os.path.join(a.out, f"{c['id']}_{k}.jpg")
                if not os.path.exists(dst):
                    os.symlink(src, dst)
    for p in clip_index.sheet(pick, a.out):
        print(p)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select")
    s = sub.add_parser("scan")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--workers", type=int, default=8)
    s.add_argument("--product", default="")
    sub.add_parser("merge")
    sub.add_parser("stats")
    sh = sub.add_parser("sheets")
    sh.add_argument("--product", required=True)
    sh.add_argument("--n", type=int, default=36)
    sh.add_argument("--out", required=True)
    a = ap.parse_args()
    {"select": cmd_select, "scan": cmd_scan, "merge": cmd_merge, "stats": cmd_stats, "sheets": cmd_sheets}[a.cmd](a)


if __name__ == "__main__":
    main()
