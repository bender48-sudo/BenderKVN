#!/usr/bin/env bash
# Install VPN-AUD-310 cron on bvpn-lv (every 15 min, apply only on selector change).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${LV_OPS_DIR:-/opt/scripts}"
CRON_LINE="*/15 * * * * root ${TARGET}/run_latency_selector_autotrim.sh >> /var/log/bvpn-latency-autotrim.log 2>&1"

_run_src="${OPS}/run_latency_selector_autotrim.sh"
_run_dst="${TARGET}/run_latency_selector_autotrim.sh"
if [[ "$(readlink -f "$_run_src" 2>/dev/null || echo "$_run_src")" != "$(readlink -f "$_run_dst" 2>/dev/null || echo "$_run_dst")" ]]; then
  install -m 755 "$_run_src" "$_run_dst"
else
  chmod 755 "$_run_dst"
fi
for f in relay_latency_probe.py nl_reachability_probe_ru.py latency_selector_autotrim.py patch_add_nl_intl_gated.py balancer_selectors.py panel_client.py site_urls.py verify_vpn_balancer_profile.py subscription_fetch.py dns_split_config.py subscription_config_notify.py vpn_verify_gate.py; do
  src="${OPS}/${f}"
  dst="${TARGET}/${f}"
  if [[ "$(readlink -f "$src" 2>/dev/null || echo "$src")" != "$(readlink -f "$dst" 2>/dev/null || echo "$dst")" ]]; then
    install -m 644 "$src" "$dst"
  fi
done

MARK="# bvpn-latency-autotrim"
CRON_FILE="/etc/cron.d/bvpn-latency-autotrim"
if grep -qF "$MARK" "$CRON_FILE" 2>/dev/null; then
  echo "OK: cron already installed ($CRON_FILE)"
else
  printf '%s\n%s\n' "$MARK" "$CRON_LINE" > "$CRON_FILE"
  chmod 644 "$CRON_FILE"
  echo "installed $CRON_FILE"
fi
echo "LATENCY_AUTOTRIM_CRON_OK"
