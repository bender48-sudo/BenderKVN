#!/usr/bin/env bash
# Cron on AMS: drop dead-node injectHosts every 15 min.
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${AMS_OPS_DIR:-/opt/scripts}"
MARK="# bvpn-ams-sync-injecthosts-connected"
CRON_LINE="*/15 * * * * root ${TARGET}/run_sync_injecthosts_connected_ams.sh >> /var/log/bvpn-ams-sync-injecthosts.log 2>&1"

_run="${TARGET}/run_sync_injecthosts_connected_ams.sh"
[[ "$(readlink -f "${OPS}/run_sync_injecthosts_connected_ams.sh" 2>/dev/null || echo "${OPS}/run_sync_injecthosts_connected_ams.sh")" != "$(readlink -f "$_run" 2>/dev/null || echo "$_run")" ]] && install -m 755 "${OPS}/run_sync_injecthosts_connected_ams.sh" "$_run" || chmod 755 "$_run"
for f in sync_injecthosts_connected.py trim_injecthosts_no_xhttp.py panel_client.py site_urls.py load_env_file.py subscription_config_notify.py; do
  src="${OPS}/${f}"
  [[ -f "$src" ]] || continue
  install -m 644 "$src" "${TARGET}/${f}"
done

CRON_FILE="/etc/cron.d/bvpn-ams-sync-injecthosts"
if grep -qF "$MARK" "$CRON_FILE" 2>/dev/null; then
  echo "OK: cron already installed ($CRON_FILE)"
else
  printf '%s\n%s\n' "$MARK" "$CRON_LINE" >"$CRON_FILE"
  chmod 644 "$CRON_FILE"
  echo "installed $CRON_FILE"
fi
echo "AMS_SYNC_INJECTHOSTS_CRON_OK"
