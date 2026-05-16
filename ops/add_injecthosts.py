"""Append host UUIDs to subscription template's injectHosts.values via PATCH.

Mirrors ops/trim_injecthosts_no_ams.py — Remnawave expects a full template
object on PATCH /api/subscription-templates (not a UUID path).

Usage:
    python ops/add_injecthosts.py uuid1 uuid2 ... uuidN
"""
from __future__ import annotations

import copy
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import site_urls

TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID
BASE = site_urls.PANEL_URL
ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / ".secrets" / "panel-token.txt").read_text(encoding="ascii").strip()


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def api(method: str, url: str, body: str | None = None) -> tuple[int, Any]:
    data = body.encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
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
    new_uuids = sys.argv[1:]
    if not new_uuids:
        sys.exit(__doc__)

    code, data = api("GET", f"{BASE}/api/subscription-templates/{TEMPLATE_UUID}")
    if code != 200:
        sys.exit(f"GET template HTTP {code}: {data}")

    tpl = copy.deepcopy(data["response"])
    doc = tpl["templateJson"]
    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = list(sel.get("values") or [])
    print(f"before: {len(before)} UUIDs")

    seen = set(before)
    appended = []
    for u in new_uuids:
        if u in seen:
            print(f"skip duplicate: {u}")
            continue
        appended.append(u)
        seen.add(u)
    after = before + appended
    sel["values"] = after
    print(f"after:  {len(after)} UUIDs (added {len(appended)})")

    minimal = {
        "uuid": tpl.get("uuid") or TEMPLATE_UUID,
        "templateJson": doc,
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    backup = ROOT / ".secrets" / "snapshots" / f"template-before-{tpl.get('uuid')}.json"
    backup.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"backup: {backup}")

    code, resp = api("PATCH", f"{BASE}/api/subscription-templates", json.dumps(minimal, ensure_ascii=False))
    print(f"PATCH HTTP {code}")
    if code not in (200, 201):
        print(json.dumps(resp, ensure_ascii=False)[:800])
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
