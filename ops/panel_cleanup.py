"""Delete a Remnawave node + its profile (used to roll back a failed deploy).

Usage:
    python ops/panel_cleanup.py <node-uuid> [<profile-uuid>]
"""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import site_urls

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
PANEL_URL = site_urls.PANEL_URL


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def api(method: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(PANEL_URL.rstrip("/") + path, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body or "{}")
        except json.JSONDecodeError:
            return e.code, {"raw": body}


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    node_uuid = sys.argv[1]
    profile_uuid = sys.argv[2] if len(sys.argv) > 2 else None

    code, data = api("DELETE", f"/api/nodes/{node_uuid}")
    print(f"DELETE node {node_uuid}: HTTP {code} -> {json.dumps(data)[:200]}")

    if profile_uuid:
        code, data = api("DELETE", f"/api/config-profiles/{profile_uuid}")
        print(f"DELETE profile {profile_uuid}: HTTP {code} -> {json.dumps(data)[:200]}")


if __name__ == "__main__":
    main()
