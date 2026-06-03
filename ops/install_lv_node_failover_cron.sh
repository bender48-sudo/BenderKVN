#!/usr/bin/env bash
# Install LV node failover auto cron on bvpn-lv (every 10 min).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${LV_OPS_DIR:-/opt/scripts}"
MARK="# bvpn-lv-node-failover-auto"
CRON_LINE="*/10 * * * * root ${TARGET}/run_lv_node_failover_auto.sh >> /var/log/bvpn-lv-node-failover.log 2>&1"

install -m 755 "${OPS}/run_lv_node_failover_auto.sh" "${TARGET}/run_lv_node_failover_auto.sh"
for f in lv_node_failover_auto.py lv_node_down_nl_failover.py lv_nl_failover_common.py verify_nl_failover_sub.py \
  sync_injecthosts_connected.py panel_client.py site_urls.py load_env_file.py subscription_fetch.py \
  balancer_selectors.py trim_injecthosts_no_xhttp.py subscription_config_notify.py verify_vpn_balancer_profile.py \
  probe_subscription.py diagnose_happ_import.py transport_mux_audit.py; do
  src="${OPS}/${f}"
  [[ -f "$src" ]] || continue
  dst="${TARGET}/${f}"
  if [[ "$(readlink -f "$src" 2>/dev/null || echo "$src")" != "$(readlink -f "$dst" 2>/dev/null || echo "$dst")" ]]; then
    install -m 644 "$src" "$dst"
  fi
done

CRON_FILE="/etc/cron.d/bvpn-lv-node-failover"
if grep -qF "$MARK" "$CRON_FILE" 2>/dev/null; then
  echo "OK: cron already installed ($CRON_FILE)"
else
  printf '%s\n%s\n' "$MARK" "$CRON_LINE" > "$CRON_FILE"
  chmod 644 "$CRON_FILE"
  echo "installed $CRON_FILE"
fi
echo "LV_NODE_FAILOVER_CRON_OK"
