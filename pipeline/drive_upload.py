#!/usr/bin/env python3
"""Upload finished ads into the Drive Outputs folders.

Needs three environment variables in the Claude cloud environment (never in the repo):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

  check   python3 pipeline/drive_upload.py check
          Read-only: confirms the variables, gets an access token, lists the Outputs folders.
  upload  python3 pipeline/drive_upload.py upload <file> --folder <folder_id> [--name "x.mp4"]
          Resumable upload, works for large videos. Prints the new file's id and link.

Exit code 3 means the variables are missing, so the caller falls back to delivering links.
"""
import argparse
import json
import mimetypes
import os
import sys
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


def list_children(token, folder_id):
    q = urllib.parse.quote(f"'{folder_id}' in parents and trashed = false")
    url = (f"{API}/drive/v3/files?q={q}&fields=files(id,name,mimeType)&pageSize=100"
           "&supportsAllDrives=true&includeItemsFromAllDrives=true")
    with api("GET", url, token) as r:
        return json.load(r)["files"]


def cmd_check(_):
    token = access_token()
    drive = load_config()["drive"]
    report = dict(ok=True, folders={})
    for key in ("research_briefs_folder", "outputs_folder", "outputs_test_images", "outputs_winner_videos"):
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


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    u = sub.add_parser("upload")
    u.add_argument("file")
    u.add_argument("--folder", required=True)
    u.add_argument("--name", default="")
    a = ap.parse_args()
    {"check": cmd_check, "upload": cmd_upload}[a.cmd](a)


if __name__ == "__main__":
    main()
