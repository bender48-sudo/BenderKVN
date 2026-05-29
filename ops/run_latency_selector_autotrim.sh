#!/usr/bin/env bash
# VPN-AUD-310: run latency probe + autotrim on LV (ru-monitor host).
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
if [[ -z "$PANEL_TOKEN" ]]; then
  echo "LATENCY_AUTOTRIM_FAIL: PANEL_TOKEN/REMNA_API_TOKEN unset" >&2
  exit 1
fi
exec python3 "${OPS}/latency_selector_autotrim.py" --apply "$@"
