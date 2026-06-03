#!/usr/bin/env bash
# P1-PRO-SUB-DEAD-OUTBOUND-01 — sync injectHosts to connected nodes only.
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
exec python3 "${OPS}/sync_injecthosts_connected.py" --apply "$@"
