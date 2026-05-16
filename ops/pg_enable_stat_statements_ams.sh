#!/bin/bash
# P6-SCALE-03: enable pg_stat_statements on AMS remnawave-db (requires container recreate).
# Run on AMS as root. Safe-deploy window recommended.
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-/opt/remnawave}"
DRY=1
for arg in "$@"; do
  case "$arg" in
    --apply) DRY=0 ;;
    --dry-run) DRY=1 ;;
  esac
done

if [[ ! -f "${COMPOSE_DIR}/docker-compose.yml" ]]; then
  echo "ERROR: ${COMPOSE_DIR}/docker-compose.yml missing" >&2
  exit 1
fi

if grep -q 'shared_preload_libraries=pg_stat_statements' "${COMPOSE_DIR}/docker-compose.yml" 2>/dev/null; then
  echo "OK: compose already has pg_stat_statements preload"
else
  echo "WARN: compose missing pg_stat_statements command — sync from repo tmpl first" >&2
  if [[ "$DRY" -eq 1 ]]; then
    echo "Dry-run: would patch compose and recreate remnawave-db"
    exit 0
  fi
  exit 1
fi

if [[ "$DRY" -eq 1 ]]; then
  echo "Dry-run plan:"
  echo "  cd ${COMPOSE_DIR} && docker compose up -d --force-recreate remnawave-db"
  echo "  docker exec remnawave-db psql -U postgres -d postgres -c \"CREATE EXTENSION IF NOT EXISTS pg_stat_statements;\""
  echo "  python3 ops/pg_remnawave_audit.py  # from repo on admin host"
  exit 0
fi

cd "${COMPOSE_DIR}"
docker compose up -d --force-recreate remnawave-db
echo "Waiting for pg_isready..."
for _ in $(seq 1 30); do
  if docker exec remnawave-db pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
docker compose up -d remnawave
echo "OK: pg_stat_statements enabled; panel remnawave restarted"
