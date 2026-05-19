#!/usr/bin/env bash
# Q091/Q088: sunset :2053 → :8443 redirect; remove public :2054 (safe block replace).
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-phase6-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
import re
from pathlib import Path

cf = Path("/etc/caddy/Caddyfile")
text = cf.read_text(encoding="utf-8")

text = re.sub(r"\n:2054 \{[^}]*\}\n", "\n", text, count=1, flags=re.S)

REDIRECT_2053 = {
    "p4n7q.conntest.xyz:2053": "https://p4n7q.conntest.xyz:8443{uri}",
    "k9x2m1.conntest.xyz:2053": "https://k9x2m1.conntest.xyz:8443{uri}",
}
for host, target in REDIRECT_2053.items():
    marker = f"{host} {{"
    if marker not in text:
        continue
    i = text.find(marker)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                repl = f"{host} {{\n    redir {target} permanent\n}}\n"
                text = text[:i] + repl + text[j + 1 :]
                break

cf.write_text(text, encoding="utf-8")
print("PATCH_CADDY_PHASE6_OK")
PY

caddy validate --config "$CF"
systemctl reload caddy
echo "CADDY_RELOAD_OK"
