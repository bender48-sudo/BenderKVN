#!/usr/bin/env python3
"""P3-FLOW-02: HMAC-signed setup page tokens (shortId + expiry)."""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402

_SHORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _secret() -> bytes:
    key = os.environ.get("PORTAL_SETUP_HMAC_SECRET", "").strip()
    if not key:
        raise ValueError("PORTAL_SETUP_HMAC_SECRET is not set")
    return key.encode("utf-8")


def sign_setup_token(short_id: str, ttl_hours: int = 72) -> str:
    sid = short_id.strip()
    if not _SHORT_ID_RE.match(sid):
        raise ValueError(f"invalid short_id: {short_id!r}")
    exp = int(time.time()) + int(ttl_hours) * 3600
    payload = {"v": 1, "sid": sid, "exp": exp}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_secret(), raw, hashlib.sha256).digest()
    return f"v1.{_b64url_encode(raw)}.{_b64url_encode(sig)}"


def verify_setup_token(token: str) -> dict:
    parts = token.strip().split(".")
    if len(parts) != 3 or parts[0] != "v1":
        raise ValueError("invalid token format")
    raw = _b64url_decode(parts[1])
    sig = _b64url_decode(parts[2])
    expected = hmac.new(_secret(), raw, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("invalid signature")
    payload = json.loads(raw.decode("utf-8"))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("token expired")
    sid = payload.get("sid", "")
    if not _SHORT_ID_RE.match(sid):
        raise ValueError("invalid sid in token")
    sub_url = site_urls.sub_url_from_short_id(sid)
    return {"short_id": sid, "exp": payload["exp"], "sub_url": sub_url}


def main() -> int:
    ap = argparse.ArgumentParser(description="Sign/verify portal setup tokens")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sign", help="create token for shortId")
    s.add_argument("--short-id", required=True)
    s.add_argument("--ttl-hours", type=int, default=72)

    v = sub.add_parser("verify", help="verify token and print sub URL")
    v.add_argument("--token", required=True)

    args = ap.parse_args()
    try:
        if args.cmd == "sign":
            tok = sign_setup_token(args.short_id, ttl_hours=args.ttl_hours)
            print(tok)
            return 0
        info = verify_setup_token(args.token)
        print(json.dumps(info, ensure_ascii=False))
        return 0
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
