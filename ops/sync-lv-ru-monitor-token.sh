#!/usr/bin/env bash
# Sync REMNA_API_TOKEN in ru-monitor.env from balancer.env (PANEL_TOKEN).
# Run on bvpn-lv as root, or: ssh root@bvpn-lv 'bash -s' < ops/sync-lv-ru-monitor-token.sh
set -euo pipefail

BAL=/etc/bvpn/balancer.env
RU=/etc/bvpn/ru-monitor.env

if [[ ! -f "$BAL" || ! -f "$RU" ]]; then
	echo "fatal: missing $BAL or $RU" >&2
	exit 1
fi

# shellcheck disable=SC1090
source "$BAL"
NEW="${PANEL_TOKEN:-${REMNA_API_TOKEN:-}}"
if [[ -z "$NEW" ]]; then
	echo "fatal: no PANEL_TOKEN/REMNA_API_TOKEN in $BAL" >&2
	exit 1
fi

URL=$(grep -m1 '^REMNA_API_URL=' "$RU" | cut -d= -f2- | tr -d "\"'")
URL="${URL:-${PANEL_URL:-https://k9x2m1.conntest.xyz:2053}}"

OLD=$(grep -m1 '^REMNA_API_TOKEN=' "$RU" | cut -d= -f2- | tr -d "\"'" || true)
if [[ "$OLD" == "$NEW" ]]; then
	echo "sync: already matches balancer token"
else
	ts=$(date +%Y%m%d-%H%M%S)
	cp -a "$RU" "${RU}.before-sync-${ts}"
	# Preserve other keys; replace REMNA_API_TOKEN line only.
	tmp=$(mktemp)
	awk -v tok="$NEW" '
		/^REMNA_API_TOKEN=/ { print "REMNA_API_TOKEN=" tok; next }
		{ print }
	' "$RU" >"$tmp"
	mv "$tmp" "$RU"
	chmod 600 "$RU"
	echo "sync: updated REMNA_API_TOKEN from balancer (backup ${RU}.before-sync-${ts})"
fi

code=$(curl -sS -o /dev/null -w "%{http_code}" \
	-H "Authorization: Bearer ${NEW}" \
	-H "X-Forwarded-Proto: https" \
	"${URL}/api/hosts" --connect-timeout 10 --max-time 20 || echo 000)
echo "probe_hosts_http=${code}"
if [[ "$code" != "200" ]]; then
	echo "fatal: API probe failed (expected 200)" >&2
	exit 1
fi
echo "SYNC_LV_RU_MONITOR_TOKEN_OK"
