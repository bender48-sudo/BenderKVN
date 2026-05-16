#!/usr/bin/env python3
"""Set FRONT_END_DOMAIN to explicit panel URL (https + port)."""
from pathlib import Path
import re

p = Path("/opt/remnawave/.env")
t = p.read_text(encoding="utf-8")
new_line = "FRONT_END_DOMAIN=https://k9x2m1.conntest.xyz:2053"
if not re.search(r"^FRONT_END_DOMAIN=", t, flags=re.M):
    raise SystemExit("FRONT_END_DOMAIN missing")
t = re.sub(r"^FRONT_END_DOMAIN=.*$", new_line, t, flags=re.M)
p.write_text(t, encoding="utf-8")
print("OK:", new_line)
