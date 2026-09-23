#!/usr/bin/env python3
"""Find the right files in the library index (built by index_library.py).

  ad      Match ad names from the brief to their source video files.
          python3 pipeline/find_assets.py ad "ACH-YEVH-123-H4 - Copy" "C9_V2_HappyWrong - Copy"

  product List candidate reference photos and videos for a product (names from config.json).
          python3 pipeline/find_assets.py product "Hobo Bag" --images 12 --videos 8

  thumbs  Download the small Drive thumbnails for some file ids, so Claude can look at
          them before choosing (a few KB each, never the full file).
          python3 pipeline/find_assets.py thumbs ID1 ID2 --outdir /tmp/thumbs

Output is JSON on stdout. Each file carries its direct download URL and size.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_library import CACHE, direct_url, file_size, load_config  # noqa: E402


def load_index():
    if not os.path.exists(CACHE):
        sys.exit("No library index yet. Run: python3 pipeline/index_library.py")
    with open(CACHE) as f:
        return [i for i in json.load(f)["items"] if i["kind"] == "file"]


def norm(s):
    s = re.sub(r"\.(mp4|mov|m4v|jpg|jpeg|png)$", "", s.strip(), flags=re.I)
    s = re.sub(r"\s*-\s*copy(\s*\d+)?\s*$", "", s, flags=re.I)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def describe(i, with_size=True):
    out = dict(id=i["id"], path=i["path"], mime=i["mime"], url=direct_url(i["id"]), thumb=i.get("thumb", ""))
    size = i.get("size")
    if size is None and with_size:
        size = file_size(i["id"])
    out["size_mb"] = round(size / 2**20, 1) if size else None
    return out


def match_ad(name, files):
    """Exact normalized name match, preferring edited exports over RAW folders."""
    key = norm(name)
    hits = [i for i in files if norm(i["path"].rsplit("/", 1)[-1]) == key]
    if not hits:
        hits = [i for i in files if key and key in norm(i["path"].rsplit("/", 1)[-1])]
    hits = [i for i in hits if i["mime"].startswith("video")] or hits
    hits.sort(key=lambda i: ("/raw/" in i["path"].lower(), len(i["path"])))
    return hits


def cmd_ad(args, files):
    result = []
    for name in args.names:
        hits = match_ad(name, files)
        result.append(dict(
            ad=name,
            matched=bool(hits),
            best=describe(hits[0]) if hits else None,
            alternatives=[describe(h, with_size=False) for h in hits[1:4]],
        ))
    print(json.dumps(result, indent=2))


def cmd_product(args, files):
    folders = load_config()["products"].get(args.name)
    if not folders:
        sys.exit(f"Unknown product '{args.name}'. Add it to 'products' in pipeline/config.json.")
    in_scope = [i for i in files if any(i["path"].startswith(f + "/") for f in folders)]
    images = [i for i in in_scope if i["mime"].startswith("image")]
    videos = [i for i in in_scope if i["mime"].startswith("video") and "/raw/" not in i["path"].lower()]
    if args.match:
        words = [w.lower() for w in args.match.split()]
        score = lambda i: -sum(w in i["path"].lower() for w in words)  # noqa: E731
        images.sort(key=score)
        videos.sort(key=score)
    print(json.dumps(dict(
        product=args.name,
        folders=folders,
        total_images=len(images),
        total_videos=len(videos),
        images=[describe(i) for i in images[: args.images]],
        videos=[describe(i) for i in videos[: args.videos]],
    ), indent=2))


def cmd_thumbs(args, files):
    by_id = {i["id"]: i for i in files}
    os.makedirs(args.outdir, exist_ok=True)
    saved = []
    for fid in args.ids:
        thumb = by_id.get(fid, {}).get("thumb")
        if not thumb:
            continue
        path = os.path.join(args.outdir, f"{fid}.jpg")
        # s190 is the listing size; ask Drive for a bigger preview that is still small.
        with urllib.request.urlopen(re.sub(r"=s\d+$", "=s640", thumb), timeout=30) as r, open(path, "wb") as f:
            f.write(r.read())
        saved.append(dict(id=fid, path=path, name=by_id[fid]["path"]))
    print(json.dumps(saved, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ad")
    a.add_argument("names", nargs="+")
    p = sub.add_parser("product")
    p.add_argument("name")
    p.add_argument("--images", type=int, default=12)
    p.add_argument("--videos", type=int, default=8)
    p.add_argument("--match", default="", help="words to rank by, e.g. 'black outside'")
    t = sub.add_parser("thumbs")
    t.add_argument("ids", nargs="+")
    t.add_argument("--outdir", default="/tmp/creative-run/thumbs")
    args = ap.parse_args()
    files = load_index()
    {"ad": cmd_ad, "product": cmd_product, "thumbs": cmd_thumbs}[args.cmd](args, files)


if __name__ == "__main__":
    main()
