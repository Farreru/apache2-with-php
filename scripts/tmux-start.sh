#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
APACHE_ROOT=$(cd "$SCRIPT_DIR"/.. && pwd)
SESSION=${1:-apache}
WINDOW_NAME=apache-run
START_CMD="$SCRIPT_DIR/start.sh"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux attach -t "$SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -n "$WINDOW_NAME" "cd '$APACHE_ROOT' && exec '$START_CMD'"
tmux attach -t "$SESSION"
