#!/bin/bash
# Run on bvpn-lv as root: add log_skip for /api/sub/* without restoring from older backup.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK=/etc/caddy/Caddyfile.bak-pre-logskip-$(date +%Y%m%d-%H%M%S)
cp -a "$CF" "$BK"
python3 <<'PY'
import sys
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
old = """    log {
        output file /var/log/caddy/sub-access.log
        format json
    }"""
new = """    @sub_path path /api/sub/*
    log_skip @sub_path

    log {
        output file /var/log/caddy/sub-access.log {
            roll_size 10mb
            roll_keep 3
        }
        format json
    }"""
if "log_skip @sub_path" in c:
    print("OK: already has log_skip")
    sys.exit(0)
if old not in c:
    print("ERROR: expected log block not found", file=sys.stderr)
    sys.exit(1)
with open(path, "w") as f:
    f.write(c.replace(old, new, 1))
print("OK: patched")
PY
caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
