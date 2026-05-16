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
