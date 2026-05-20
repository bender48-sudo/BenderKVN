"""Public HTTPS URLs from environment (P1-ENG-CONFIG-01).

Production must set TELEGRAM_WEBAPP_URL and/or PUBLIC_PORTAL_ORIGIN in bot env.
No hardcoded *.conntest.xyz fallbacks when BOT_PAYMENTS_LIVE=1.
"""
from __future__ import annotations

import os


def _payments_live() -> bool:
    return os.getenv("BOT_PAYMENTS_LIVE", "").strip().lower() in ("1", "true", "yes")


def _edge_port() -> str:
    return (os.getenv("EDGE_PUBLIC_PORT", "8443") or "8443").strip()


def _dev_fallback_origin() -> str:
    return f"https://k9x2m1.conntest.xyz:{_edge_port()}"


def portal_origin() -> str:
    explicit = os.getenv("PUBLIC_PORTAL_ORIGIN", "").strip().rstrip("/")
    if explicit:
        return explicit
    webapp = os.getenv("TELEGRAM_WEBAPP_URL", "").strip().rstrip("/")
    if webapp:
        if webapp.endswith("/portal"):
            return webapp[: -len("/portal")].rstrip("/")
        return webapp
    # Prod compose may omit explicit URLs — keep canonical :8443 default (do not crash bot).
    return _dev_fallback_origin()


def telegram_webapp_url() -> str:
    explicit = os.getenv("TELEGRAM_WEBAPP_URL", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"
    return f"{portal_origin().rstrip('/')}/portal/"


def public_bootstrap_url() -> str:
    explicit = os.getenv("PUBLIC_BOOTSTRAP_URL", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"
    path = (os.getenv("PUBLIC_BOOTSTRAP_PATH", "/start") or "/start").strip("/") or "start"
    return f"{portal_origin().rstrip('/')}/{path}/"


def public_status_url() -> str:
    explicit = os.getenv("PUBLIC_STATUS_URL", "").strip()
    if explicit:
        return explicit
    path = (os.getenv("PUBLIC_STATUS_PATH", "/status") or "/status").strip()
    if not path.startswith("/"):
        path = "/" + path
    return f"{portal_origin().rstrip('/')}{path}"


def setup_origin() -> str:
    return (
        os.getenv("PUBLIC_SETUP_ORIGIN", "").strip().rstrip("/")
        or portal_origin().rstrip("/")
    )


def normalize_subscription_url(url: str | None) -> str:
    """Panel may return :2053; public edge serves /api/sub on :8443 (no auth strip on redirect)."""
    u = (url or "").strip()
    if not u:
        return u
    for host in ("p4n7q.conntest.xyz", "k9x2m1.conntest.xyz"):
        u = u.replace(f"://{host}:2053/", f"://{host}:8443/")
        u = u.replace(f"://{host}:2053", f"://{host}:8443")
    return u
