#!/bin/bash
set -euo pipefail
docker stop remna-shop-bot || true
docker cp /opt/remna-shop/src/shop_bot/. remna-shop-bot:/app/src/shop_bot/
docker start remna-shop-bot
sleep 3
docker exec remna-shop-bot pip install -q 'tenacity>=8.2,<10'
docker restart remna-shop-bot
sleep 12
docker logs remna-shop-bot --tail 12
