#!/usr/bin/env bash
# VPN-AUD-101: one-shot gate — reliability + speed + simplicity checks.
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${OPS}/../ops/verify_vpn_balancer_profile.py" ]]; then
  ROOT="$(cd "${OPS}/.." && pwd)"
else
  ROOT="${OPS}"
fi
ENV_FILE="${RU_MONITOR_ENV:-/etc/bvpn/ru-monitor.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
export PANEL_TOKEN="${PANEL_TOKEN:-${REMNA_API_TOKEN:-}}"
cd "${ROOT}"
exec python3 "${OPS}/vpn_verify_gate.py" "$@"
