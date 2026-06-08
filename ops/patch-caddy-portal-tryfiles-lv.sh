#!/bin/bash
# P1: serve directory index.html under /start/* and /portal/* (e.g. /start/help/errors/).
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-portal-tryfiles-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
import sys
from pathlib import Path

path = Path("/etc/caddy/Caddyfile")
text = path.read_text(encoding="utf-8")
old = "try_files {path} /index.html"
new = "try_files {path} {path}/index.html /index.html"
if "PORTAL_TRYFILES_INDEX_01" in text:
    print("OK: portal try_files marker already present")
    sys.exit(0)
if old not in text:
    print("ERROR: expected try_files line not found", file=sys.stderr)
    sys.exit(1)
count = text.count(old)
text = text.replace(old, new)
# Mark first /start/* portal block only (idempotent deploy marker).
needle = "handle_path /start/* {"
idx = text.find(needle)
if idx < 0:
    print("ERROR: handle_path /start/* not found", file=sys.stderr)
    sys.exit(1)
insert_at = text.find("\n", idx)
text = text[: insert_at + 1] + "        # PORTAL_TRYFILES_INDEX_01\n" + text[insert_at + 1 :]
path.write_text(text, encoding="utf-8")
print(f"patched try_files ({count} occurrence(s))")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active --quiet caddy
echo "PATCH_CADDY_PORTAL_TRYFILES_OK"
