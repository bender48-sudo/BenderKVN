#!/bin/bash
# Run on the host where Docker remnawave-db runs (Amsterdam after migration).
# From Windows: [IO.File]::ReadAllText('ops/pg_dump_remnawave.sh').Replace("`r`n","`n") | ssh bvpn-ams bash
set -euo pipefail

_notify_pg_dump_fail() {
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
    --data-urlencode "text=❌ Remnawave pg_dump on $(hostname -s): ${msg}" >/dev/null 2>&1 || true
}

trap '_notify_pg_dump_fail "exit code $? (see /var/log/pg_dump_remnawave.log)"' ERR

OUT_DIR="${OUT_DIR:-/opt/backups}"
mkdir -p "$OUT_DIR"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="${OUT_DIR}/remnawave-${TS}.sql.gz"
if ! docker ps --format '{{.Names}}' | grep -qx 'remnawave-db'; then
  echo "ERROR: remnawave-db not running on this host (panel DB is usually on AMS)." >&2
  exit 1
fi
PGP="$(docker exec remnawave-db printenv POSTGRES_PASSWORD)"
PGU="$(docker exec remnawave-db printenv POSTGRES_USER)"
PGD="$(docker exec remnawave-db printenv POSTGRES_DB)"
echo "Dumping ${PGD} as ${PGU} -> ${OUT}"
docker exec -e "PGPASSWORD=${PGP}" remnawave-db \
  pg_dump -h 127.0.0.1 -U "${PGU}" "${PGD}" | gzip -c > "${OUT}"
ls -lh "${OUT}"
sha256sum "${OUT}"
echo "Keep this hash; after any copy, sha256sum must match."
