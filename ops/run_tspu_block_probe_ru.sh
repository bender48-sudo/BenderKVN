#!/usr/bin/env bash
# P1-RED-TSPU-BLOCK-RU-01: run tspu_block_probe from RU relay (egress inside RU).
set -euo pipefail
# Prefer ru-monitor.env (bvpncheck@72.56.0.145); do not source balancer secrets here.
if [[ -f /etc/bvpn/ru-monitor.env ]]; then
  # shellcheck source=/dev/null
  set -a && source /etc/bvpn/ru-monitor.env && set +a
fi
HOST="${RU_RELAY_HOST:-${RELAY_HOST:-72.56.0.145}}"
PORT="${RU_RELAY_SSH_PORT:-${RELAY_SSH_PORT:-3344}}"
USER="${RU_RELAY_SSH_USER:-${RELAY_SSH_USER:-bvpncheck}}"
KEY="${RU_RELAY_SSH_KEY:-${RELAY_SSH_KEY:-/root/.ssh/id_ed25519}}"
REMOTE_DIR="${RU_PROBE_REMOTE_DIR:-/opt/scripts}"
if [[ ! -f "$KEY" ]]; then
  echo "TSPU_BLOCK_PROBE_RU_FAIL: missing SSH key $KEY" >&2
  exit 1
fi
echo "RU_PROBE_SSH ${USER}@${HOST}:${PORT} key=${KEY}"
exec ssh -i "$KEY" -p "$PORT" -o BatchMode=yes -o ConnectTimeout=25 "${USER}@${HOST}" \
  "cd ${REMOTE_DIR} && PYTHONPATH=${REMOTE_DIR} python3 tspu_block_probe.py --host k9x2m1.conntest.xyz"
