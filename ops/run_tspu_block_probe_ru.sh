#!/usr/bin/env bash
# P1-RED-TSPU-BLOCK-RU-01: RU egress edge probe via relay check.py (bvpncheck forced command).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${OPS}/tspu_block_probe_ru.py" "$@"
