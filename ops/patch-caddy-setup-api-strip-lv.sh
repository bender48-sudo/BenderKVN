#!/bin/bash
# Ensure /setup/api strips prefix before verify upstream.
set -euo pipefail
CF=/etc/caddy/Caddyfile
python3 <<'PY'
import re
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
block = """    handle /setup/api/* {
        uri strip_prefix /setup/api
        reverse_proxy 127.0.0.1:8871 {
            header_up Host {host}
        }
    }
"""
pat = re.compile(
    r"    # SETUP_API_BOOT_02.*?\n    handle /setup/api/\* \{.*?\n    \}\n",
    re.DOTALL,
)
if not pat.search(c):
    print("ERROR: SETUP_API block missing", file=__import__("sys").stderr)
    raise SystemExit(1)
c = pat.sub(block + "\n", c, count=1)
with open(path, "w") as f:
    f.write(c)
print("updated SETUP_API strip_prefix")
PY
caddy validate --config "$CF"
systemctl restart caddy
echo "PATCH_CADDY_SETUP_API_STRIP_OK"
