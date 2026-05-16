#!/bin/bash
# Install status mirror builder + cron on bvpn-lv.
set -euo pipefail
SCRIPT_SRC=${1:-/opt/scripts/build_status_mirror.py}
install -d -m 0755 /opt/scripts /var/www/bvpn-status
if [[ -f "$SCRIPT_SRC" ]] && [[ "$(readlink -f "$SCRIPT_SRC")" != "$(readlink -f /opt/scripts/build_status_mirror.py)" ]]; then
  install -m 0755 "$SCRIPT_SRC" /opt/scripts/build_status_mirror.py
fi
MARKER="bvpn-status-mirror"
CRON_LINE="*/2 * * * * . /etc/bvpn/balancer.env 2>/dev/null; PYTHONPATH=/opt/scripts /usr/bin/python3 /opt/scripts/build_status_mirror.py -o /var/www/bvpn-status/status.json >> /var/log/bvpn-status-mirror.log 2>&1"
( crontab -l 2>/dev/null | grep -vF "$MARKER"; echo "$CRON_LINE # $MARKER" ) | crontab -
/usr/bin/python3 /opt/scripts/build_status_mirror.py -o /var/www/bvpn-status/status.json
echo "INSTALL_STATUS_MIRROR_LV_OK"
