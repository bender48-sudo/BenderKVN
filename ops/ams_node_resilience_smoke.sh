#!/usr/bin/env bash
# Run on AMS after deploy: dry-run only (hot prod safe).
set -euo pipefail
OPS="${AMS_OPS_DIR:-/opt/scripts}"
set -a
# shellcheck disable=SC1091
source /opt/remna-shop/.env
set +a
export PANEL_URL="${REMNA_BASE_URL:-http://127.0.0.1:3000}"
export PANEL_TOKEN="${REMNA_API_TOKEN}"
python3 "${OPS}/lv_node_failover_auto.py"
python3 "${OPS}/sync_injecthosts_connected.py"
python3 "${OPS}/lv_node_down_nl_failover.py" --status
echo "AMS_NODE_RESILIENCE_SMOKE_OK"
