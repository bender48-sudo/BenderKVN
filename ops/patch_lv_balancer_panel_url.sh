#!/usr/bin/env bash
set -euo pipefail
TS="$(date +%Y%m%d-%H%M%S)"
cp -a /opt/scripts/balancer.sh "/opt/scripts/balancer.sh.bak-panelurl-${TS}"
sed -i 's|^PANEL_URL="http://localhost:3000"|PANEL_URL="${PANEL_URL:-http://localhost:3000}"|' /opt/scripts/balancer.sh
if ! grep -q '^PANEL_URL=https://' /etc/bvpn/balancer.env; then
  echo 'PANEL_URL=https://k9x2m1.conntest.xyz:2053' >> /etc/bvpn/balancer.env
fi
bash -n /opt/scripts/balancer.sh
echo "OK: patched balancer.sh + balancer.env"
