#!/bin/bash
# AMS: expose remna-shop webhook :1488 to LV only (UFW + compose bind)
set -euo pipefail

LV_IP="${LV_PANEL_IP:-176.126.162.158}"
COMPOSE=/opt/remna-shop/docker-compose.yml
ENV=/opt/remna-shop/.env

ts=$(date +%Y%m%d-%H%M%S)
cp -a "$COMPOSE" "${COMPOSE}.before-webhook-port-${ts}"

python3 - "$COMPOSE" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
old = '"127.0.0.1:1488:1488"'
new = '"1488:1488"'
if new in text:
    print("OK: compose already binds 1488")
elif old not in text:
    print("ERROR: expected 127.0.0.1:1488 bind", file=sys.stderr)
    sys.exit(1)
else:
    open(path, "w", encoding="utf-8").write(text.replace(old, new, 1))
    print("OK: compose bind 1488:1488")
PY

grep -q '^WEBHOOK_ALLOWED_IPS=' "$ENV" 2>/dev/null && sed -i '/^WEBHOOK_ALLOWED_IPS=/d' "$ENV"
echo "WEBHOOK_ALLOWED_IPS=127.0.0.1/32,::1/128,${LV_IP}/32" >> "$ENV"

ufw allow from "$LV_IP" to any port 1488 proto tcp comment 'bot-webhook-from-lv' >/dev/null 2>&1 || true
ufw status numbered | grep 1488 || true

cd /opt/remna-shop && docker compose up -d remna-shop-bot
sleep 4
ss -tlnp | grep 1488 || true
echo "AMS_WEBHOOK_PORT_OK"
