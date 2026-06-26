#!/bin/bash
# Run ON Latvia (or any host with SSH+scp to AMS and local /opt/backups).
# From Windows: pwsh -File ops/deploy_ams_ops_private_to_lv.ps1
# Pulls latest /opt/backups/remnawave-*.sql.gz from AMS and verifies SHA256.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/ams_ops_env.sh"

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

mapfile -t _SSH_BASE < <(ams_ops_ssh_base)
SSH=(ssh "${_SSH_BASE[@]}")
mapfile -t _SCP_BASE < <(ams_ops_scp_base)
SCP=(scp "${_SCP_BASE[@]}")

LOCAL_DIR="${LOCAL_DIR:-/opt/backups}"
mkdir -p "${LOCAL_DIR}"
REMOTE="$("${SSH[@]}" 'ls -1t /opt/backups/remnawave-*.sql.gz 2>/dev/null | head -1' | tr -d '\r')"
if [[ -z "${REMOTE}" ]]; then
  echo "ERROR: no remnawave-*.sql.gz on ${AMS_OPS_IP}" >&2
  exit 1
fi
BASE="$(basename "${REMOTE}")"
LOCAL="${LOCAL_DIR}/${BASE}"
echo "Remote: ${AMS_OPS_IP}:${REMOTE}"
EXP="$("${SSH[@]}" "sha256sum \"$REMOTE\"" | tr -d '\r' | cut -d' ' -f1)"
echo "Expected SHA256: ${EXP}"
"${SCP[@]}" "root@${AMS_OPS_IP}:${REMOTE}" "${LOCAL}.partial"
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
