#!/bin/bash
# P6-RED-SUBHA-01: split-host — k9x2m1 (alt origin) -> AMS :3011, p4n7q stays on :3010.
# Run on bvpn-lv as root.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK=/etc/caddy/Caddyfile.bak-pre-subha-split-$(date +%Y%m%d-%H%M%S)
cp -a "$CF" "$BK"

python3 <<'PY'
import sys

path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()

if "SUBHA_SPLIT_HOST_K9X2M1_3011" in c:
    print("OK: split-host marker already present")
    sys.exit(0)

marker = "k9x2m1.conntest.xyz:2053"
if marker not in c:
    print("ERROR: k9x2m1 block not found", file=sys.stderr)
    sys.exit(1)

old = """        reverse_proxy http://168.100.11.140:3010 {
            header_up X-Forwarded-Proto "https"
            header_up X-Forwarded-For {remote_host}
        }
    }

    handle {
        reverse_proxy http://168.100.11.140:3000 {
            header_up Host k9x2m1.conntest.xyz"""

new = """        # SUBHA_SPLIT_HOST_K9X2M1_3011 — alt origin -> second sub-page instance
        reverse_proxy http://168.100.11.140:3011 {
            header_up X-Forwarded-Proto "https"
            header_up X-Forwarded-For {remote_host}
        }
    }

    handle {
        reverse_proxy http://168.100.11.140:3000 {
            header_up Host k9x2m1.conntest.xyz"""

# Only replace inside k9x2m1 block (first occurrence after marker)
idx = c.find(marker)
if idx < 0:
    sys.exit(1)
segment = c[idx:]
if old not in segment:
    print("ERROR: expected k9x2m1 sub reverse_proxy :3010 block not found", file=sys.stderr)
    sys.exit(1)
segment_new = segment.replace(old, new, 1)
c = c[:idx] + segment_new

with open(path, "w") as f:
    f.write(c)
print("OK: k9x2m1 /api/sub/* -> AMS:3011 (split-host)")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
PROBE="${SUB_MONITOR_PROBE_SUFFIX:-api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"
curl -fsSI -m 15 "https://k9x2m1.conntest.xyz:2053/${PROBE}" | head -3
curl -fsSI -m 15 "https://p4n7q.conntest.xyz:2053/${PROBE}" | head -3
echo "OK: split-host smoke (backup $BK)"
