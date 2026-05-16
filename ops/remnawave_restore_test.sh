#!/bin/bash
# Quarterly restore test (P2-OPS-RESTORE-TEST-01) — isolated Postgres, no prod DB touch.
# Run on bvpn-lv as root. Uses latest /opt/backups/remnawave-*.sql.gz unless DUMP= set.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/backups}"
DUMP="${DUMP:-}"
PGIMG="${PGIMG:-postgres:17}"
PORT="${RESTORE_TEST_PORT:-55432}"
CONTAINER="${RESTORE_TEST_CONTAINER:-remnawave-restore-test}"

if [[ -z "${DUMP}" ]]; then
  DUMP="$(ls -1t "${BACKUP_DIR}"/remnawave-*.sql.gz 2>/dev/null | head -1 || true)"
fi
if [[ -z "${DUMP}" || ! -f "${DUMP}" ]]; then
  echo "ERROR: no dump file (set DUMP= or place remnawave-*.sql.gz in ${BACKUP_DIR})" >&2
  exit 1
fi

if ! command -v docker >/dev/null; then
  echo "ERROR: docker required" >&2
  exit 1
fi

# Dump from pg_dump uses OWNER postgres — match prod role name in ephemeral instance.
PGPASS="${RESTORE_TEST_PG_PASS:-restoretest}"
PGUSER="${RESTORE_TEST_PG_USER:-postgres}"
PGDB="${RESTORE_TEST_PG_DB:-postgres}"
LOG="/tmp/remnawave-restore-test-$(date +%Y%m%d-%H%M%S).log"
START_TS="$(date -Iseconds)"

cleanup() {
  docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> dump: ${DUMP} ($(du -h "${DUMP}" | cut -f1))"
echo "==> image: ${PGIMG} (ephemeral container ${CONTAINER})"

docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
docker run -d --name "${CONTAINER}" \
  -e "POSTGRES_USER=${PGUSER}" \
  -e "POSTGRES_PASSWORD=${PGPASS}" \
  -e "POSTGRES_DB=${PGDB}" \
  -p "127.0.0.1:${PORT}:5432" \
  "${PGIMG}" >/dev/null

for _ in $(seq 1 60); do
  if docker exec "${CONTAINER}" pg_isready -U "${PGUSER}" -d "${PGDB}" -q 2>/dev/null; then
    break
  fi
  sleep 1
done
docker exec "${CONTAINER}" pg_isready -U "${PGUSER}" -d "${PGDB}" -q

echo "==> restore (log: ${LOG})"
set +e
zcat "${DUMP}" | docker exec -i -e "PGPASSWORD=${PGPASS}" "${CONTAINER}" \
  psql -v ON_ERROR_STOP=1 -U "${PGUSER}" -d "${PGDB}" >"${LOG}" 2>&1
RC=$?
set -e

if grep -Eiq '(^ERROR:|^FATAL:)' "${LOG}"; then
  echo "ERROR: psql reported errors (see ${LOG})" >&2
  tail -30 "${LOG}" >&2
  exit 1
fi
if [[ "${RC}" -ne 0 ]]; then
  echo "ERROR: psql exit ${RC} (see ${LOG})" >&2
  tail -30 "${LOG}" >&2
  exit 1
fi

TABLES="$(
  docker exec -e "PGPASSWORD=${PGPASS}" "${CONTAINER}" \
    psql -U "${PGUSER}" -d "${PGDB}" -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" \
    | tr -d '[:space:]'
)"
MIGRATIONS="$(
  docker exec -e "PGPASSWORD=${PGPASS}" "${CONTAINER}" \
    psql -U "${PGUSER}" -d "${PGDB}" -tAc \
    "SELECT count(*) FROM public._prisma_migrations;" 2>/dev/null | tr -d '[:space:]' || echo 0
)"

if [[ -z "${TABLES}" || "${TABLES}" -lt 5 ]]; then
  echo "ERROR: expected >=5 public tables, got '${TABLES}'" >&2
  exit 1
fi

END_TS="$(date -Iseconds)"
PGVER="$(docker exec "${CONTAINER}" psql -U "${PGUSER}" -d "${PGDB}" -tAc 'SHOW server_version;' | tr -d '[:space:]')"

echo "OK: restore test passed"
echo "  started:  ${START_TS}"
echo "  finished: ${END_TS}"
echo "  dump:     ${DUMP}"
echo "  postgres: ${PGVER}"
echo "  tables:   ${TABLES} (public)"
echo "  prisma_migrations rows: ${MIGRATIONS}"
echo "  log:      ${LOG}"
