#!/usr/bin/env sh
set -eu

LABEL="com.farreru.apache-with-php"
PLIST_DST="/Library/LaunchDaemons/$LABEL.plist"

if [ ! -f "$PLIST_DST" ]; then
  echo "Plist not found: $PLIST_DST"
  echo "Service not installed."
  exit 0
fi

echo "Unloading service..."
sudo launchctl unload -w "$PLIST_DST" || true

echo "Service status:"
sudo launchctl list | grep "$LABEL" || echo "STOPPED"

