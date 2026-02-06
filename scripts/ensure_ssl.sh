#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
python3 "$SCRIPT_DIR/ensure_ssl.py"
