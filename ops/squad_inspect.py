"""Inspect internal squads and their inbounds (and check NL inbound membership)."""
from __future__ import annotations

import io
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()
PANEL = site_urls.PANEL_URL


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def api(method: str, path: str, body=None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(PANEL.rstrip("/") + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if body is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(txt or "{}")
        except json.JSONDecodeError:
            return e.code, {"raw": txt}


def main() -> None:
    code, data = api("GET", "/api/internal-squads")
    if code != 200:
        sys.exit(f"squads HTTP {code}: {data}")
    payload = data.get("response")
    squads = payload.get("internalSquads") if isinstance(payload, dict) and "internalSquads" in payload else payload
    if not isinstance(squads, list):
        sys.exit(f"unexpected payload: {str(payload)[:200]}")
    for sq in squads:
        sq_uuid = sq.get("uuid")
        name = sq.get("name")
        info = sq.get("info", {}) or {}
        inbounds = sq.get("inbounds") or info.get("inbounds") or []
        ids = []
        tags = []
        for ib in inbounds:
            if isinstance(ib, dict):
                ids.append(ib.get("uuid"))
                tags.append(ib.get("tag"))
            else:
                ids.append(ib)
        print(f"squad: {name} uuid={sq_uuid} inbounds={len(ids)} tags={tags}")


if __name__ == "__main__":
    main()
