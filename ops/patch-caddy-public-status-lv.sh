#!/bin/bash
# P5-COM-01: serve /status HTML from /var/www/bvpn-status on k9x2m1.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-public-status-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"
mkdir -p /var/www/bvpn-status

python3 <<'PY'
import sys
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
if "PUBLIC_STATUS_PAGE_01" in c:
    print("OK: public status page marker already present")
    sys.exit(0)
marker = "k9x2m1.conntest.xyz:2053"
idx = c.find(marker)
if idx < 0:
    print("ERROR: k9x2m1 block not found", file=sys.stderr)
    sys.exit(1)
insert = """
    # PUBLIC_STATUS_PAGE_01 — user-facing incident status (P5-COM-01)
    handle /status {
        root * /var/www/bvpn-status
        rewrite * /index.html
        file_server
    }

"""
needle = "    respond @fingerprint 404\n\n"
pos = c.find(needle, idx)
if pos < 0:
    print("ERROR: fingerprint block not found in k9x2m1", file=sys.stderr)
    sys.exit(1)
pos += len(needle)
c = c[:pos] + insert + c[pos:]
with open(path, "w") as f:
    f.write(c)
print("patched Caddyfile")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active --quiet caddy
echo "PATCH_CADDY_PUBLIC_STATUS_OK"
