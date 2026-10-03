#!/bin/bash
# Uploads the 2026-10-02 test run (22 statics + 20 videos) into Drive:
#   Outputs/2026-10-02 – Test run (40 ads)/Statics  and  /Videos
# Works on a fresh machine: downloads the full-quality files from the permanent links in hosted.json first.
# Needs GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN (cloud environment variables).
# Usage: bash pipeline/recipes/daily/2026-10-02/upload_to_drive.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
STATICS=1pgHxLekVpfcDiyrRaOdciPb2AFel-I0v
VIDEOS=1dZghj2eEzTNk2EpRECwotSqmO4yRCSih
UP="python3 $HERE/../../../drive_upload.py"
WORK=${TMPDIR:-/tmp}/run_2026-10-02; mkdir -p "$WORK"
$UP check
python3 - "$HERE/hosted.json" "$WORK" <<'P'
import json, sys, os, urllib.request
m = json.load(open(sys.argv[1]))
for name, v in sorted(m.items()):
    out = os.path.join(sys.argv[2], name)
    if not os.path.exists(out):
        urllib.request.urlretrieve(v["url"], out)
    print("got", name, os.path.getsize(out))
P
for f in "$WORK"/S*.png; do $UP upload "$f" --folder $STATICS; done
for f in "$WORK"/V*.mp4; do $UP upload "$f" --folder $VIDEOS; done
echo "DONE"
