#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
APACHE_ROOT=$(cd "$SCRIPT_DIR"/.. && pwd)
TMP_CONF="$APACHE_ROOT/tmp/httpd.conf"
HTTPD_BIN=$(PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/get_httpd_bin.py")

ensure_not_root() {
  if grep -q "^User[[:space:]]\+root\\b" "$TMP_CONF"; then
    echo "FATAL: Apache configured to run as root" >&2
    exit 1
  fi
  if grep -q "^Group[[:space:]]\+root\\b" "$TMP_CONF"; then
    echo "FATAL: Apache configured to run as root" >&2
    exit 1
  fi
}

if [ ! -x "$HTTPD_BIN" ]; then
  echo "Error: httpd binary not found at $HTTPD_BIN" >&2
  exit 1
fi

cd "$APACHE_ROOT"
PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/ensure_php_fpm.py"
PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/update_hosts.py"
"$SCRIPT_DIR/generate_httpd_conf.py" --output "$TMP_CONF"
"$SCRIPT_DIR/ensure_ssl.sh"
ensure_not_root
#exec sudo "$HTTPD_BIN" -f "$TMP_CONF" -k start -DFOREGROUND

# NEW SCRIPTS
PIDFILE="$APACHE_ROOT/tmp/httpd.pid"

if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Apache already running with PID $OLD_PID"
    exit 0
  fi
  echo "Removing stale pidfile $PIDFILE"
  rm -f "$PIDFILE"
fi

exec "$HTTPD_BIN" -f "$TMP_CONF" -DFOREGROUND

