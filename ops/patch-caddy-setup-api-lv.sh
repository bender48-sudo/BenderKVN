#!/bin/bash
# P3-FLOW-02: /setup API verify proxy + rate limit on /setup.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-setup-api-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
import sys
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
if "SETUP_API_BOOT_02" in c:
    print("OK: setup API marker already present")
    sys.exit(0)
marker = "k9x2m1.conntest.xyz:2053"
idx = c.find(marker)
if idx < 0:
    print("ERROR: k9x2m1 block not found", file=sys.stderr)
    sys.exit(1)
insert = """
    # SETUP_API_BOOT_02 — verify setup token (P3-FLOW-02)
    handle /setup/api/* {
        uri strip_prefix /setup/api
        reverse_proxy 127.0.0.1:8871 {
            header_up Host {host}
        }
    }

"""
needle = "    # USER_PORTAL_BOOT_01"
pos = c.find(needle, idx)
if pos < 0:
    print("ERROR: USER_PORTAL_BOOT_01 block not found", file=sys.stderr)
    sys.exit(1)
c = c[:pos] + insert + c[pos:]
with open(path, "w") as f:
    f.write(c)
print("patched Caddyfile")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active --quiet caddy
echo "PATCH_CADDY_SETUP_API_OK"
