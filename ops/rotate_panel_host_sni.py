#!/usr/bin/env python3
"""P2-RED-SNI-LIVE-01: rotate deprecated Reality SNI on panel hosts to www.yandex.ru."""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import site_urls

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / ".secrets" / "panel-token.txt"
BASE = site_urls.PANEL_URL

FORBIDDEN = frozenset(
    {
        "api.github.com",
        "www.bing.com",
        "www.microsoft.com",
        "www.apple.com",
        "github.com",
    }
)
TARGET_SNI = os.environ.get("REMNA_SERVER_SNI", "www.yandex.ru").strip() or "www.yandex.ru"


def _api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = BASE.rstrip("/") + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN_FILE.read_text(encoding='ascii').strip()}")
    if body is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", errors="replace") or "{}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--include-hidden", action="store_true")
    args = ap.parse_args()

    code, data = _api("GET", "/api/hosts")
    if code != 200:
        print(f"GET hosts HTTP {code}", file=sys.stderr)
        return 1

    hosts = data.get("response") or []
    todo = []
    for h in hosts:
        if h.get("isDisabled"):
            continue
        if h.get("isHidden") and not args.include_hidden:
            continue
        sni = (h.get("sni") or "").strip()
        if sni in FORBIDDEN:
            todo.append(h)

    if not todo:
        print("ROTATE_PANEL_SNI_OK (nothing to change)")
        return 0

    for h in todo:
        uid = h["uuid"]
        old = h.get("sni")
        remark = (h.get("remark") or "")[:40].encode("ascii", "replace").decode()
        print(f"  {uid[:8]} {remark!r}: {old} -> {TARGET_SNI}")
        if not args.apply:
            continue
        code, body = _api("PATCH", "/api/hosts", {"uuid": uid, "sni": TARGET_SNI})
        if code not in (200, 201, 204):
            print(f"PATCH {uid} HTTP {code}: {str(body)[:200]}", file=sys.stderr)
            return 1

    if not args.apply:
        print(f"\n# dry-run: {len(todo)} hosts; pass --apply to PATCH")
        return 0

    print(f"ROTATE_PANEL_SNI_OK ({len(todo)} hosts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
