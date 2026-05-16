"""Dump full user object + raw subscription response for the first active user."""
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
PANEL = site_urls.PANEL_URL
SUB = site_urls.SUB_PUBLIC_ORIGIN


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
        return r.read()


short = sys.argv[1] if len(sys.argv) > 1 else "eF6EH6wGc7J_4xUdMSv2knA6T"

users = json.loads(fetch(f"{PANEL}/api/users?limit=50&start=0", {"Authorization": f"Bearer {TOKEN}"}))
pick = None
for u in users.get("response", {}).get("users") or []:
    if (u.get("shortUuid") or u.get("subscriptionUuid")) == short:
        pick = u
        break

print("=== USER ===")
print(json.dumps(pick, ensure_ascii=False, indent=2))
print()

print("=== SUBSCRIPTION (Happ UA) ===")
raw = fetch(f"{SUB}/api/sub/{short}", {"User-Agent": "Happ/1.9.4 (iOS)"})
sub = json.loads(raw)
print(json.dumps(sub, ensure_ascii=False, indent=2)[:6000])
