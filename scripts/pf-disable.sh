#!/usr/bin/env sh
set -eu
if ! command -v pfctl >/dev/null 2>&1; then
  echo "pfctl not found; cannot disable." >&2
  exit 1
fi
sudo pfctl -F all -f /etc/pf.conf
