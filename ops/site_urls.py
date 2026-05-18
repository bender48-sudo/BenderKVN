"""Public production URLs (no secrets) for BenderVPN ops scripts.

Resolution order for each value:
  1. Already set in ``os.environ`` (wins)
  2. Optional untracked ``ops/site.env`` (``export KEY=value`` or ``KEY=value`` lines)
  3. Built-in defaults matching current prod

``site.env`` typically is gitignored via the ``*.env`` pattern; use
``site.env.example`` as a template.

Importing this module applies the file load once (``setdefault`` only).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
_ROOT = _OPS.parent
_SITE_ENV = _OPS / "site.env"

if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from load_env_file import load_env_file as _parse_env_file


def _load_site_env_file() -> None:
    if not _SITE_ENV.is_file():
        return
    for k, v in _parse_env_file(_SITE_ENV).items():
        os.environ.setdefault(k, v)


_load_site_env_file()

# Aliases: legacy example used PANEL_PUBLIC_URL
if "PANEL_URL" not in os.environ and os.environ.get("PANEL_PUBLIC_URL"):
    os.environ["PANEL_URL"] = os.environ["PANEL_PUBLIC_URL"]

PANEL_URL = os.environ.get("PANEL_URL", "https://k9x2m1.conntest.xyz:2053").rstrip("/")
SUB_PUBLIC_ORIGIN = os.environ.get(
    "SUB_PUBLIC_ORIGIN", "https://p4n7q.conntest.xyz:2053"
).rstrip("/")

# P2-RED-SUB-01: comma-separated alternate subscription HTTPS origins (different DNS name, same backend).
_raw_alt = os.environ.get("SUB_ALT_PUBLIC_ORIGINS", "https://k9x2m1.conntest.xyz:2053")
SUB_ALT_PUBLIC_ORIGINS = [o.strip().rstrip("/") for o in _raw_alt.split(",") if o.strip()]
REMNA_TEMPLATE_UUID = os.environ.get(
    "REMNA_TEMPLATE_UUID", "9ebbce97-ae45-4f39-a7e6-d7e675a94a73"
)
RU_RELAY_HOST = os.environ.get("RU_RELAY_HOST", "72.56.0.145")
RU_RELAY_SSH_PORT = os.environ.get("RU_RELAY_SSH_PORT", "3344")

# Same shortId path as monitor.sh / daily-report.sh (public smoke URL, not a secret).
_SUB_MONITOR_SUFFIX = os.environ.get(
    "SUB_MONITOR_PROBE_SUFFIX", "api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2"
).lstrip("/")


def sub_monitor_probe_url() -> str:
    """HTTPS URL used for subscription edge health (returns 200 when OK)."""
    return f"{SUB_PUBLIC_ORIGIN}/{_SUB_MONITOR_SUFFIX}"


STATUS_MIRROR_PATH = os.environ.get(
    "STATUS_MIRROR_PATH", "/api/ops/status.json"
).lstrip("/")


def status_mirror_url() -> str:
    """Public HTTPS JSON ops status (P2-RED-BOOT-01), alt panel/sub domain."""
    origin = os.environ.get(
        "STATUS_MIRROR_ORIGIN", SUB_ALT_PUBLIC_ORIGINS[0] if SUB_ALT_PUBLIC_ORIGINS else PANEL_URL
    ).rstrip("/")
    return f"{origin}/{STATUS_MIRROR_PATH}"


PUBLIC_STATUS_PATH = os.environ.get("PUBLIC_STATUS_PATH", "/status").strip()
if not PUBLIC_STATUS_PATH.startswith("/"):
    PUBLIC_STATUS_PATH = "/" + PUBLIC_STATUS_PATH


def public_status_url() -> str:
    """User-facing HTML incident status page (P5-COM-01)."""
    origin = os.environ.get(
        "PUBLIC_STATUS_ORIGIN",
        SUB_ALT_PUBLIC_ORIGINS[0] if SUB_ALT_PUBLIC_ORIGINS else PANEL_URL,
    ).rstrip("/")
    path = PUBLIC_STATUS_PATH.rstrip("/") or "/status"
    return f"{origin}{path}"


def _portal_origin() -> str:
    return os.environ.get(
        "PUBLIC_PORTAL_ORIGIN",
        SUB_ALT_PUBLIC_ORIGINS[0] if SUB_ALT_PUBLIC_ORIGINS else PANEL_URL,
    ).rstrip("/")


PUBLIC_BOOTSTRAP_PATH = os.environ.get(
    "PUBLIC_BOOTSTRAP_PATH", "/start"
).strip()
if not PUBLIC_BOOTSTRAP_PATH.startswith("/"):
    PUBLIC_BOOTSTRAP_PATH = "/" + PUBLIC_BOOTSTRAP_PATH

PUBLIC_PORTAL_PATH = os.environ.get("PUBLIC_PORTAL_PATH", "/portal").strip()
if not PUBLIC_PORTAL_PATH.startswith("/"):
    PUBLIC_PORTAL_PATH = "/" + PUBLIC_PORTAL_PATH

PUBLIC_SETUP_PATH = os.environ.get("PUBLIC_SETUP_PATH", "/setup").strip()
if not PUBLIC_SETUP_PATH.startswith("/"):
    PUBLIC_SETUP_PATH = "/" + PUBLIC_SETUP_PATH


def public_bootstrap_url() -> str:
    """Bootstrap landing (P3-FLOW-01), clearnet without VPN."""
    path = PUBLIC_BOOTSTRAP_PATH.rstrip("/") or "/start"
    return f"{_portal_origin()}{path}/"


def public_portal_url() -> str:
    """Canonical portal URL for site + Telegram Mini App (P3-FLOW-12/14)."""
    path = PUBLIC_PORTAL_PATH.rstrip("/") or "/portal"
    return f"{_portal_origin()}{path}/"


def public_guide_url(platform: str | None = None) -> str:
    """Setup video/GIF page (P3-FLOW-06)."""
    base = f"{_portal_origin()}/portal/guide.html"
    if not platform:
        return base
    key = platform.strip().lower()
    if key in ("ios", "iphone", "ipad"):
        return f"{base}?device=iphone"
    if key == "android":
        return f"{base}?device=android"
    return base


def telegram_webapp_url() -> str:
    """Telegram Mini App URL (BotFather Menu Button); defaults to public_portal_url()."""
    explicit = os.environ.get("TELEGRAM_WEBAPP_URL", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"
    return public_portal_url()


def public_setup_url(token: str = "") -> str:
    """Personal setup page (P3-FLOW-02). Token appended as ?t= when set."""
    path = PUBLIC_SETUP_PATH.rstrip("/") or "/setup"
    base = f"{_portal_origin()}{path}"
    if token:
        return f"{base}/?t={token}"
    return f"{base}/"


def sub_url_from_short_id(short_id: str) -> str:
    """Public subscription URL for a panel shortId (capability URL)."""
    sid = short_id.strip().lstrip("/")
    return f"{SUB_PUBLIC_ORIGIN}/api/sub/{sid}"


def probe_short_id() -> str:
    """shortId segment from monitor smoke path (public, not secret)."""
    return _SUB_MONITOR_SUFFIX.split("/")[-1]


def sub_all_probe_urls() -> list[str]:
    """Primary + alternate subscription smoke URLs (same shortId path)."""
    urls = [sub_monitor_probe_url()]
    for origin in SUB_ALT_PUBLIC_ORIGINS:
        u = f"{origin}/{_SUB_MONITOR_SUFFIX}"
        if u not in urls:
            urls.append(u)
    return urls
