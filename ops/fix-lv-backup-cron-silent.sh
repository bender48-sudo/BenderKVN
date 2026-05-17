#!/bin/bash
# Remove legacy backup-remnawave.sh cron on LV (DB on AMS; pull-only + silent dumps).
set -euo pipefail
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
crontab -l 2>/dev/null \
  | grep -vF 'backup-remnawave.sh' \
  | grep -v '^[[:space:]]*$' >"$TMP" || true
if ! grep -qF 'pull-latest-dump-ams-to-lv.sh' "$TMP" 2>/dev/null; then
  echo '50 1,7,13,19 * * * /bin/bash /opt/scripts/pull-latest-dump-ams-to-lv.sh >> /var/log/remnawave-pull.log 2>&1' >>"$TMP"
fi
crontab "$TMP"
echo "OK: LV crontab (no backup-remnawave Telegram spam)"
crontab -l | grep -E 'backup|pull-latest|pg_dump' || echo "(no backup lines — OK if pull elsewhere)"
