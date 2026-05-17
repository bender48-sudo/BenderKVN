#!/bin/bash
# P3-FLOW-02: fix /setup and /setup/?t= routing (serve setup.html, not panel).
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-setup-pages-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
import re
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
new_block = """
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
pat = re.compile(
    r"    handle_path /setup/\* \{.*?    \}\n    handle /setup \{\n        redir /setup/ 308\n    \}\n",
    re.DOTALL,
)
if pat.search(c):
    c = pat.sub(new_block + "\n", c, count=1)
    print("replaced legacy /setup handlers")
elif "@setup_pages path /setup" in c:
    print("OK: @setup_pages already present")
else:
    print("ERROR: legacy /setup block not found", file=sys.stderr)
    raise SystemExit(1)
with open(path, "w") as f:
    f.write(c)
PY

caddy validate --config "$CF"
systemctl restart caddy
echo "PATCH_CADDY_SETUP_PAGES_OK"
