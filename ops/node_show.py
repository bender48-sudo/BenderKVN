"""Show full node detail (address, port, status)."""
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

ctx = ssl.create_default_context()


def fetch(path: str) -> dict:
    req = urllib.request.Request(BASE + path)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


for n in fetch("/api/nodes")["response"]:
    print(f"{n['name']:18s} {n['address']:18s} port={n['port']:5d} connected={n['isConnected']}  lastMsg={n.get('lastStatusMessage')}")
