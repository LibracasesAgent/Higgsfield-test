#!/bin/bash
# Installs ffmpeg (pipeline/media.py cuts clips from Drive) and tesseract (ai_gen.py gate reads the AI ads' words back) in Claude Code
# cloud sessions.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
export DEBIAN_FRONTEND=noninteractive
for pkg in ffmpeg:ffmpeg tesseract:tesseract-ocr; do
  cmd=${pkg%%:*}; deb=${pkg##*:}
  command -v "$cmd" >/dev/null 2>&1 && continue
  apt-get install -y -qq "$deb" >/dev/null 2>&1 || { apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq "$deb" >/dev/null 2>&1; } || true
  command -v "$cmd" >/dev/null 2>&1 && echo "$cmd ready" || echo "WARNING: $cmd install failed"
done
