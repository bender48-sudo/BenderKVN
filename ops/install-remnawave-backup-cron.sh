#!/bin/bash
# Idempotent crontab lines for P2-BAK-01 (AMS dump + LV pull). Run as root on target host.
set -euo pipefail

ROLE="${1:-}"
case "${ROLE}" in
  ams)
    LINE='5 */6 * * * /bin/bash /opt/scripts/pg_dump_remnawave.sh >> /var/log/pg_dump_remnawave.log 2>&1'
    MARKER='pg_dump_remnawave.sh'
    ;;
  lv)
    LINE='15 */6 * * * /bin/bash /opt/scripts/pull-latest-dump-ams-to-lv.sh >> /var/log/remnawave-pull.log 2>&1'
    MARKER='pull-latest-dump-ams-to-lv.sh'
    ;;
  *)
    echo "Usage: $0 ams|lv" >&2
    exit 2
    ;;
esac

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
crontab -l 2>/dev/null | sort -u >"$TMP" || true
if grep -Fq "${MARKER}" "$TMP"; then
  echo "OK: crontab already has ${MARKER}"
else
  echo "${LINE}" >>"$TMP"
  crontab "$TMP"
  echo "OK: crontab line added for ${ROLE}"
fi
crontab -l | grep -F "${MARKER}" || true
