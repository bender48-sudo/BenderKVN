#!/usr/bin/env bash
# P1-RED-TSPU-BLOCK-RU-01: hourly TSPU probe from RU relay (install on LV ops host).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN="${OPS}/run_tspu_block_probe_ru.sh"
chmod +x "${RUN}" "${OPS}/tspu_block_probe.py" 2>/dev/null || true
CRON_LINE="17 * * * * ${RUN} >> /var/log/bvpn-tspu-ru-probe.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'run_tspu_block_probe_ru.sh' || true
  echo "$CRON_LINE"
) | crontab -
echo "TSPU_RU_PROBE_CRON_INSTALLED"
