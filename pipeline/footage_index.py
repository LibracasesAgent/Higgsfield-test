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


def retry(fn, tries=5):
    """Drive answers 5XX / a quota page now and then, more under many parallel reads: the same call again after a pause."""
    import time
    for k in range(tries):
        r = fn()
        if r:
            return r
        time.sleep(2 + 3 * k)
    return None


def local_source(fid):
    """The clip as a local file when recut.source can fetch it (1 MB range requests in parallel: whole-file and big-range reads of
    the shared library files hit Drive's anonymous download quota, "Quota exceeded"), else its public URL."""
    import recut
    return recut.source(fid)


def probe(src):
    def run():
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration,size:stream=codec_type,width,height,r_frame_rate:stream_tags=rotate:stream_side_data=rotation",
                            "-of", "json", src], capture_output=True, text=True, timeout=150)
        return r if json.loads(r.stdout or "{}").get("format") else None
    r = retry(run)
    if r is None:
        return dict(duration=0)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    w, h = v.get("width"), v.get("height")
    rot = [str(v.get("tags", {}).get("rotate", "0"))] + [str(x.get("rotation", 0)) for x in v.get("side_data_list") or []]
    if any(r.split(".")[0] in ("90", "270", "-90", "-270") for r in rot) and w and h:      # (an iPhone clip: the display matrix, not a tag)
        w, h = h, w
    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    return dict(duration=round(float(d.get("format", {}).get("duration", 0) or 0), 2), width=w, height=h,
                fps=round(int(num) / max(int(den), 1), 2), size_mb=round(int(d.get("format", {}).get("size", 0) or 0) / 2**20, 1),
                audio=any(s.get("codec_type") == "audio" for s in d.get("streams", [])))


def grab(src, t, path):
    vf = f"scale='if(gt(iw,ih),{LONG},-2)':'if(gt(iw,ih),-2,{LONG})'"

    def run():
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                        "-vf", vf, "-q:v", "3", "-y", path], timeout=240, capture_output=True)
        return os.path.exists(path) and os.path.getsize(path) > 2000
    return bool(retry(run, 4))


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
    src = None
    try:
        src = local_source(fid)
        r.update(probe(src))
        if not r.get("duration") or r["duration"] < 0.5:
            r["error"] = "no duration"
            return r
        paths = []
        for k in range(FRAMES):
            p = os.path.join(sheets, f"{fid}_{k}.jpg")
            if grab(src, r["duration"] * (k + 0.5) / FRAMES, p):
                paths.append(p)
        rows, diff = analyse(paths)
        r.update(frames=rows, diff=diff)
    except Exception as e:  # noqa: BLE001  (a clip that cannot be read is marked, the scan goes on)
        r["error"] = str(e)[:160]
    finally:
        if src and os.path.exists(src) and not r.get("keep"):     # (the scan keeps no copies: ~40 GB of footage)
            os.remove(src)
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


# ------------------------------------------------------------------ the frame bank (statics from real footage)
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
BANK_AT = (0.12, 0.25, 0.38, 0.5, 0.62, 0.75, 0.88)      # where in a clip the candidate frames are taken
BANK_W = 1440                                             # a 4K frame is stored 1440 px wide (the static is 1080 wide)


def bank_rows(product, avoid=()):
    """Indexed clips a static can use: usable, no face, vertical (1080+ px) or 4K landscape, no on-screen text, a clip
    the batch does not show in its video footage again (`avoid`: Drive ids)."""
    try:
        rows = json.load(open(INDEX))
    except (OSError, ValueError):
        return []
    return [r for r in rows if r.get("product") == product and r.get("usable") == "yes" and r.get("faces") == "none"
            and r.get("text") in (None, "", "none") and DRIVE_ID.match(str(r.get("id") or ""))
            and ((r.get("height") or 0) > (r.get("width") or 0) and min(r.get("width") or 0, r.get("height") or 0) >= 1080
                 or (r.get("width") or 0) >= (r.get("height") or 0) >= 1900)      # (a 4K landscape clip: a 4:5 window is cut from it)
            and r["id"] not in set(avoid) and not re.search(r"\bRAW\b|Concept \d|Creative Delivery", r.get("path") or "")]


def texture(path):
    """Share of edge pixels (Canny at 360x640): a bag in a scene is ~0.07-0.14, a macro of leather grain 0.23+."""
    import cv2
    g = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if g is None:
        return 0.0
    return float(cv2.Canny(cv2.resize(g, (360, 640)), 60, 150).mean() / 255)


def portrait_window(path, aspect=0.8):
    """Cuts a 4:5 window out of a landscape frame, at the x where the picture has the most structure (edges + colour: the bag, the hands),
    in place; returns the path. A vertical frame is left alone."""
    import cv2
    import numpy as np
    im = cv2.imread(path)
    if im is None or im.shape[0] >= im.shape[1]:
        return path
    h, w = im.shape[:2]
    cw = int(h * aspect)
    small = cv2.resize(im, (w // 8, h // 8))
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    mag = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1))
    sat = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)[..., 1].astype(np.float32)
    score = mag + 0.5 * sat
    col = score.sum(axis=0)
    sw = max(1, cw // 8)
    best = max(range(0, max(1, small.shape[1] - sw + 1), max(1, sw // 6)), key=lambda x: col[x:x + sw].sum() - 0.15 * abs(x + sw / 2 - small.shape[1] / 2) * col.mean())
    x0 = min(max(best * 8, 0), w - cw)
    cv2.imwrite(path, im[:, x0:x0 + cw], [cv2.IMWRITE_JPEG_QUALITY, 94])
    return path


def frame_bank(product, n, out_dir, avoid=(), seed=1, workers=4):
    """n real frames from n different indexed clips of the product, as statics photos: the sharpest face-free frame of 7 taken
    across each clip (4K vertical clips first), written to out_dir as JPGs (1440 px wide). `avoid`: Drive ids the product's last
    batches already used (other clips first, repeats only when too few are left). -> [{file, id, t, w, h, note, sharp}]; fewer than n
    (or none) when the library has too few clips: the caller says so."""
    import hashlib
    import ai_gen
    import new_product
    rows = bank_rows(product)
    avoid = set(avoid)
    rows.sort(key=lambda r: (r["id"] in avoid, -(max(r["width"], r["height"]) >= 3840),
                             hashlib.md5(f"{seed}{r['id']}".encode()).hexdigest()))
    os.makedirs(out_dir, exist_ok=True)

    def one(r):
        got = []
        src = local_source(r["id"])           # (kept in pipeline/cache/media: the batch's videos read the same file)
        for k, f in enumerate(BANK_AT):
            t = round(float(r["duration"]) * f, 2)
            p = os.path.join(out_dir, f"_c_{r['id'][:10]}_{k}.jpg")
            land = r["width"] > r["height"]
            vf = f"scale={2880 if land else BANK_W}:-2:flags=lanczos"        # (a landscape 4K frame is cut to 4:5 below: 1152 px wide)
            def run():
                try:
                    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src,
                                    "-frames:v", "1", "-vf", vf, "-q:v", "2", "-y", p], timeout=240, capture_output=True)
                except subprocess.SubprocessError:
                    return False
                return os.path.exists(p) and os.path.getsize(p) > 20000
            if retry(run, 4):
                if land:
                    portrait_window(p)
                with _cv_lock:
                    face = new_product.count_faces(p, strict=True)
                sh = ai_gen.sharpness(p)
                if not face and sh >= MIN_SHARP * 2:
                    got.append((min(sh, 800.0) * (0.2 if texture(p) > 0.2 else 1.0), t, p))    # (a macro of grain is the last choice)
        if not got:
            for k in range(len(BANK_AT)):
                q = os.path.join(out_dir, f"_c_{r['id'][:10]}_{k}.jpg")
                if os.path.exists(q):
                    os.remove(q)
            return None
        sh, t, p = max(got)
        final = os.path.join(out_dir, f"F_{r['id'][:10]}_{int(t * 10):04d}.jpg")
        os.replace(p, final)
        for k in range(len(BANK_AT)):                       # (the other candidates, with a face or softer, are not kept)
            q = os.path.join(out_dir, f"_c_{r['id'][:10]}_{k}.jpg")
            if os.path.exists(q):
                os.remove(q)
        return dict(file=final, id=r["id"], t=t, w=r["width"], h=r["height"], note=r.get("note") or "", sharp=round(sh, 1))
    out, i = [], 0
    with cf.ThreadPoolExecutor(workers) as ex:
        while len(out) < n and i < len(rows):
            batch = rows[i:i + (n - len(out)) + 2]        # (a few spare clips: one with no clean frame is skipped)
            i += len(batch)
            out += [x for x in ex.map(one, batch) if x]
    return out[:n]


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
