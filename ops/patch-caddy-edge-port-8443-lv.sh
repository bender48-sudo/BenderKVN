#!/bin/bash
# P2-RED-EDGE-PORT-01: append p4n7q/k9x2m1 :8443 blocks from repo Caddyfile-latvia-full.txt
set -euo pipefail
CF=/etc/caddy/Caddyfile
REPO_CF="${REPO_CF:-/opt/bvpn-repo/Caddyfile-latvia-full.txt}"
BK="/etc/caddy/Caddyfile.bak-pre-edge-8443-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

export REPO_CF
python3 <<'PY'
import os
import sys

live = open("/etc/caddy/Caddyfile", encoding="utf-8").read()
ref_path = os.environ.get("REPO_CF", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
if not ref_path:
    print("ERROR: REPO_CF not set", file=sys.stderr)
    sys.exit(1)
ref = open(ref_path, encoding="utf-8").read()
for marker in ("p4n7q.conntest.xyz:8443", "k9x2m1.conntest.xyz:8443"):
    if marker in live:
        print(f"OK: {marker} already in live Caddyfile")
        sys.exit(0)
idx = ref.find("# P2-RED-EDGE-PORT-01")
if idx < 0:
    idx = ref.find("p4n7q.conntest.xyz:8443")
if idx < 0:
    print("ERROR: edge 8443 section not in reference Caddyfile", file=sys.stderr)
    sys.exit(1)
chunk = ref[idx:]
with open("/etc/caddy/Caddyfile", "a", encoding="utf-8") as f:
    f.write("\n\n")
    f.write(chunk)
print("OK: appended :8443 blocks")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active --quiet caddy
echo "PATCH_CADDY_EDGE_8443_OK"
