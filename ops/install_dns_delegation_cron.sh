#!/usr/bin/env bash
# P4-DNS-04: weekly DNS delegation probe on bvpn-lv.
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${LV_OPS_DIR:-/opt/scripts}"
CRON_LINE="17 6 * * 1 root python3 ${TARGET}/dns_delegation_probe.py >> /var/log/bvpn-dns-delegation.log 2>&1"
MARK="# bvpn-dns-delegation-probe"

for f in dns_delegation_probe.py dns_critical_inventory.json site_urls.py load_env_file.py; do
  src="${OPS}/${f}"
  dst="${TARGET}/${f}"
  if [[ -f "$src" ]] && [[ "$(readlink -f "$src" 2>/dev/null || echo "$src")" != "$(readlink -f "$dst" 2>/dev/null || echo "$dst")" ]]; then
    install -m 644 "$src" "$dst"
  fi
done

CRON_FILE="/etc/cron.d/bvpn-dns-delegation"
if grep -qF "$MARK" "$CRON_FILE" 2>/dev/null; then
  echo "OK: dns delegation cron already installed"
else
  printf '%s\n%s\n' "$MARK" "$CRON_LINE" > "$CRON_FILE"
  chmod 644 "$CRON_FILE"
  echo "installed $CRON_FILE"
fi
echo "DNS_DELEGATION_CRON_OK"
