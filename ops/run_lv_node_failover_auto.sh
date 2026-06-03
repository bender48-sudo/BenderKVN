#!/usr/bin/env bash
# P2-OPS-NODE-FAILOVER-AUTO-01 — run on bvpn-lv (panel token from ru-monitor.env).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${RU_MONITOR_ENV:-/etc/bvpn/ru-monitor.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
export PANEL_TOKEN="${PANEL_TOKEN:-${REMNA_API_TOKEN:-}}"
exec python3 "${OPS}/lv_node_failover_auto.py" --apply "$@"
