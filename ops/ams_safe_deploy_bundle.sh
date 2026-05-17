#!/bin/bash
# AMS-side checks for smoke_ams_safe_deploy.py (P2-OPS-AMS-SAFE-DEPLOY-01)
set -eu
names=$(docker ps --format '{{.Names}}')
echo "$names" | grep -qx remnawave || echo MISSING_remnawave
echo "$names" | grep -qx remnawave-db || echo MISSING_remnawave-db
echo "$names" | grep -qx remna-shop-bot || echo MISSING_remna-shop-bot
echo "$names" | grep -q '^remnawave-subscription-page' || echo MISSING_SUB_PAGE
test -f /opt/remnawave/.env || echo MISSING_PANEL_ENV
grep -q 'connection_limit=' /opt/remnawave/.env || echo BAD_DATABASE_URL
grep -q '^POSTGRES_PASSWORD=' /opt/remnawave/.env || echo BAD_POSTGRES_PASSWORD
dc=/opt/remnawave/sub/docker-compose.yml
if [ ! -r "$dc" ]; then echo MISSING_SUB_COMPOSE; fi
if [ -r "$dc" ] && grep -qE '^\s*-\s*REMNAWAVE_API_TOKEN=eyJ' "$dc"; then echo INLINED_JWT_SUB_COMPOSE; fi
if [ -r "$dc" ] && ! grep -Fq '${REMNA_API_TOKEN}' "$dc"; then echo BAD_SUB_COMPOSE_TOKEN_REF; fi
if [ ! -r /opt/remnawave/sub/.env ]; then echo MISSING_SUB_ENV; fi
if [ -r /opt/remnawave/sub/.env ] && ! grep -q '^REMNA_API_TOKEN=' /opt/remnawave/sub/.env; then
  echo MISSING_REMNA_API_TOKEN_SUB_ENV
fi
echo BUNDLE_DONE
