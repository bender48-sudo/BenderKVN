#!/bin/bash
# Run on bvpn-lv as root: rate_limit on p4n7q subscription vhost (/api/sub/* per IP).
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK=/etc/caddy/Caddyfile.bak-pre-ratelimit-$(date +%Y%m%d-%H%M%S)
cp -a "$CF" "$BK"

python3 <<'PY'
import sys

path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()

if "zone sub_api_per_ip" in c:
    print("OK: already has rate_limit sub_api_per_ip")
    sys.exit(0)

block = """    rate_limit {
        zone sub_api_per_ip {
            match path /api/sub/*
            key {remote_host}
            events 120
            window 1m
        }
    }

"""

anchors = [
    ("        -Caddy-Server\n    }\n\n    @blocked {", "    @blocked {"),
    (
        "        -Caddy-Server\n    }\n\n    @blocked not path /api/sub/*",
        "    @blocked not path /api/sub/*",
    ),
]
for anchor, tail in anchors:
    if anchor in c:
        repl = "        -Caddy-Server\n    }\n\n" + block + tail
        c = c.replace(anchor, repl, 1)
        with open(path, "w") as f:
            f.write(c)
        print("OK: rate_limit block added")
        sys.exit(0)

print("ERROR: anchor after security headers not found", file=sys.stderr)
sys.exit(1)
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
echo "OK: caddy active (backup $BK)"
