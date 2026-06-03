#!/usr/bin/env bash
# Cron on AMS: LV down → NL template failover (every 10 min). Hot prod safe: skip if LV up.
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${AMS_OPS_DIR:-/opt/scripts}"
MARK="# bvpn-ams-lv-node-failover-auto"
CRON_LINE="*/10 * * * * root ${TARGET}/run_lv_node_failover_auto_ams.sh >> /var/log/bvpn-ams-lv-node-failover.log 2>&1"

_run="${TARGET}/run_lv_node_failover_auto_ams.sh"
[[ "$(readlink -f "${OPS}/run_lv_node_failover_auto_ams.sh" 2>/dev/null || echo "${OPS}/run_lv_node_failover_auto_ams.sh")" != "$(readlink -f "$_run" 2>/dev/null || echo "$_run")" ]] && install -m 755 "${OPS}/run_lv_node_failover_auto_ams.sh" "$_run" || chmod 755 "$_run"
for f in lv_node_failover_auto.py lv_node_down_nl_failover.py lv_nl_failover_common.py verify_nl_failover_sub.py \
  panel_client.py site_urls.py load_env_file.py subscription_fetch.py balancer_selectors.py \
  trim_injecthosts_no_xhttp.py subscription_config_notify.py verify_vpn_balancer_profile.py \
  probe_subscription.py diagnose_happ_import.py transport_mux_audit.py; do
  src="${OPS}/${f}"
  [[ -f "$src" ]] || continue
  install -m 644 "$src" "${TARGET}/${f}"
done

CRON_FILE="/etc/cron.d/bvpn-ams-lv-node-failover"
if grep -qF "$MARK" "$CRON_FILE" 2>/dev/null; then
  echo "OK: cron already installed ($CRON_FILE)"
else
  printf '%s\n%s\n' "$MARK" "$CRON_LINE" >"$CRON_FILE"
  chmod 644 "$CRON_FILE"
  echo "installed $CRON_FILE"
fi
echo "AMS_LV_NODE_FAILOVER_CRON_OK"
