#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PF_CONF="$SCRIPT_DIR/pf-https.conf"
if ! command -v pfctl >/dev/null 2>&1; then
  echo "pfctl not found. This tool only works on macOS." >&2
  exit 1
fi
sudo pfctl -ef "$PF_CONF"
