#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
APACHE_ROOT=$(cd "$SCRIPT_DIR"/.. && pwd)
TMP_CONF="$APACHE_ROOT/tmp/httpd.conf"
PIDFILE="$APACHE_ROOT/tmp/httpd.pid"
HTTPD_BIN=$(PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/get_httpd_bin.py")

if [ ! -x "$HTTPD_BIN" ]; then
  echo "Error: httpd binary not found at $HTTPD_BIN"
  exit 1
fi

if [ -f "$PIDFILE" ]; then
  sudo "$HTTPD_BIN" -f "$TMP_CONF" -k stop || true
else
  echo "httpd does not appear to be running (no $PIDFILE)"
fi

for pidfile in "$APACHE_ROOT/tmp/php-fpm-"*.pid; do
  [ -f "$pidfile" ] || continue
  if pid=$(cat "$pidfile" 2>/dev/null); then
    kill -TERM "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
done
