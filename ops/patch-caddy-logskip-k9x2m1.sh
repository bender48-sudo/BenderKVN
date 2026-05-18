#!/bin/bash
# P1-RED-LOG-02: log_skip /api/sub/* on k9x2m1 block (bvpn-lv).
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-logskip-k9-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
import sys
path = "/etc/caddy/Caddyfile"
with open(path) as f:
    c = f.read()
marker = "k9x2m1.conntest.xyz:2053"
idx = c.find(marker)
if idx < 0:
    print("ERROR: k9x2m1 block not found", file=sys.stderr)
    sys.exit(1)
block_end = c.find("\n\n", idx + len(marker))
snippet = c[idx:block_end if block_end > 0 else idx + 4000]
if "log_skip @sub_path_k9" in snippet or "log_skip @sub_path" in snippet:
    print("OK: k9x2m1 log_skip already present")
    sys.exit(0)
insert = """    @sub_path_k9 path /api/sub/*
    log_skip @sub_path_k9

"""
needle = "    @fingerprint path"
pos = c.find(needle, idx)
if pos < 0:
    print("ERROR: @fingerprint not found in k9 block", file=sys.stderr)
    sys.exit(1)
c = c[:pos] + insert + c[pos:]
with open(path, "w") as f:
    f.write(c)
print("OK: patched k9x2m1 log_skip")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active --quiet caddy
echo "SUB_LOG_SKIP_K9_OK"
