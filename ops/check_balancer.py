"""Inspect routing/balancer strategy in the subscription template."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
snap = sorted((ROOT / ".secrets" / "snapshots").glob("panel-*.json"))[-1]
doc = json.loads(snap.read_text(encoding="utf-8"))["template"]["data"]["response"]["templateJson"]

routing = doc.get("routing") or {}
balancers = routing.get("balancers") or []
print(f"# balancers: {len(balancers)}")
for b in balancers:
    print(json.dumps(b, ensure_ascii=False, indent=2))

print("\n# routing rules referencing balancer:")
for r in routing.get("rules") or []:
    if "balancerTag" in r or "balancer" in r:
        print(json.dumps(r, ensure_ascii=False))
