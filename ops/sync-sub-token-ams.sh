#!/usr/bin/env bash
# Safe replacement for the old script that read REMNAWAVE_API_TOKEN from
# /opt/remnawave/docker-compose.yml on LV and sed-inlined it into AMS sub compose
# (LV stack is gone / divergent — that pattern caused mass 502 + repeated "rotate API" churn).
#
# Rule: single writer for machine API JWT is /opt/remna-shop/.env on AMS (REMNA_API_TOKEN).
# Subscription-page reads the same value via /opt/remnawave/sub/.env + compose interpolation.
#
# Run from dev machine (repo checkout):
#   bash ops/sync-sub-token-ams.sh
set -euo pipefail
OPS_DIR=$(cd "$(dirname "$0")" && pwd)
exec ssh -o BatchMode=yes bvpn-ams "bash -s" <"${OPS_DIR}/fix-ams-subscription-api-token.sh"
