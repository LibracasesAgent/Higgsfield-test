#!/usr/bin/env python3
"""Index real library clips for recuts: probe + 4 frames + contact sheets.

Only the file header and 4 single frames are read per clip (HTTP range reads),
never the whole video.

  python3 pipeline/clip_index.py select --out pipeline/cache/clips.json      # pick candidates
  python3 pipeline/clip_index.py probe  pipeline/cache/clips.json --sheets /tmp/sheets
  python3 pipeline/clip_index.py tag    pipeline/cache/clips.json <id> key=value ...

Tags a human/Claude fills after looking at the sheets: product, colour, faces
(none|partial|full), text (none|burned), usable (yes|no), note, in, out,
rights_ok (unknown until the client confirms usage rights).
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_library import CACHE, direct_url  # noqa: E402

# (product, folder regex, keyword regex boosting macro/demo clips, how many)
SELECTION = [
    ("Hobo Bag", r"^Raw files/Hobo Bag/", r"pocket|zip|detail|metal|table|keys|open|close|inside|tassel|strap|hang", 30),
    ("Hobo 2.0", r"^Raw files/HOBO 2.0/", r"pocket|zip|strap|secure|stitch|360|feature|table|close|keys", 18),
    ("Vintage Bag", r"^Raw files/(Vintage Bag|Slouchy)/", r"novoice|clasp|snap|open|top|packing|capacity|colour|color|one by one|hardware|strap", 16),
    ("RAW winners", r"Concept (147|172|113|123)/RAW/", r".", 8),
]


def select(out):
    items = [i for i in json.load(open(CACHE))["items"] if i["kind"] == "file" and i["mime"].startswith("video")]
    chosen = []
    for product, folder, kw, n in SELECTION:
        pool = [i for i in items if re.search(folder, i["path"], re.I)]
        pool.sort(key=lambda i: (not re.search(kw, i["path"].rsplit("/", 1)[-1], re.I), i["path"]))
        for i in pool[:n]:
            chosen.append(dict(id=i["id"], path=i["path"][len("Raw files/"):], group=product,
                               thumb=i.get("thumb", ""), tags=dict(rights_ok="unknown")))
    json.dump(chosen, open(out, "w"), indent=1)
    print(f"selected {len(chosen)} clips -> {out}")


def probe_one(c):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration,size:stream=codec_type,width,height,r_frame_rate:stream_tags=rotate",
                            "-of", "json", direct_url(c["id"])], capture_output=True, text=True, timeout=120)
        d = json.loads(r.stdout or "{}")
        v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
        w, h = v.get("width"), v.get("height")
        if str(v.get("tags", {}).get("rotate", "0")) in ("90", "270", "-90") and w and h:
            w, h = h, w
        num, den = (v.get("r_frame_rate") or "0/1").split("/")
        c.update(duration=round(float(d.get("format", {}).get("duration", 0) or 0), 2), width=w, height=h,
                 fps=round(int(num) / max(int(den), 1), 2),
                 size_mb=round(int(d.get("format", {}).get("size", 0) or 0) / 2**20, 1),
                 audio=any(s.get("codec_type") == "audio" for s in d.get("streams", [])))
    except Exception as e:  # keep going; mark the clip
        c["probe_error"] = str(e)[:120]
    return c


def frames_one(c, outdir):
    dur = c.get("duration") or 0
    if not dur:
        return None
    paths = []
    for k in range(4):
        t = dur * (k + 0.5) / 4
        p = os.path.join(outdir, f"{c['id']}_{k}.jpg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", direct_url(c["id"]),
                        "-frames:v", "1", "-vf", "scale=-2:360", "-q:v", "4", "-y", p], timeout=180)
        if os.path.exists(p):
            paths.append(p)
    return paths


def sheet(clips, outdir, per_page=6):
    """Pages of 6 clips; each row = 4 frames with a numbered label."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=20)
    pages = []
    for p0 in range(0, len(clips), per_page):
        rows = clips[p0:p0 + per_page]
        page = Image.new("RGB", (4 * 204 + 10, len(rows) * 392), "white")
        d = ImageDraw.Draw(page)
        for r, c in enumerate(rows):
            for k in range(4):
                f = os.path.join(outdir, f"{c['id']}_{k}.jpg")
                if os.path.exists(f):
                    im = Image.open(f)
                    im.thumbnail((200, 360))
                    page.paste(im, (5 + k * 204, r * 392 + 28))
            label = f"#{c['n']} {c['path'].rsplit('/', 1)[-1][:60]}  {c.get('duration', '?')}s {c.get('width')}x{c.get('height')}"
            d.text((6, r * 392 + 4), label, fill="black", font=font)
        path = os.path.join(outdir, f"page_{p0 // per_page + 1:02d}.jpg")
        page.save(path, quality=85)
        pages.append(path)
    return pages


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--out", default=os.path.join(os.path.dirname(CACHE), "clips.json"))
    p = sub.add_parser("probe")
    p.add_argument("index")
    p.add_argument("--sheets", required=True)
    t = sub.add_parser("tag")
    t.add_argument("index")
    t.add_argument("id")
    t.add_argument("kv", nargs="+")
    a = ap.parse_args()
    if a.cmd == "select":
        select(a.out)
    elif a.cmd == "probe":
        clips = json.load(open(a.index))
        for n, c in enumerate(clips, 1):
            c["n"] = n
        with cf.ThreadPoolExecutor(12) as ex:
            clips = list(ex.map(probe_one, clips))
        os.makedirs(a.sheets, exist_ok=True)
        with cf.ThreadPoolExecutor(12) as ex:
            list(ex.map(lambda c: frames_one(c, a.sheets), clips))
        json.dump(clips, open(a.index, "w"), indent=1)
        for pg in sheet(clips, a.sheets):
            print(pg)
        print(f"probed {len(clips)} clips; errors: {sum('probe_error' in c or not c.get('duration') for c in clips)}")
    else:
        clips = json.load(open(a.index))
        for c in clips:
            if c["id"] == a.id or str(c.get("n")) == a.id:
                c["tags"].update(dict(kv.split("=", 1) for kv in a.kv))
        json.dump(clips, open(a.index, "w"), indent=1)


if __name__ == "__main__":
    main()
