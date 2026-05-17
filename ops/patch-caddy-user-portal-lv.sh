#!/bin/bash
# P3-FLOW-01: serve /start and /portal from /var/www/bvpn-portal on k9x2m1.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-user-portal-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"
mkdir -p /var/www/bvpn-portal

python3 <<'PY'
import sys
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
if "USER_PORTAL_BOOT_01" in c:
    print("OK: user portal marker already present")
    sys.exit(0)
marker = "k9x2m1.conntest.xyz:2053"
idx = c.find(marker)
if idx < 0:
    print("ERROR: k9x2m1 block not found", file=sys.stderr)
    sys.exit(1)
insert = """
    # USER_PORTAL_BOOT_01 — bootstrap + Mini App static portal (P3-FLOW-01)
    handle_path /start/* {
        root * /var/www/bvpn-portal
        try_files {path} /index.html
        file_server
    }
    handle /start {
        redir /start/ 308
    }
    handle_path /portal/* {
        root * /var/www/bvpn-portal
        try_files {path} /index.html
        file_server
    }
    handle /portal {
        redir /portal/ 308
    }
    @setup_pages path /setup /setup/*
    handle @setup_pages {
        root * /var/www/bvpn-portal
        @not_api not path /setup/api/*
        handle @not_api {
            rewrite * /setup.html
            file_server
        }
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
echo "PATCH_CADDY_USER_PORTAL_OK"
