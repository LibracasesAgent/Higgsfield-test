#!/usr/bin/env python3
"""Build a full index of the client's asset library without downloading files.

The Drive connector's search only returns files the user has opened, so it
misses most of the library. This reads Drive's public folder view instead
(works because the library folder is shared "anyone with the link") and
records every file's id, path, type and thumbnail.

Usage:
  python3 pipeline/index_library.py                 # writes pipeline/cache/library.json
  python3 pipeline/index_library.py --sizes         # also look up each file's size (1-byte requests)
  python3 pipeline/index_library.py --summary       # print counts per top folder from the cache
"""
import argparse
import collections
import concurrent.futures as cf
import html
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "library.json")


def load_config():
    with open(os.path.join(HERE, "config.json")) as f:
        return json.load(f)


def fetch(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {})
    return urllib.request.urlopen(req, timeout=timeout)


def list_folder(folder_id):
    """Return (entries, ok). Each entry: dict(id, title, is_folder, mime, thumb)."""
    for _ in range(3):
        try:
            page = fetch(f"https://drive.google.com/embeddedfolderview?id={folder_id}").read().decode("utf-8", "ignore")
            break
        except Exception:
            page = None
    if page is None:
        return [], False
    entries = []
    for chunk in page.split('<div class="flip-entry" id="entry-')[1:]:
        href = re.search(r'<a href="([^"]+)"', chunk)
        thumb = re.search(r'<img src="(https://lh3[^"]+)"', chunk)
        icon = re.search(r'flip-entry-list-icon"><img src="([^"]*)"', chunk)
        title = re.search(r'flip-entry-title">(.*?)</div>', chunk, re.S)
        mime = re.search(r"/type/(.+)$", icon.group(1)) if icon else None
        entries.append(dict(
            id=chunk.split('"', 1)[0],
            title=html.unescape(title.group(1)).strip() if title else "",
            is_folder=bool(href and "/folders/" in href.group(1)),
            mime=mime.group(1) if mime else "",
            thumb=thumb.group(1) if thumb else "",
        ))
    return entries, True


def crawl(root_id, root_name="Raw files", workers=8):
    items, failed, seen = [], [], set()
    frontier = [(root_id, root_name)]
    with cf.ThreadPoolExecutor(workers) as ex:
        while frontier:
            batch = [f for f in frontier if f[0] not in seen and not seen.add(f[0])]
            frontier = []
            for (fid, path), (entries, ok) in zip(batch, ex.map(lambda f: list_folder(f[0]), batch)):
                if not ok:
                    failed.append(path)
                for e in entries:
                    p = f"{path}/{e['title']}"
                    if e["is_folder"]:
                        items.append(dict(id=e["id"], path=p, kind="folder"))
                        frontier.append((e["id"], p))
                    else:
                        items.append(dict(id=e["id"], path=p, kind="file", mime=e["mime"], thumb=e["thumb"]))
    return items, failed


def direct_url(file_id):
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"


_TOKEN = [None, 0.0]       # [the agent's Drive access token, when it was made]: one token for 45 minutes


def drive_token():
    """The agent's own Drive access token (drive_upload.access_token) or None without the Google variables. Reads through the Drive API
    are not stopped by the public link's download quota ("Quota exceeded": a shared library file read a lot by everyone). The token is
    only used in-process (never a command line, a log or a file)."""
    import time
    if _TOKEN[0] and time.time() - _TOKEN[1] < 2700:
        return _TOKEN[0]
    tok = None
    try:
        import contextlib
        import io
        import drive_upload
        with contextlib.redirect_stdout(io.StringIO()):
            tok = drive_upload.access_token()
    except (SystemExit, Exception):  # noqa: BLE001 - no login here: the public link still works for a file under its quota
        tok = None
    _TOKEN[:] = [tok, time.time() if tok else time.time() - 2400]      # (a failed login is tried again after ~5 minutes)
    return tok


def api_get(file_id, headers=None, query="alt=media", timeout=120):
    """GET of a Drive API file URL with the agent's token -> (status, body bytes, response headers); None without a token."""
    tok = drive_token()
    if not tok:
        return None
    req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files/{file_id}?{query}&supportsAllDrives=true",
                                 headers=dict(headers or {}, Authorization=f"Bearer {tok}"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), r.headers
    except Exception:  # noqa: BLE001
        return None


def range_bytes(file_id, off, want):
    """Bytes off .. off+want-1 of a library file: through the Drive API (the agent's token), else the public link; None when neither
    gives exactly `want` bytes (a 'Quota exceeded' page is a few KB of HTML)."""
    got = api_get(file_id, {"Range": f"bytes={off}-{off + want - 1}"})
    if got and len(got[1]) == want and got[0] in (200, 206):
        return got[1]
    try:
        r = fetch(direct_url(file_id), headers={"Range": f"bytes={off}-{off + want - 1}"}, timeout=120)
        b = r.read()
        return b if len(b) == want else None
    except Exception:  # noqa: BLE001
        return None


def file_size(file_id):
    """Size in bytes (Drive API metadata, else a 1-byte range request on the public link; does not download the file)."""
    got = api_get(file_id, query="fields=size", timeout=40)
    if got and got[0] == 200:
        try:
            return int(json.loads(got[1])["size"])
        except (ValueError, KeyError):
            pass
    for _ in range(2):
        try:
            r = fetch(direct_url(file_id), headers={"Range": "bytes=0-0"}, timeout=40)
            m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
            if m:
                return int(m.group(1))
        except Exception:
            pass
    return None


def add_sizes(items, workers=24):
    files = [i for i in items if i["kind"] == "file"]
    with cf.ThreadPoolExecutor(workers) as ex:
        for i, s in zip(files, ex.map(lambda i: file_size(i["id"]), files)):
            i["size"] = s


def summary(items):
    table = collections.defaultdict(collections.Counter)
    for i in items:
        top = i["path"].split("/")[1] if "/" in i["path"] else i["path"]
        if i["kind"] == "folder":
            table[top]["subfolders"] += 1
        else:
            kind = "video" if i["mime"].startswith("video") else "image" if i["mime"].startswith("image") else "other"
            table[top][kind] += 1
            table[top]["bytes"] += i.get("size") or 0
    print(f"{'Folder':32}{'videos':>8}{'images':>8}{'other':>7}{'GB':>8}")
    total = collections.Counter()
    for name, c in sorted(table.items(), key=lambda kv: -(kv[1]["video"] + kv[1]["image"])):
        print(f"{name[:31]:32}{c['video']:>8}{c['image']:>8}{c['other']:>7}{c['bytes'] / 2**30:>8.1f}")
        total += c
    print(f"{'TOTAL':32}{total['video']:>8}{total['image']:>8}{total['other']:>7}{total['bytes'] / 2**30:>8.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", action="store_true", help="look up every file's size (a few minutes)")
    ap.add_argument("--summary", action="store_true", help="print counts from the existing cache")
    args = ap.parse_args()

    if args.summary:
        with open(CACHE) as f:
            summary(json.load(f)["items"])
        return

    root = load_config()["drive"]["asset_library_root"]
    items, failed = crawl(root)
    if args.sizes:
        add_sizes(items)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(dict(root=root, items=items, failed=failed), f)
    n_files = sum(i["kind"] == "file" for i in items)
    print(f"Indexed {n_files} files in {sum(i['kind'] == 'folder' for i in items)} folders -> {CACHE}")
    if failed:
        print(f"WARNING: {len(failed)} folders could not be read: {failed[:5]}")
    summary(items)


if __name__ == "__main__":
    main()
