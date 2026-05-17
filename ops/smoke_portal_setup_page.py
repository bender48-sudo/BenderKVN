#!/usr/bin/env python3
"""P3-FLOW-02: setup page with signed token returns 200 without VPN."""
from __future__ import annotations

import json
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402

_SECRET_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]{20,}|REMNA_API_TOKEN|BOT_TOKEN",
    re.I,
)


def _get(url: str, timeout: float = 12.0) -> tuple[int, str]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _sign_token_on_lv(short_id: str) -> str:
    cmd = (
        f"set -a; . /etc/bvpn/portal-setup.env; "
        f"PYTHONPATH=/opt/scripts /usr/bin/python3 /opt/scripts/portal_setup_token.py "
        f"sign --short-id {short_id}"
    )
    out = subprocess.check_output(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            str(Path.home() / ".ssh" / "bvpn_lv_ed25519"),
            "root@bvpn-lv",
            cmd,
        ],
        text=True,
        timeout=40,
    )
    return out.strip().splitlines()[-1]


def main() -> int:
    short_id = site_urls.probe_short_id()
    try:
        token = _sign_token_on_lv(short_id)
    except Exception as e:
        print(f"PORTAL_SETUP_FAIL: cannot sign on LV: {e}", file=sys.stderr)
        return 1

    page_url = site_urls.public_setup_url(token)
    code, body = _get(page_url)
    print(f"setup page url={page_url[:80]}... http={code}")
    if code != 200:
        print("PORTAL_SETUP_FAIL: setup page not 200", file=sys.stderr)
        return 1
    if _SECRET_RE.search(body):
        print("PORTAL_SETUP_FAIL: page may leak secrets", file=sys.stderr)
        return 1
    for needle in ("setup-qr", "setup.js", "btn-copy", "setup-content"):
        if needle not in body:
            print(f"PORTAL_SETUP_FAIL: missing {needle!r}", file=sys.stderr)
            return 1

    api_base = site_urls.public_setup_url("").rstrip("/")
    verify_url = f"{api_base}/api/verify?t={token}"
    vcode, vbody = _get(verify_url)
    print(f"verify url={verify_url[:80]}... http={vcode}")
    try:
        doc = json.loads(vbody)
    except json.JSONDecodeError:
        print("PORTAL_SETUP_FAIL: verify not JSON", file=sys.stderr)
        return 1
    if not doc.get("ok") or not doc.get("sub_url"):
        print(f"PORTAL_SETUP_FAIL: verify failed: {doc}", file=sys.stderr)
        return 1
    if short_id not in doc["sub_url"]:
        print("PORTAL_SETUP_FAIL: sub_url mismatch", file=sys.stderr)
        return 1

    paste_url = site_urls.public_setup_url("")
    pcode, pbody = _get(paste_url)
    print(f"setup paste url={paste_url} http={pcode}")
    if pcode != 200:
        print("PORTAL_SETUP_FAIL: setup paste page not 200", file=sys.stderr)
        return 1
    for needle in ("setup-signup", "signup-email", "btn-signup-submit"):
        if needle not in pbody:
            print(f"PORTAL_SETUP_FAIL: signup page missing {needle!r}", file=sys.stderr)
            return 1

    print("PORTAL_SETUP_PAGE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
