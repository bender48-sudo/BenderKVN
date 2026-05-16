"""Add NL inbound UUIDs to the 'Vless reality' internal squad.

Strategy:
1. GET the squad — collect existing inbound UUIDs (4 currently).
2. Compose target list = existing + NL Reality + NL XHTTP (6 total).
3. Try PATCH/POST/PUT against a few candidate routes with the FULL list
   in body — so even if a "replace inbounds" endpoint is hit we get the
   correct end state.
4. On success, verify GET shows 6 inbounds.

Usage:
    python ops/squad_add_nl.py --apply
"""
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
BASE = site_urls.PANEL_URL
NL_REALITY = "eeeb131b-ce71-4d06-9f15-5c5fbbb858fb"
NL_XHTTP = "128a0d98-488e-4f3d-bcf7-cfb358a83db3"


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def api(method: str, url: str, body=None) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if body is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def get_squad_inbounds() -> list[str]:
    code, body = api("GET", f"{BASE}/api/internal-squads/{SQUAD}")
    if code != 200:
        sys.exit(f"GET squad HTTP {code}: {body[:300]}")
    data = json.loads(body)["response"]
    ids = [ib["uuid"] for ib in (data.get("inbounds") or [])]
    print(f"current inbounds ({len(ids)}): {ids}")
    return ids


def try_update(target: list[str]) -> None:
    bodies = [
        {"uuid": SQUAD, "inbounds": target},
        {"inbounds": target},
        {"uuid": SQUAD, "activeInbounds": target},
    ]
    routes = [
        ("PATCH", f"{BASE}/api/internal-squads/{SQUAD}"),
        ("PATCH", f"{BASE}/api/internal-squads"),
        ("PUT", f"{BASE}/api/internal-squads/{SQUAD}"),
        ("POST", f"{BASE}/api/internal-squads/{SQUAD}/inbounds"),
    ]
    for method, url in routes:
        for body in bodies:
            code, resp = api(method, url, body)
            keys = ",".join(list(body.keys()))
            short_resp = resp.replace("\n", " ")[:150]
            print(f"{code} | {method:5s} {url[len(BASE):]} | body_keys={keys} | {short_resp}")
            if code in (200, 201, 204):
                print("  -> APPLIED, will verify")
                return


def main() -> None:
    existing = get_squad_inbounds()
    if NL_REALITY in existing and NL_XHTTP in existing:
        print("NL inbounds already in squad — nothing to do")
        return
    target = list(dict.fromkeys(existing + [NL_REALITY, NL_XHTTP]))
    print(f"target ({len(target)}): {target}")

    apply = "--apply" in sys.argv[1:]
    if not apply:
        print("# dry mode: pass --apply to actually try update")
        return

    try_update(target)

    # Verify
    after = get_squad_inbounds()
    if NL_REALITY in after and NL_XHTTP in after and len(after) >= len(existing):
        print(f"VERIFY OK: squad now has {len(after)} inbounds")
    else:
        print(f"VERIFY FAIL: squad inbounds={after}")
        sys.exit(1)


if __name__ == "__main__":
    main()
