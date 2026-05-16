"""Dump per-node stats fields from /api/nodes — used to design the load monitor."""
from __future__ import annotations

import io
import json
import ssl
import sys
import urllib.request
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
BASE = site_urls.PANEL_URL
req.add_header("Authorization", f"Bearer {TOKEN}")
with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
    data = json.loads(r.read().decode("utf-8"))

for n in data["response"]:
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
print(list(data["response"][0].keys()))
