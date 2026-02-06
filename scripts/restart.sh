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

if [ -f "$PIDFILE" ]; then
  sudo kill -HUP "$(cat "$PIDFILE")" || true
fi
PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/ensure_php_fpm.py"
PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/update_hosts.py"
"$SCRIPT_DIR/generate_httpd_conf.py" --output "$TMP_CONF"
"$SCRIPT_DIR/ensure_ssl.sh"
ensure_not_root
sudo "$HTTPD_BIN" -f "$TMP_CONF" -k restart
