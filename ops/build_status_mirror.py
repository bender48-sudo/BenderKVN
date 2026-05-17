#!/usr/bin/env python3
"""Build public HTTPS status JSON (P2-RED-BOOT-01 backup ops channel)."""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_OPS = Path(__file__).resolve().parent
_ROOT = _OPS.parent
for _p in (_OPS, _ROOT / "ops"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# Optional: source /etc/bvpn/balancer.env on LV before import.
_BAL_ENV = Path("/etc/bvpn/balancer.env")
if _BAL_ENV.is_file() and not os.environ.get("PANEL_TOKEN"):
    from load_env_file import load_env_file as _lef  # noqa: E402

    for k, v in _lef(_BAL_ENV).items():
        os.environ.setdefault(k, v)

import site_urls  # noqa: E402
from panel_client import PanelClient  # noqa: E402
from public_status_page import render_public_html  # noqa: E402

DECOM_NODES = {"Amsterdam-01"}


def _probe_url(url: str, timeout: float = 8.0) -> int:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def _probe_telegram_api() -> str:
    try:
        code = _probe_url("https://api.telegram.org/", timeout=5.0)
        return "reachable" if code in (200, 301, 302, 404) else "degraded"
    except Exception:
        return "unknown"


def build_status() -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    client = PanelClient()
    fwd = {"X-Forwarded-Proto": "https", "X-Forwarded-For": "127.0.0.1"}

    nodes_out: list[dict] = []
    overall = "ok"
    code_n, nodes_payload = client.get("/api/nodes", extra_headers=fwd)
    if code_n != 200:
        overall = "degraded"
        nodes_payload = {}
    for n in (nodes_payload or {}).get("response") or []:
        name = n.get("name", "?")
        connected = bool(n.get("isConnected"))
        expected = name in DECOM_NODES
        if not connected and not expected:
            overall = "degraded"
        nodes_out.append(
            {"name": name, "connected": connected, "expected_down": expected}
        )

    hosts_summary = {}
    code_h, hosts_payload = client.get("/api/hosts", extra_headers=fwd)
    if code_h == 200:
        hosts = (hosts_payload or {}).get("response") or []
        hosts_summary = {
            "total": len(hosts),
            "visible": sum(
                1 for h in hosts if not h.get("isHidden") and not h.get("isDisabled")
            ),
            "hidden": sum(1 for h in hosts if h.get("isHidden")),
            "disabled": sum(1 for h in hosts if h.get("isDisabled")),
        }
    else:
        overall = "degraded"

    sub_primary = _probe_url(site_urls.sub_monitor_probe_url())
    sub_alt_codes = {}
    for origin in site_urls.SUB_ALT_PUBLIC_ORIGINS:
        suffix = os.environ.get(
            "SUB_MONITOR_PROBE_SUFFIX", "api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2"
        ).lstrip("/")
        sub_alt_codes[origin] = _probe_url(f"{origin.rstrip('/')}/{suffix}")
    if sub_primary not in (200, 304):
        overall = "degraded"

    tg_api = _probe_telegram_api()
    msg = "All core checks green."
    if overall != "ok":
        msg = "Degraded: review nodes/subscription in JSON."

    return {
        "service": "bender-vpn",
        "schema": "status-mirror/v1",
        "updated_at": now,
        "overall": overall,
        "message": msg,
        "channels": {
            "primary_admin": "telegram",
            "telegram_bot_api": tg_api,
            "https_status_mirror": site_urls.status_mirror_url(),
        },
        "subscription": {
            "primary_origin": site_urls.SUB_PUBLIC_ORIGIN,
            "primary_http": sub_primary,
            "alt_origins_http": sub_alt_codes,
        },
        "nodes": nodes_out,
        "hosts": hosts_summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-o",
        "--output",
        default="/var/www/bvpn-status/status.json",
        help="write path (default LV web root)",
    )
    ap.add_argument("--stdout", action="store_true", help="print JSON only")
    args = ap.parse_args()

    doc = build_status()
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"

    if args.stdout:
        print(text, end="")
        return 0

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(out)

    html_path = out.parent / "index.html"
    incidents = out.parent / "incidents.json"
    html_tmp = html_path.with_suffix(".html.tmp")
    html_tmp.write_text(
        render_public_html(
            doc,
            incidents if incidents.is_file() else None,
            json_url=site_urls.status_mirror_url(),
        ),
        encoding="utf-8",
    )
    html_tmp.replace(html_path)
    print(
        f"STATUS_MIRROR_WRITTEN {out} html={html_path} overall={doc['overall']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
