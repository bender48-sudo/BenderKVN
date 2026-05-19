#!/bin/bash
# P1-RED-CADDY-K9-BLOCKED-01: add @blocked_k9 on k9x2m1:8443 (panel paths -> 404).
set -euo pipefail

CADDYFILE="${1:-/etc/caddy/Caddyfile}"
MARKER='@blocked_k9'

if grep -q "$MARKER" "$CADDYFILE" 2>/dev/null; then
  echo "OK: $MARKER already present"
  exit 0
fi

python3 - "$CADDYFILE" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
needle = """    handle {
        reverse_proxy http://168.100.11.140:3000 {
            header_up Host k9x2m1.conntest.xyz"""
block = """    @blocked_k9 {
        not path /api/sub/*
        not path /api/ops/status.json
        not path /status
        not path /status/*
        not path /start
        not path /start/*
        not path /portal
        not path /portal/*
        not path /setup
        not path /setup/*
    }
    respond @blocked_k9 404

    handle {
        reverse_proxy http://168.100.11.140:3000 {
            header_up Host k9x2m1.conntest.xyz"""
if needle not in text:
    print("ERROR: k9x2m1 catch-all block not found", file=sys.stderr)
    sys.exit(1)
open(path + ".bak-pre-k9-blocked", "w", encoding="utf-8").write(text)
open(path, "w", encoding="utf-8").write(text.replace(needle, block, 1))
print("OK: inserted @blocked_k9")
PY

caddy validate --config "$CADDYFILE"
systemctl restart caddy
echo "CADDY_K9_BLOCKED_OK"
