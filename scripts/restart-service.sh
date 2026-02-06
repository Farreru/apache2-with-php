#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/stop-service.sh"
sleep 1
"$SCRIPT_DIR/start-service.sh"

