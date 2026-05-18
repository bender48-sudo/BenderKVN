"""Public portal URLs + signed setup tokens (P3-FLOW-03). No panel secrets."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time

_SHORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")

PUBLIC_BOOTSTRAP_URL = (
    os.getenv("PUBLIC_BOOTSTRAP_URL", "https://k9x2m1.conntest.xyz:8443/start/")
    .strip()
    .rstrip("/")
    + "/"
)


def _setup_origin() -> str:
    return os.environ.get(
        "PUBLIC_SETUP_ORIGIN",
        os.environ.get("PUBLIC_PORTAL_ORIGIN", "https://k9x2m1.conntest.xyz:8443"),
    ).rstrip("/")


def _setup_path() -> str:
    path = os.environ.get("PUBLIC_SETUP_PATH", "/setup").strip("/")
    return path or "setup"


def short_id_from_sub_url(sub_url: str | None) -> str | None:
    if not sub_url:
        return None
    segment = sub_url.rstrip("/").split("/")[-1].split("?")[0]
    if _SHORT_ID_RE.match(segment):
        return segment
    return None


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def sign_setup_token(short_id: str, ttl_hours: int = 72) -> str:
    key = os.environ.get("PORTAL_SETUP_HMAC_SECRET", "").strip()
    if not key:
        raise ValueError("PORTAL_SETUP_HMAC_SECRET is not set")
    sid = short_id.strip()
    if not _SHORT_ID_RE.match(sid):
        raise ValueError(f"invalid short_id: {short_id!r}")
    exp = int(time.time()) + int(ttl_hours) * 3600
    payload = {"v": 1, "sid": sid, "exp": exp}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(key.encode("utf-8"), raw, hashlib.sha256).digest()
    return f"v1.{_b64url_encode(raw)}.{_b64url_encode(sig)}"


def public_portal_origin() -> str:
    return _setup_origin()


def public_errors_url(code: str | None = None) -> str:
    """Human-readable errors page (P3-FLOW-08), clearnet without VPN."""
    base = f"{public_portal_origin()}/start/help/errors/"
    if not code:
        return base
    key = code.strip().lower()
    return f"{base}?code={key}"


def public_guide_url(platform: str | None = None) -> str:
    """Setup video/GIF page (P3-FLOW-06), clearnet without VPN."""
    base = f"{public_portal_origin()}/portal/guide.html"
    if not platform:
        return base
    key = platform.strip().lower()
    if key in ("ios", "iphone", "ipad"):
        return f"{base}?device=iphone"
    if key == "android":
        return f"{base}?device=android"
    return base


def public_setup_url(token: str = "") -> str:
    base = f"{_setup_origin()}/{_setup_path()}"
    if token:
        return f"{base}/?t={token}"
    return f"{base}/"


def setup_url_for_sub(sub_url: str | None, ttl_hours: int = 72) -> str | None:
    sid = short_id_from_sub_url(sub_url)
    if not sid:
        return None
    try:
        token = sign_setup_token(sid, ttl_hours=ttl_hours)
    except ValueError:
        return None
    return public_setup_url(token)
