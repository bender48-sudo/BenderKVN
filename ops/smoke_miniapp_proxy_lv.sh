#!/usr/bin/env bash
# Verify the LV proxy allowlist forwards every new Mini App path (run AFTER applying the
# setup_verify_service.py allowlist + restarting bvpn-setup-verify). The proxy injects the
# portal secret, so we hit the public edge without it. A 404 = allowlist MISS (fail); a
# forwarded path returns 200/403 (gated) = PASS.
#
# Usage:  BASE=https://<portal-host>/setup/api TID=<telegram_id> bash smoke_miniapp_proxy_lv.sh
set -uo pipefail
BASE="${BASE:?set BASE=https://<portal-host>/setup/api}"
TID="${TID:-0}"
fail=0

check() {
  local name="$1" path="$2" data="$3"
  local code
  code=$(curl -sS -o /tmp/mp_smoke.out -w '%{http_code}' -X POST \
    -H 'Content-Type: application/json' -d "$data" "$BASE$path" || echo 000)
  if [ "$code" = "404" ] || [ "$code" = "000" ]; then
    echo "[FAIL] ${name} -> http=${code} (allowlist miss / unreachable)"; fail=$((fail+1)); return
  fi
  echo "[PASS] ${name} -> http=${code} $(head -c 120 /tmp/mp_smoke.out)"
}

check home           /home            "{\"telegram_id\":$TID}"
check tariff         /tariff          '{}'
check transactions   /transactions    "{\"telegram_id\":$TID}"
check create-payment /create-payment  "{\"telegram_id\":$TID,\"amount_rub\":600}"
check referral       /referral        "{\"telegram_id\":$TID}"
check cabinet        /cabinet         "{\"telegram_id\":$TID}"
check tickets        /tickets         "{\"telegram_id\":$TID}"
check unread         /unread          "{\"telegram_id\":$TID}"
check ticket         /ticket          "{\"telegram_id\":$TID,\"subject\":\"connection\",\"text\":\"smoke\"}"
check ticket-get     /ticket-get      "{\"telegram_id\":$TID,\"ticket_id\":1}"
check ticket-message /ticket-message  "{\"telegram_id\":$TID,\"ticket_id\":1,\"text\":\"x\"}"
check fortune        /fortune         "{\"telegram_id\":$TID}"
check fortune-spin   /fortune-spin    "{\"telegram_id\":$TID}"

if [ "$fail" -eq 0 ]; then echo "=== ALL PROXY PATHS FORWARDED ==="; exit 0; fi
echo "=== ${fail} PATH(S) NOT FORWARDED (allowlist) ==="; exit 2
