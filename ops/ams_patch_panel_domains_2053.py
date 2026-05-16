#!/usr/bin/env python3
"""Set FRONT_END_DOMAIN and PANEL_DOMAIN to host:2053 for Remnawave behind LV Caddy on :2053."""
from pathlib import Path

p = Path("/opt/remnawave/.env")
t = p.read_text(encoding="utf-8")
repl = (
    ("FRONT_END_DOMAIN=k9x2m1.conntest.xyz", "FRONT_END_DOMAIN=k9x2m1.conntest.xyz:2053"),
    ("PANEL_DOMAIN=k9x2m1.conntest.xyz", "PANEL_DOMAIN=k9x2m1.conntest.xyz:2053"),
)
for a, b in repl:
    if b in t:
        continue
    if a not in t:
        raise SystemExit(f"missing {a!r}")
    t = t.replace(a, b, 1)
p.write_text(t, encoding="utf-8")
print("OK: FRONT_END_DOMAIN / PANEL_DOMAIN include :2053")
