#!/usr/bin/env bash
# Run ON AMS (as root): apply grandfather expiry + install bot_py from /tmp/bvpn-rollout.
# Push files first via scp from dev machine (see docs/DEPLOY.md §4.4).
set -euo pipefail
ROLL=/tmp/bvpn-rollout
BOT=/opt/remna-shop/src/shop_bot
CT=remna-shop-bot

if [[ ! -d "$ROLL" ]]; then
	echo "fatal: missing $ROLL (scp bot files here first)"
	exit 2
fi

_ts=$(date +%Y%m%d-%H%M%S)

_env_upsert() {
	local key="$1" val="$2" f="/opt/remna-shop/.env"
	[[ -f "$f" ]] || { echo "fatal: missing $f"; exit 3; }
	if grep -qE "^${key}=" "$f"; then
		sed -i.bak-"$_ts"-"$key" "s|^${key}=.*|${key}=${val}|" "$f"
	else
		printf '\n%s=%s\n' "$key" "$val" >>"$f"
	fi
}

echo "=== Grandfather expire (legacy users only) ==="
TOKEN=$(grep '^REMNA_API_TOKEN=' /opt/remna-shop/.env | cut -d= -f2-)
BASE=$(grep '^REMNA_BASE_URL=' /opt/remna-shop/.env | cut -d= -f2-)
export PANEL_TOKEN="$TOKEN"
export PANEL_URL="${BASE%/}"
pushd "$ROLL/grandfam" >/dev/null
PYTHONPATH=. python3 grandfather_panel_users_expire.py --apply
popd >/dev/null

echo "=== Update /opt/remna-shop/.env ==="
_env_upsert REMNA_TRIAL_DAYS "90"
_env_upsert REMNA_DEFAULT_DAYS "90"
_env_upsert TRIAL_DAYS "90"
# Пустое значение: оплата в боте выключена
if grep -qE '^BOT_PAYMENTS_LIVE=' /opt/remna-shop/.env; then
	sed -i.bak-"$_ts"-pay 's|^BOT_PAYMENTS_LIVE=.*|BOT_PAYMENTS_LIVE=|' /opt/remna-shop/.env
else
	printf '\nBOT_PAYMENTS_LIVE=\n' >>/opt/remna-shop/.env
fi

echo "=== Backup + install bot sources ==="
for pair in "$ROLL/handlers.py:$BOT/bot/handlers.py" \
	"$ROLL/keyboards.py:$BOT/bot/keyboards.py" \
	"$ROLL/config.py:$BOT/config.py" \
	"$ROLL/scheduler.py:$BOT/data_manager/scheduler.py" \
	"$ROLL/remnawave_api.py:$BOT/modules/remnawave_api.py"; do
	src=${pair%%:*}
	dst=${pair##*:}
	[[ -f "$src" ]] || { echo "fatal: missing shipped file $src"; exit 4; }
	cp -a "$dst" "${dst}.bak-trial-$_ts"
	install -m 0644 "$src" "$dst"
done

echo "=== Sync into container + restart ==="
docker cp "$BOT/bot/handlers.py" "$CT:/app/src/shop_bot/bot/handlers.py"
docker cp "$BOT/bot/keyboards.py" "$CT:/app/src/shop_bot/bot/keyboards.py"
docker cp "$BOT/config.py" "$CT:/app/src/shop_bot/config.py"
docker cp "$BOT/data_manager/scheduler.py" "$CT:/app/src/shop_bot/data_manager/scheduler.py"
docker cp "$BOT/modules/remnawave_api.py" "$CT:/app/src/shop_bot/modules/remnawave_api.py"

if [[ -f /opt/remna-shop/docker-compose.yml ]]; then
	(cd /opt/remna-shop && docker compose up -d --force-recreate remna-shop-bot)
elif docker compose version >/dev/null 2>&1 && [[ -f /opt/remna-shop/docker-compose.yaml ]]; then
	(cd /opt/remna-shop && docker compose up -d --force-recreate remna-shop-bot)
else
	docker restart "$CT"
fi
echo "DONE"
