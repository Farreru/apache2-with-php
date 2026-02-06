#!/usr/bin/env sh
set -eu

LABEL="com.farreru.apache-with-php"
PLIST_NAME="$LABEL.plist"
PLIST_DST="/Library/LaunchDaemons/$PLIST_NAME"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
START_SH="$PROJECT_ROOT/scripts/start.sh"

OUT_LOG="/var/log/farreru-apache-with-php.out.log"
ERR_LOG="/var/log/farreru-apache-with-php.err.log"

if [ ! -f "$START_SH" ]; then
  echo "ERROR: start.sh not found at $START_SH" >&2
  exit 1
fi

generate_plist() {
  sudo tee "$PLIST_DST" >/dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>$START_SH</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>

  <key>ThrottleInterval</key>
  <integer>5</integer>

  <key>WorkingDirectory</key>
  <string>$PROJECT_ROOT</string>

  <key>StandardOutPath</key>
  <string>$OUT_LOG</string>

  <key>StandardErrorPath</key>
  <string>$ERR_LOG</string>
</dict>
</plist>
EOF

  sudo chown root:wheel "$PLIST_DST"
  sudo chmod 644 "$PLIST_DST"
}

if [ ! -f "$PLIST_DST" ]; then
  echo "Installing plist: $PLIST_DST"
  generate_plist
else
  echo "Plist already exists: $PLIST_DST"
fi

echo "Loading service..."
sudo launchctl unload -w "$PLIST_DST" 2>/dev/null || true
sudo launchctl load -w "$PLIST_DST"

echo "Service status:"
sudo launchctl list | grep "$LABEL" || true

