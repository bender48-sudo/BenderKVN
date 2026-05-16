"""Discover Remnawave panel endpoints that expose a node's SECRET_KEY/cert.

Queries /api/docs-json and prints every path containing 'node'."""
from __future__ import annotations

import json
import re
import ssl
import urllib.request
from pathlib import Path

import site_urls

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
URL = f"{site_urls.PANEL_URL}/api/docs-json"


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


req = urllib.request.Request(URL)
req.add_header("Authorization", f"Bearer {TOKEN}")
with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
    spec = json.loads(r.read().decode("utf-8"))

paths = spec.get("paths", {})
print(f"# total paths: {len(paths)}")
print("# node-related paths")
for p, methods in paths.items():
    if "node" in p.lower():
        for m, info in methods.items():
            summary = info.get("summary") or info.get("operationId") or ""
            print(f"  {m.upper():6s} {p:60s} {summary}")
print()
print("# keygen / cert / secret paths")
for p, methods in paths.items():
    if any(k in p.lower() for k in ("keygen", "cert", "secret")):
        for m, info in methods.items():
            summary = info.get("summary") or info.get("operationId") or ""
            print(f"  {m.upper():6s} {p:60s} {summary}")
