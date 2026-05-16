#!/bin/bash
# P2-RED-BOOT-01: serve /api/ops/status.json from /var/www/bvpn-status on k9x2m1.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-status-mirror-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"
mkdir -p /var/www/bvpn-status

python3 <<'PY'
import sys
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
if "STATUS_MIRROR_BOOT_01" in c:
    print("OK: status mirror marker already present")
    sys.exit(0)
marker = "k9x2m1.conntest.xyz:2053"
idx = c.find(marker)
if idx < 0:
    print("ERROR: k9x2m1 block not found", file=sys.stderr)
    sys.exit(1)
insert = """
    # STATUS_MIRROR_BOOT_01 — HTTPS JSON ops status (no TG required)
    handle /api/ops/status.json {
        root * /var/www/bvpn-status
        rewrite * /status.json
        file_server
    }

"""
# After fingerprint respond block inside k9x2m1
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
echo "PATCH_CADDY_STATUS_MIRROR_OK"
