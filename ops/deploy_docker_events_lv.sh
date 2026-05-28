#!/usr/bin/env bash
# Deploy docker_events_tg.py to LV and install cron (VPN-AUD-140).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_HOST="${REMOTE_HOST:-bvpn-lv}"
REMOTE_DIR="/opt/bvpn"
SCRIPT="docker_events_tg.py"
CRON_LINE='*/5 * * * * /usr/bin/python3 /opt/bvpn/docker_events_tg.py >> /var/log/bvpn-docker-events.log 2>&1'

echo "[deploy] copy ${SCRIPT} -> ${REMOTE_HOST}:${REMOTE_DIR}/"
scp -q "${ROOT}/ops/${SCRIPT}" "${REMOTE_HOST}:${REMOTE_DIR}/${SCRIPT}"
ssh -o BatchMode=yes "${REMOTE_HOST}" "chmod 755 ${REMOTE_DIR}/${SCRIPT}"
ssh -o BatchMode=yes "${REMOTE_HOST}" "python3 ${REMOTE_DIR}/${SCRIPT} --dry-run || true"
if ssh -o BatchMode=yes "${REMOTE_HOST}" "crontab -l 2>/dev/null | grep -F docker_events_tg.py"; then
  echo "[deploy] cron already present"
else
  ssh -o BatchMode=yes "${REMOTE_HOST}" "(crontab -l 2>/dev/null; echo '${CRON_LINE}') | crontab -"
  echo "[deploy] cron installed"
fi
echo "DEPLOY_DOCKER_EVENTS_LV_OK"
