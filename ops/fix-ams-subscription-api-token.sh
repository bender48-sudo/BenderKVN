#!/usr/bin/env bash
# Run on AMS (as root): sync REMNA_API_TOKEN from shop to subscription-page stack,
# replace hardcoded JWT in sub/docker-compose.yml with ${REMNA_API_TOKEN} from sub/.env
set -euo pipefail

SHOP_ENV="${1:-/opt/remna-shop/.env}"
SUB_DIR="${2:-/opt/remnawave/sub}"

if [[ ! -r "$SHOP_ENV" ]]; then
	echo "fatal: unreadable shop env $SHOP_ENV" >&2
	exit 2
fi
if [[ ! -d "$SUB_DIR" ]]; then
	echo "fatal: missing $SUB_DIR" >&2
	exit 2
fi

TOK=$(grep "^REMNA_API_TOKEN=" "$SHOP_ENV" | cut -d= -f2-) || true
if [[ -z "${TOK:-}" ]]; then
	echo "fatal: no REMNA_API_TOKEN in $SHOP_ENV" >&2
	exit 3
fi

umask 077
printf 'REMNA_API_TOKEN=%s\n' "$TOK" >"$SUB_DIR/.env.new"
mv "$SUB_DIR/.env.new" "$SUB_DIR/.env"

dc="$SUB_DIR/docker-compose.yml"
if grep -qE '^\s*-\s*REMNAWAVE_API_TOKEN=eyJ' "$dc" 2>/dev/null; then
	ts=$(date +%Y%m%d-%H%M%S)
	cp -a "$dc" "$dc.before-api-token-fix-$ts"
	python3 <<'PY'
from pathlib import Path
import re
import sys

path = Path("/opt/remnawave/sub/docker-compose.yml")
text = path.read_text()
repl, n = re.subn(
	r"^(\s*- )REMNAWAVE_API_TOKEN=.+$",
	r"\1REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}",
	text,
	flags=re.M,
)
if n != 1:
	print(f"fatal: token line replace count={n}, expected 1", file=sys.stderr)
	sys.exit(4)
path.write_text(repl)
PY
elif ! grep -Fq '${REMNA_API_TOKEN}' "$dc"; then
	echo "fatal: $dc must set REMNAWAVE_API_TOKEN from \${REMNA_API_TOKEN} (no inlined JWT)" >&2
	exit 4
fi

(cd "$SUB_DIR" && docker compose up -d --force-recreate remnawave-subscription-page)
sleep 5
docker logs remnawave-subscription-page --tail 30
