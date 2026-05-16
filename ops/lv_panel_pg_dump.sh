#!/bin/bash
# Run ON Latvia panel host (bvpn-lv). Writes gzipped Remnawave DB dump under /opt/backups.
set -euo pipefail
BACKDIR=/opt/backups
mkdir -p "$BACKDIR"
if ! docker ps --format '{{.Names}}' | grep -qx remnawave-db; then
  echo "remnawave-db container not running" >&2
  exit 1
fi
PGP=$(docker exec remnawave-db printenv POSTGRES_PASSWORD)
PGU=$(docker exec remnawave-db printenv POSTGRES_USER)
PGD=$(docker exec remnawave-db printenv POSTGRES_DB)
TS=$(date +%Y%m%d-%H%M%S)
OUT="${BACKDIR}/panel-${TS}.sql.gz"
docker exec -e "PGPASSWORD=${PGP}" remnawave-db \
  pg_dump -h 127.0.0.1 -U "${PGU}" "${PGD}" | gzip -c > "${OUT}"
ls -lh "${OUT}"
sha256sum "${OUT}"
echo "OK: ${OUT}"
