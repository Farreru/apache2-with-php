#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
if [ -n "$TMUX" ] || [ -n "$STY" ]; then
  exit 0
fi
"$SCRIPT_DIR/start.sh"
