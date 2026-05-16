#!/bin/bash
# Run on the host where Docker remnawave-db runs (Amsterdam after migration).
# From Windows: [IO.File]::ReadAllText('ops/pg_dump_remnawave.sh').Replace("`r`n","`n") | ssh bvpn-ams bash
set -euo pipefail
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
