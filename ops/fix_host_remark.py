"""Update a single host's remark (and only remark) via PATCH /api/hosts.

Usage:
    python ops/fix_host_remark.py <host-uuid> "<new remark>" [--apply]

Without --apply, prints what would change (dry-run).
"""
from __future__ import annotations

import argparse
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


def _ctx() -> ssl.SSLContext:
    # TLS verification ON: panel uses Let's Encrypt cert; system CA is enough.
    return ssl.create_default_context()


def api(method: str, url: str, body=None) -> tuple[int, str]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if body is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=30) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("uuid")
    ap.add_argument("remark")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    code, body = api("GET", f"{BASE}/api/hosts/{args.uuid}")
    if code != 200:
        sys.exit(f"GET host {args.uuid} HTTP {code}: {body[:300]}")
    host = json.loads(body)["response"]
    old_remark = host.get("remark")
    print(f"# host  : {args.uuid}")
    print(f"# old   : {old_remark!r}")
    print(f"# new   : {args.remark!r}")
    if old_remark == args.remark:
        print("no change")
        return

    # Try minimal body first (uuid + remark). Mirror what works for templates/squads:
    # PATCH /api/hosts with body that includes uuid.
    payload = {"uuid": args.uuid, "remark": args.remark}

    if not args.apply:
        print("\n# dry-run; pass --apply to actually PATCH")
        print(f"# body: {json.dumps(payload, ensure_ascii=False)}")
        return

    code, body = api("PATCH", f"{BASE}/api/hosts", payload)
    print(f"PATCH /api/hosts HTTP {code}")
    print(body[:600])
    if code not in (200, 201, 204):
        sys.exit(1)

    # Verify
    code, body = api("GET", f"{BASE}/api/hosts/{args.uuid}")
    after = json.loads(body)["response"].get("remark")
    print(f"# after : {after!r}")
    if after != args.remark:
        sys.exit("verify mismatch")
    print("OK")


if __name__ == "__main__":
    main()
