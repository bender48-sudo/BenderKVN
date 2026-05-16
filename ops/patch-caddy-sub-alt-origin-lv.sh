#!/bin/bash
# P2-RED-SUB-01: route /api/sub/* on k9x2m1 (panel host) to AMS subscription-page :3010.
# Run on bvpn-lv as root. Primary sub origin remains p4n7q.conntest.xyz:2053.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK=/etc/caddy/Caddyfile.bak-pre-sub-alt-$(date +%Y%m%d-%H%M%S)
cp -a "$CF" "$BK"

python3 <<'PY'
import sys

path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()

marker = "k9x2m1.conntest.xyz:2053"
if marker not in c:
    print("ERROR: k9x2m1 block not found", file=sys.stderr)
    sys.exit(1)

if "handle @sub_path_alt" in c or "SUB_ALT_ORIGIN_P2_RED_SUB_01" in c:
    print("OK: alt sub route already present")
    sys.exit(0)

insert = """    # SUB_ALT_ORIGIN_P2_RED_SUB_01 — second public name for /api/sub (same upstream as p4n7q)
    @sub_path_alt path /api/sub/*
    handle @sub_path_alt {
        rate_limit {
            zone sub_api_per_ip_alt {
                key {remote_host}
                events 120
                window 1m
            }
        }
        reverse_proxy http://168.100.11.140:3011 {
            header_up X-Forwarded-Proto "https"
            header_up X-Forwarded-For {remote_host}
        }
    }

    handle {
"""

old = """    reverse_proxy http://168.100.11.140:3000 {
        header_up Host k9x2m1.conntest.xyz
        header_up X-Forwarded-Proto "https"
        header_up X-Forwarded-For {remote_host}
    }
}
"""

new = insert + """        reverse_proxy http://168.100.11.140:3000 {
            header_up Host k9x2m1.conntest.xyz
            header_up X-Forwarded-Proto "https"
            header_up X-Forwarded-For {remote_host}
        }
    }
}
"""

if old not in c:
    print("ERROR: expected k9x2m1 reverse_proxy block not found", file=sys.stderr)
    sys.exit(1)

c = c.replace(old, new, 1)
with open(path, "w") as f:
    f.write(c)
print("OK: k9x2m1 /api/sub/* -> AMS:3010")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
PROBE="${SUB_MONITOR_PROBE_SUFFIX:-api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"
curl -fsSI -m 15 "https://k9x2m1.conntest.xyz:2053/${PROBE}" | head -3
echo "OK: alt origin smoke (backup $BK)"
