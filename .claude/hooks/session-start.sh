#!/bin/bash
# Installs ffmpeg in Claude Code cloud sessions (used by pipeline/media.py to cut clips from Drive).
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
command -v ffmpeg >/dev/null 2>&1 && exit 0
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq ffmpeg >/dev/null 2>&1 || { apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq ffmpeg >/dev/null 2>&1; }
command -v ffmpeg >/dev/null 2>&1 && echo "ffmpeg ready" || echo "WARNING: ffmpeg install failed"
