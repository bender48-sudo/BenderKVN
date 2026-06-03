#!/usr/bin/env bash
# Cron: drop injectHosts for disconnected panel nodes (every 15 min).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${LV_OPS_DIR:-/opt/scripts}"
MARK="# bvpn-sync-injecthosts-connected"
CRON_LINE="*/15 * * * * root ${TARGET}/run_sync_injecthosts_connected.sh >> /var/log/bvpn-sync-injecthosts.log 2>&1"

install -m 755 "${OPS}/run_sync_injecthosts_connected.sh" "${TARGET}/run_sync_injecthosts_connected.sh"
for f in sync_injecthosts_connected.py trim_injecthosts_no_xhttp.py panel_client.py site_urls.py load_env_file.py subscription_config_notify.py; do
  src="${OPS}/${f}"
  [[ -f "$src" ]] || continue
  install -m 644 "$src" "${TARGET}/${f}"
done

CRON_FILE="/etc/cron.d/bvpn-sync-injecthosts"
if grep -qF "$MARK" "$CRON_FILE" 2>/dev/null; then
  echo "OK: cron already installed ($CRON_FILE)"
else
  printf '%s\n%s\n' "$MARK" "$CRON_LINE" > "$CRON_FILE"
  chmod 644 "$CRON_FILE"
  echo "installed $CRON_FILE"
fi
echo "SYNC_INJECTHOSTS_CRON_OK"
