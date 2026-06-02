#!/bin/bash
# VPN-AUD-152/153: p4n7q sub-page — dual upstream :3010/:3011 + active health + cache 8m.
# Run on bvpn-lv as root after lv-install-caddy-edge-plugins.sh.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK=/etc/caddy/Caddyfile.bak-pre-sub-ha-cache-$(date +%Y%m%d-%H%M%S)
PROBE="${SUB_MONITOR_PROBE_SUFFIX:-api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"
PROBE="${PROBE#/}"

cp -a "$CF" "$BK"

python3 <<PY
import sys

path = "/etc/caddy/Caddyfile"
probe = "${PROBE}"
with open(path) as f:
    c = f.read()

marker = "VPN_AUD_152_SUB_HA_CACHE"
if marker in c:
    print("OK: HA+cache marker already present")
    sys.exit(0)

global_block = """{
    order cache before reverse_proxy
}

"""
if not c.lstrip().startswith("{"):
    c = global_block + c

old = """    respond @blocked 404

    reverse_proxy http://168.100.11.140:3010 {
        header_up X-Forwarded-Proto "https"
        header_up X-Forwarded-For {remote_host}
    }
}

k9x2m1.conntest.xyz:8443 {"""

if old not in c:
    print("ERROR: expected p4n7q reverse_proxy block not found", file=sys.stderr)
    sys.exit(1)

upstream = f"""    respond @blocked 404

    @sub_api path /api/sub/*
    handle @sub_api {{
        # {marker} — cache GET sub JSON; dual AMS backends with health failover
        cache {{
            ttl 8m
        }}
        reverse_proxy http://168.100.11.140:3010 http://168.100.11.140:3011 {{
            lb_policy first
            health_uri /{probe}
            health_interval 15s
            health_timeout 10s
            health_status 2xx
            health_headers {{
                X-Forwarded-Proto https
                X-Forwarded-For 127.0.0.1
            }}
            header_up X-Forwarded-Proto "https"
            header_up X-Forwarded-For {{remote_host}}
        }}
    }}

    handle {{
        reverse_proxy http://168.100.11.140:3010 http://168.100.11.140:3011 {{
            lb_policy first
            health_uri /{probe}
            health_interval 15s
            health_timeout 10s
            health_status 2xx
            health_headers {{
                X-Forwarded-Proto https
                X-Forwarded-For 127.0.0.1
            }}
            header_up X-Forwarded-Proto "https"
            header_up X-Forwarded-For {{remote_host}}
        }}
    }}
}}

k9x2m1.conntest.xyz:8443 {{"""

c = c.replace(old, upstream, 1)
with open(path, "w") as f:
    f.write(c)
print("OK: p4n7q /api/sub/* -> HA :3010+:3011 + cache 8m")
PY

if ! caddy list-modules 2>/dev/null | grep -q 'http.handlers.cache'; then
  echo "ERROR: Caddy missing cache handler — run ops/lv-install-caddy-edge-plugins.sh first" >&2
  cp -a "$BK" "$CF"
  exit 1
fi

mkdir -p /var/cache/caddy
caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy

curl -fsSI -m 20 "https://p4n7q.conntest.xyz:8443/${PROBE}" | head -3
echo "OK: sub HA+cache patch (backup $BK)"
