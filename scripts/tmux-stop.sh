#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SESSION=${1:-apache}

if tmux has-session -t "$SESSION" 2>/dev/null; then
  sudo "$SCRIPT_DIR/stop.sh"
  tmux kill-session -t "$SESSION" >/dev/null 2>&1 || true
  exit 0
fi

echo "No tmux session named $SESSION" >&2
