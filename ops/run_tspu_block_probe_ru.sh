#!/usr/bin/env bash
# P1-RED-TSPU-BLOCK-RU-01: run tspu_block_probe from RU relay (egress inside RU).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
[[ -f /etc/bvpn/balancer.env ]] && set -a && source /etc/bvpn/balancer.env && set +a
[[ -f "$ROOT/ops/site.env" ]] && set -a && source "$ROOT/ops/site.env" && set +a
HOST="${RU_RELAY_HOST:-72.56.0.145}"
PORT="${RU_RELAY_SSH_PORT:-3344}"
KEY="${RU_RELAY_SSH_KEY:-$HOME/.ssh/bvpn_ru_ed25519}"
REMOTE_DIR="${RU_PROBE_REMOTE_DIR:-/opt/scripts}"
exec ssh -i "$KEY" -p "$PORT" -o BatchMode=yes -o ConnectTimeout=25 "root@${HOST}" \
  "cd ${REMOTE_DIR} && PYTHONPATH=${REMOTE_DIR} python3 tspu_block_probe.py --host k9x2m1.conntest.xyz"
