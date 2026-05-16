"""Show port mapping for relay hosts in the panel."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
snap = sorted((ROOT / ".secrets" / "snapshots").glob("panel-*.json"))[-1]
data = json.loads(snap.read_text(encoding="utf-8"))

print(f"# {snap.name}")
for h in data["hosts"]["data"]["response"]:
    if h.get("address") == "72.56.0.145":
        print(f"  {h['port']:>5} | {h.get('remark')!r}")
