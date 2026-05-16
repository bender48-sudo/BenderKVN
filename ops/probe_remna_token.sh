#!/usr/bin/env bash
# Probe REMNA JWT against /api/hosts (no token printed). Usage: probe_remna_token.sh <env-file>
set -euo pipefail
ENV_FILE=${1:?env file}
URL=${2:-https://k9x2m1.conntest.xyz:2053}
# shellcheck disable=SC1090
source "$ENV_FILE"
TOK="${REMNA_API_TOKEN:-${PANEL_TOKEN:-}}"
code=$(curl -sS -o /dev/null -w "%{http_code}" \
	-H "Authorization: Bearer ${TOK}" \
	-H "X-Forwarded-Proto: https" \
	"${URL}/api/hosts" --connect-timeout 10 --max-time 20 || echo 000)
echo "file=$(basename "$ENV_FILE") http=${code} len=${#TOK}"
