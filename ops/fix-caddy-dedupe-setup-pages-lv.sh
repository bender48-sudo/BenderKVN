#!/usr/bin/env bash
# Remove duplicate @setup_pages (+ handle block) inside the same Caddy site block.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-dedupe-setup-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
import re
from pathlib import Path

SETUP_BLOCK = re.compile(
    r"\n    @setup_pages path /setup /setup/\*\n"
    r"    handle @setup_pages \{.*?\n    \}\n",
    re.DOTALL,
)

path = Path("/etc/caddy/Caddyfile")
text = path.read_text(encoding="utf-8")

site_start = re.compile(r"(?m)^(?:[\w.-]+:\d+|:\d+) \{")

parts: list[str] = []
starts = [m.start() for m in site_start.finditer(text)]
if not starts:
    raise SystemExit("no site blocks found")
starts.append(len(text))

removed = 0
for i in range(len(starts) - 1):
    block = text[starts[i] : starts[i + 1]]
    matches = list(SETUP_BLOCK.finditer(block))
    if len(matches) <= 1:
        parts.append(block)
        continue
    # keep first, drop rest
    new_block = block
    for m in reversed(matches[1:]):
        new_block = new_block[: m.start()] + "\n" + new_block[m.end() :]
        removed += 1
    parts.append(new_block)

path.write_text("".join(parts), encoding="utf-8")
print(f"DEDUPE_SETUP_PAGES_OK removed={removed}")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
echo "CADDY_RESTART_OK"
