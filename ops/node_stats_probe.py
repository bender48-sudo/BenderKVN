"""Dump per-node stats fields from /api/nodes — used to design the load monitor."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

from panel_client import PanelClient  # noqa: E402

c = PanelClient()
data = c.get_or_raise("/api/nodes")

nodes = data["response"]
if not isinstance(nodes, list):
    nodes = nodes.get("nodes", nodes.get("items", []))

for n in nodes:
    print(json.dumps({
        "name": n.get("name"),
        "address": n.get("address"),
        "isConnected": n.get("isConnected"),
        "usersOnline": n.get("usersOnline"),
        "trafficUsedBytes": n.get("trafficUsedBytes"),
        "xrayUptime": n.get("xrayUptime"),
        "lastStatusChange": n.get("lastStatusChange"),
        "lastStatusMessage": n.get("lastStatusMessage"),
    }, ensure_ascii=False))
print()
print("# full first-node keys:")
if nodes:
    print(list(nodes[0].keys()))
