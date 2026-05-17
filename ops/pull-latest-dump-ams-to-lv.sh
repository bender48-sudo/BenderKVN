#!/bin/bash
# Run ON Latvia (or any host with SSH+scp to AMS and local /opt/backups).
# From Windows: scp ops/pull-latest-dump-ams-to-lv.sh bvpn-lv:/tmp/ && ssh bvpn-lv "sed -i 's/\r$//' /tmp/pull-latest-dump-ams-to-lv.sh; bash /tmp/pull-latest-dump-ams-to-lv.sh"
# Pulls latest /opt/backups/remnawave-*.sql.gz from AMS and verifies SHA256.
set -euo pipefail

_notify_pull_fail() {
  local msg="$1"
  for f in /etc/bvpn/balancer.env /opt/remna-shop/.env; do
    if [ -f "$f" ]; then
      # shellcheck disable=SC1091
      source "$f"
      break
    fi
  done
  BOT_TOKEN="${BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
  ADMIN_CHAT_ID="${ADMIN_CHAT_ID:-${ADMIN_TELEGRAM_ID:-}}"
  [ -n "${BOT_TOKEN:-}" ] && [ -n "${ADMIN_CHAT_ID:-}" ] || return 0
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d "chat_id=${ADMIN_CHAT_ID}" \
    --data-urlencode "text=❌ Remnawave pull AMS→LV failed: ${msg}" >/dev/null 2>&1 || true
}

trap '_notify_pull_fail "exit code $? (see /var/log/remnawave-pull.log)"' ERR
AMS_IP="${AMS_IP:-168.100.11.140}"
AMS_PORT="${AMS_PORT:-3344}"
SSH=(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 -p "${AMS_PORT}" "root@${AMS_IP}")
SCP=(scp -o StrictHostKeyChecking=no -o ConnectTimeout=20 -P "${AMS_PORT}")
LOCAL_DIR="${LOCAL_DIR:-/opt/backups}"
mkdir -p "${LOCAL_DIR}"
REMOTE="$("${SSH[@]}" 'ls -1t /opt/backups/remnawave-*.sql.gz 2>/dev/null | head -1' | tr -d '\r')"
if [[ -z "${REMOTE}" ]]; then
  echo "ERROR: no remnawave-*.sql.gz on ${AMS_IP}" >&2
  exit 1
fi
BASE="$(basename "${REMOTE}")"
LOCAL="${LOCAL_DIR}/${BASE}"
echo "Remote: ${AMS_IP}:${REMOTE}"
EXP="$("${SSH[@]}" "sha256sum \"$REMOTE\"" | tr -d '\r' | cut -d' ' -f1)"
echo "Expected SHA256: ${EXP}"
"${SCP[@]}" "root@${AMS_IP}:${REMOTE}" "${LOCAL}.partial"
mv -f "${LOCAL}.partial" "${LOCAL}"
GOT="$(sha256sum "${LOCAL}" | cut -d' ' -f1)"
echo "Local file:  ${LOCAL}"
echo "Got SHA256:  ${GOT}"
if [[ "${EXP}" != "${GOT}" ]]; then
  echo "ERROR: hash mismatch" >&2
  exit 1
fi
echo "OK — copy verified."
ls -lh "${LOCAL}"
