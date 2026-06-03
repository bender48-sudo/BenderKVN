#!/usr/bin/env bash
# LV node failover auto — run on AMS when LV SSH is down (panel token from shop).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${AMS_SHOP_ENV:-/opt/remna-shop/.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
export PANEL_URL="${REMNA_BASE_URL:-${REMNA_API_URL:-http://127.0.0.1:3000}}"
export PANEL_TOKEN="${REMNA_API_TOKEN:-${PANEL_TOKEN:-}}"
exec python3 "${OPS}/lv_node_failover_auto.py" --apply "$@"
