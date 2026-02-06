#!/usr/bin/env sh
set -eu

LABEL="com.farreru.apache-with-php"

echo "== launchd status =="
LINE="$(sudo launchctl list | awk -v lbl="$LABEL" '$3==lbl {print $0}')"

if [ -z "${LINE:-}" ]; then
  echo "NOT LOADED: $LABEL"
  exit 1
fi

PID="$(echo "$LINE" | awk '{print $1}')"
STATUS="$(echo "$LINE" | awk '{print $2}')"

echo "$LINE"
echo ""
echo "PID         : $PID"
echo "Last status : $STATUS"

if [ "$PID" = "-" ]; then
  echo "STATE: loaded but not running"
  exit 2
fi

echo ""
echo "== process info =="
ps -p "$PID" -o pid,ppid,user,command

echo ""
echo "== ports =="
sudo lsof -nP -iTCP:80 -sTCP:LISTEN || true
sudo lsof -nP -iTCP:443 -sTCP:LISTEN || true

echo ""
echo "== last logs (stderr) =="
sudo tail -n 50 /var/log/farreru-apache-with-php.err.log 2>/dev/null || true

echo ""
echo "== last logs (stdout) =="
sudo tail -n 50 /var/log/farreru-apache-with-php.out.log 2>/dev/null || true

