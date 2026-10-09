#!/usr/bin/env python3
"""Upload finished ads into the Drive Outputs folders.

Needs three environment variables in the Claude cloud environment (never in the repo):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

  check   python3 pipeline/drive_upload.py check
          Read-only: confirms the variables, gets an access token, lists the Outputs folders.
  upload  python3 pipeline/drive_upload.py upload <file> --folder <folder_id> [--name "x.mp4"]
          Resumable upload, works for large videos. Prints the new file's id and link.
  mkdir   python3 pipeline/drive_upload.py mkdir "<name>" --parent <folder_id>
          Find-or-create a folder; prints its id.
  ls      python3 pipeline/drive_upload.py ls <folder_id>            (JSON list, newest first)
  find    python3 pipeline/drive_upload.py find "<folder name>" [--parent <folder_id>]   (folder id or exit 1)
  download python3 pipeline/drive_upload.py download <file_id> --out <path>   (chunked, any size)
  export  python3 pipeline/drive_upload.py export <google_doc_id> [--out file.txt]   (Doc as plain text)

Exit code 3 means the variables are missing, so the caller falls back to delivering links.
"""
import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_library import load_config  # noqa: E402

VARS = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
API = "https://www.googleapis.com"


def access_token():
    missing = [v for v in VARS if not os.environ.get(v)]
    if missing:
        print(json.dumps(dict(ok=False, error="missing environment variables", missing=missing)))
        sys.exit(3)
    body = urllib.parse.urlencode(dict(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        grant_type="refresh_token",
    )).encode()
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=body, timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        print(json.dumps(dict(ok=False, error="token exchange failed", detail=e.read().decode()[:300])))
        sys.exit(4)


def api(method, url, token, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", **(headers or {})})
    return urllib.request.urlopen(req, timeout=600)


FOLDER = "application/vnd.google-apps.folder"
FIELDS = "id,name,mimeType,size,md5Checksum,createdTime,modifiedTime,webViewLink"


def query(token, q):
    """All files matching a Drive query (follows nextPageToken), newest first."""
    out, page = [], ""
    while True:
        url = (f"{API}/drive/v3/files?q={urllib.parse.quote(q)}&fields=nextPageToken,files({FIELDS})&pageSize=1000"
               "&orderBy=createdTime%20desc&supportsAllDrives=true&includeItemsFromAllDrives=true"
               + (f"&pageToken={page}" if page else ""))
        with api("GET", url, token) as r:
            j = json.load(r)
        out += j.get("files", [])
        page = j.get("nextPageToken")
        if not page:
            return out


def list_children(token, folder_id):
    return query(token, f"'{folder_id}' in parents and trashed = false")


def find_folder(token, name, parent=None):
    """Id of the newest folder with this exact name (optionally inside parent), or None."""
    q = f"name = '{name.replace(chr(39), chr(92) + chr(39))}' and mimeType = '{FOLDER}' and trashed = false"
    if parent:
        q += f" and '{parent}' in parents"
    hits = query(token, q)
    return hits[0]["id"] if hits else None


def download(token, file_id, dest, chunk=8 * 2**20):
    """Download any Drive file the account can read, in ranged chunks (resumes a partial .part file)."""
    with api("GET", f"{API}/drive/v3/files/{file_id}?fields=size,mimeType,name&supportsAllDrives=true", token) as r:
        meta = json.load(r)
    if meta["mimeType"].startswith("application/vnd.google-apps"):
        raise ValueError(f"{meta['name']} is a Google {meta['mimeType'].rsplit('.', 1)[-1]}: use export")
    size = int(meta.get("size", 0))
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    part = dest + ".part"
    import fcntl
    had = os.path.exists(dest)
    lock = open(dest + ".lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX)           # one writer per file: parallel renders may want the same clip
    if not had and os.path.exists(dest):       # another process finished it while we waited
        return dest
    have = os.path.getsize(part) if os.path.exists(part) else 0
    with open(part, "ab") as f:
        while have < size:
            end = min(have + chunk, size) - 1
            for attempt in range(4):
                try:
                    with api("GET", f"{API}/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true", token,
                             headers={"Range": f"bytes={have}-{end}"}) as r:
                        data = r.read()
                    break
                except (urllib.error.URLError, TimeoutError):
                    if attempt == 3:
                        raise
            f.write(data)
            have += len(data)
    os.replace(part, dest)
    return dest


def export_text(token, doc_id):
    with api("GET", f"{API}/drive/v3/files/{doc_id}/export?mimeType=text/plain", token) as r:
        return r.read().decode("utf-8-sig")


def cmd_check(_):
    token = access_token()
    drive = load_config()["drive"]
    report = dict(ok=True, folders={})
    for key in ("research_briefs_folder", "outputs_folder", "new_products_folder"):
        if not drive.get(key):
            continue
        try:
            names = [f["name"] for f in list_children(token, drive[key])]
            report["folders"][key] = dict(ok=True, items=len(names), sample=names[:5])
        except urllib.error.HTTPError as e:
            report["ok"] = False
            report["folders"][key] = dict(ok=False, error=f"HTTP {e.code}", detail=e.read().decode()[:200])
    print(json.dumps(report, indent=2))


def cmd_upload(a):
    token = access_token()
    name = a.name or os.path.basename(a.file)
    if a.skip_existing:
        same = [f for f in list_children(token, a.folder) if f["name"] == name]
        if same:
            print(json.dumps(dict(ok=True, id=same[0]["id"], name=name, link=same[0].get("webViewLink"), skipped=True)))
            return
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    size = os.path.getsize(a.file)
    meta = json.dumps(dict(name=name, parents=[a.folder])).encode()
    start = api("POST", f"{API}/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true"
                        "&fields=id,name,webViewLink", token, data=meta,
                headers={"Content-Type": "application/json; charset=UTF-8",
                         "X-Upload-Content-Type": ctype, "X-Upload-Content-Length": str(size)})
    session = start.headers["Location"]
    with open(a.file, "rb") as f:
        req = urllib.request.Request(session, data=f.read(), method="PUT",
                                     headers={"Content-Type": ctype, "Content-Length": str(size)})
    with urllib.request.urlopen(req, timeout=1800) as r:
        info = json.load(r)
    print(json.dumps(dict(ok=True, id=info["id"], name=info["name"], link=info.get("webViewLink"))))


def cmd_mkdir(a):
    """Find-or-create a folder by name under a parent; prints its id (safe to re-run)."""
    token = access_token()
    fid = find_folder(token, a.name, a.parent)
    if fid:
        print(fid)
        return
    meta = json.dumps(dict(name=a.name, parents=[a.parent], mimeType="application/vnd.google-apps.folder")).encode()
    with api("POST", f"{API}/drive/v3/files?supportsAllDrives=true&fields=id", token, data=meta,
             headers={"Content-Type": "application/json; charset=UTF-8"}) as r:
        print(json.load(r)["id"])


def cmd_ls(a):
    print(json.dumps(list_children(access_token(), a.folder), indent=1))


def cmd_find(a):
    fid = find_folder(access_token(), a.name, a.parent)
    if not fid:
        sys.exit(1)
    print(fid)


def cmd_download(a):
    print(download(access_token(), a.file_id, a.out))


def cmd_export(a):
    txt = export_text(access_token(), a.doc_id)
    if a.out:
        open(a.out, "w").write(txt)
        print(a.out)
    else:
        print(txt)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    u = sub.add_parser("upload")
    u.add_argument("file")
    u.add_argument("--folder", required=True)
    u.add_argument("--name", default="")
    u.add_argument("--skip-existing", action="store_true", help="do nothing if the folder already has a file with this name")
    m = sub.add_parser("mkdir")
    m.add_argument("name")
    m.add_argument("--parent", required=True)
    ls = sub.add_parser("ls")
    ls.add_argument("folder")
    fd = sub.add_parser("find")
    fd.add_argument("name")
    fd.add_argument("--parent")
    dl = sub.add_parser("download")
    dl.add_argument("file_id")
    dl.add_argument("--out", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("doc_id")
    ex.add_argument("--out")
    a = ap.parse_args()
    {"check": cmd_check, "upload": cmd_upload, "mkdir": cmd_mkdir, "ls": cmd_ls, "find": cmd_find,
     "download": cmd_download, "export": cmd_export}[a.cmd](a)


if __name__ == "__main__":
    main()
