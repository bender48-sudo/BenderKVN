#!/bin/bash
# Add Prisma connection_limit to /opt/remnawave/.env on AMS (P6-RED-PG-01).
# Idempotent. Recreates remnawave only — not remnawave-db.
set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/remnawave/.env}"
LIMIT="${PRISMA_CONNECTION_LIMIT:-15}"
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "Usage: $0 [--dry-run]" >&2; exit 2 ;;
  esac
done

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing $ENV_FILE" >&2
  exit 1
fi

if grep -q 'connection_limit=' "$ENV_FILE" 2>/dev/null; then
  echo "OK: connection_limit already present in $ENV_FILE"
  grep '^DATABASE_URL=' "$ENV_FILE" | sed 's/:[^:@]*@/:***@/'
  exit 0
fi

ts=$(date +%Y%m%d-%H%M%S)
cp -a "$ENV_FILE" "${ENV_FILE}.before-pg-pool-${ts}"

python3 - "$ENV_FILE" "$LIMIT" <<'PY'
import re
import sys

path, limit = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
pat = re.compile(r'^(DATABASE_URL="postgresql://[^"]+)"\s*$', re.M)

def repl(m):
    url = m.group(1)
    if "?" in url:
        return f'{url}&connection_limit={limit}&connect_timeout=10&pool_timeout=20"'
    return f'{url}?connection_limit={limit}&connect_timeout=10&pool_timeout=20"'

new, n = pat.subn(repl, text, count=1)
if n != 1:
    sys.exit("DATABASE_URL line not found or already has query params in unexpected form")
open(path, "w", encoding="utf-8").write(new)
print(f"patched DATABASE_URL connection_limit={limit}")
PY

if [ "$DRY_RUN" = "1" ]; then
  echo "[dry-run] would: docker compose -f /opt/remnawave/docker-compose.yml up -d --no-deps --force-recreate remnawave"
  exit 0
fi

cd /opt/remnawave
docker compose up -d --no-deps --force-recreate remnawave
echo "OK: remnawave recreated with pool limits"
