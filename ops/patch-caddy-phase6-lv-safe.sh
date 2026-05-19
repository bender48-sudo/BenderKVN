#!/usr/bin/env bash
# Phase 6: :2053 → 301→8443; remove :2054 (brace-safe). Validate then restart Caddy.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-phase6-safe-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
from pathlib import Path


def replace_block(text: str, marker: str, replacement: str) -> str:
    i = text.find(marker)
    if i < 0:
        return text
    depth = 0
    started = False
    for j in range(i, len(text)):
        c = text[j]
        if c == "{":
            depth += 1
            started = True
        elif c == "}":
            depth -= 1
            if started and depth == 0:
                return text[:i] + replacement + text[j + 1 :]
    raise SystemExit(f"unbalanced braces for {marker!r}")


cf = Path("/etc/caddy/Caddyfile")
text = cf.read_text(encoding="utf-8")

text = replace_block(
    text,
    ":2054 {",
    "\n# P1-RED-NET-2054-01: panel only via k9x2m1:8443 (removed public :2054)\n",
)
text = replace_block(
    text,
    "p4n7q.conntest.xyz:2053 {",
    "p4n7q.conntest.xyz:2053 {\n    redir https://p4n7q.conntest.xyz:8443{uri} permanent\n}\n",
)
text = replace_block(
    text,
    "k9x2m1.conntest.xyz:2053 {",
    "k9x2m1.conntest.xyz:2053 {\n    redir https://k9x2m1.conntest.xyz:8443{uri} permanent\n}\n",
)
text = text.replace(
    "redir https://k9x2m1.conntest.xyz:2053{uri} permanent",
    "redir https://k9x2m1.conntest.xyz:8443{uri} permanent",
)

cf.write_text(text, encoding="utf-8")
print("PATCH_CADDY_PHASE6_SAFE_OK")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
echo "CADDY_RESTART_OK"
