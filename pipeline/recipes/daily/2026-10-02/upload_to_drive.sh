#!/bin/bash
# Uploads the test run (22 statics + 20 videos) into Drive:
#   Outputs/oct 3 test/Statics  and  Outputs/oct 3 test/Videos   (folders are created if missing)
# Works on a fresh machine: downloads the full-quality files from the permanent links in hosted.json first.
# Needs GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN (cloud environment variables).
# Usage: bash pipeline/recipes/daily/2026-10-02/upload_to_drive.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
OUTPUTS=1k6VzbHgOoIAFDAVWQeaf6xx-_mJh98sK
FOLDER_NAME="oct 3 test"
UP="python3 $HERE/../../../drive_upload.py"
WORK=${TMPDIR:-/tmp}/run_2026-10-02; mkdir -p "$WORK"
$UP check
RUN=$($UP mkdir "$FOLDER_NAME" --parent $OUTPUTS)
STATICS=$($UP mkdir "Statics" --parent "$RUN")
VIDEOS=$($UP mkdir "Videos" --parent "$RUN")
echo "folder: https://drive.google.com/drive/folders/$RUN"
python3 - "$HERE/hosted.json" "$WORK" <<'P'
import json, sys, os, urllib.request
m = json.load(open(sys.argv[1]))
for name, v in sorted(m.items()):
    out = os.path.join(sys.argv[2], name)
    if not os.path.exists(out):
        urllib.request.urlretrieve(v["url"], out)
    print("got", name, os.path.getsize(out))
P
for f in "$WORK"/S*.png; do $UP upload "$f" --folder "$STATICS"; done
for f in "$WORK"/V*.mp4; do $UP upload "$f" --folder "$VIDEOS"; done
echo "DONE: https://drive.google.com/drive/folders/$RUN"
