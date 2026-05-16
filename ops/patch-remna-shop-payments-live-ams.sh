#!/bin/bash
# Enable BOT_PAYMENTS_LIVE=1 on AMS remna-shop (P2-COM-MONETIZE-02). Run on bvpn-ams as root.
set -euo pipefail
ENV=/opt/remna-shop/.env
ts=$(date +%Y%m%d-%H%M%S)
cp -a "$ENV" "${ENV}.before-payments-live-${ts}"

if grep -qE '^BOT_PAYMENTS_LIVE=' "$ENV"; then
  sed -i "s|^BOT_PAYMENTS_LIVE=.*|BOT_PAYMENTS_LIVE=1|" "$ENV"
else
  printf '\nBOT_PAYMENTS_LIVE=1\n' >>"$ENV"
fi

grep '^BOT_PAYMENTS_LIVE=' "$ENV"
docker restart remna-shop-bot
sleep 4
docker exec remna-shop-bot python -c "from shop_bot.config import BOT_PAYMENTS_LIVE; assert BOT_PAYMENTS_LIVE; print('BOT_PAYMENTS_LIVE=OK')"
echo "OK: remna-shop-bot restarted (backup ${ENV}.before-payments-live-${ts})"
