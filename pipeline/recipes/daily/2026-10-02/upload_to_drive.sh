#!/bin/bash
# Puts the 2026-10-02 test run into Drive: Outputs/2026-10-02 – Test run (40 ads)/{Statics,Videos}.
# Needs GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN in the environment (see pipeline/drive_upload.py).
# Usage: upload_to_drive.sh <day1 output dir containing statics/ and videos/>
set -e
OUT=${1:?output dir}
STATICS=1pgHxLekVpfcDiyrRaOdciPb2AFel-I0v
VIDEOS=1dZghj2eEzTNk2EpRECwotSqmO4yRCSih
UP="python3 $(dirname "$0")/../../../drive_upload.py"
$UP check
for f in "$OUT"/statics/*.png; do $UP upload "$f" --folder $STATICS; done
for f in "$OUT"/videos/*.mp4; do $UP upload "$f" --folder $VIDEOS; done
