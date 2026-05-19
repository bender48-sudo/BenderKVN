#!/bin/bash
# P2-RED-SELFSTEAL-SNI-01: replace api.github.com:9443 decoy with www.yandex.ru:9443 on LV.
set -euo pipefail
CADDYFILE="${1:-/etc/caddy/Caddyfile}"
if grep -q 'api.github.com:9443' "$CADDYFILE"; then
  cp -a "$CADDYFILE" "${CADDYFILE}.bak-pre-selfsteal-sni"
  sed -i 's/api\.github\.com/www.yandex.ru/g' "$CADDYFILE"
  echo "patched github -> yandex in $CADDYFILE"
else
  echo "no api.github.com:9443 block (already patched?)"
fi
caddy validate --config "$CADDYFILE"
systemctl restart caddy
echo "SELFSTEAL_SNI_PATCH_OK"
