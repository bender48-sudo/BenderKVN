#!/usr/bin/env python3
"""Smoke: live Happ sub is NL-only (LV down failover mode).

Exit 0 prints NL_FAILOVER_SUB_OK.
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from lv_nl_failover_common import analyze_live_sub  # noqa: E402
from subscription_fetch import (  # noqa: E402
    HAPP_UA,
    LV_IP,
    NL_IP,
    RELAY_IP,
    decode_subscription,
    fetch_url,
    xray_config_root,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = ROOT / ".secrets" / "panel-token.txt"


def main() -> int:
    token = os.environ.get("PANEL_TOKEN") or os.environ.get("REMNA_API_TOKEN")
    if not token and TOKEN_PATH.is_file():
        token = TOKEN_PATH.read_text(encoding="ascii").strip()
    if not token:
        print("FAIL: no panel token", file=sys.stderr)
        return 1

    users_resp = fetch_url(
        f"{site_urls.PANEL_URL}/api/users?limit=10&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if users_resp.status != 200:
        print(f"FAIL: users HTTP {users_resp.status}", file=sys.stderr)
        return 1
    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    active = [u for u in users if u.get("status") == "ACTIVE" and u.get("shortUuid")]
    if not active:
        print("FAIL: no active user", file=sys.stderr)
        return 1

    short = active[0]["shortUuid"]
    sub_resp = fetch_url(
        f"{site_urls.SUB_PUBLIC_ORIGIN}/api/sub/{short}",
        headers={"User-Agent": HAPP_UA},
    )
    if sub_resp.status != 200:
        print(f"FAIL: sub HTTP {sub_resp.status}", file=sys.stderr)
        return 1
    if not sub_resp.content_type_ok:
        print(f"WARN: Content-Type {sub_resp.content_type!r}")

    cfg = xray_config_root(decode_subscription(sub_resp.body))
    info = analyze_live_sub(cfg)
    print(
        f"proxy={info['proxy_count']} lv={info['lv_count']} nl={info['nl_count']} "
        f"relay={info['relay_count']} rules={info['rules_count']}"
    )

    errs: list[str] = []
    if info["proxy_count"] < 1:
        errs.append("no proxy outbounds")
    if info["nl_count"] < 1:
        errs.append("no NL endpoint in sub")
    if info["lv_count"] > 0:
        errs.append(f"LV still present ({info['lv_count']} outbounds)")
    if info["relay_count"] > 0:
        errs.append(f"relay still present ({info['relay_count']} outbounds)")
    if info["has_geoip_private"]:
        errs.append("geoip:private still in routing (run patch_routing_client_refresh)")

    if errs:
        print("FAIL:", "; ".join(errs), file=sys.stderr)
        return 1

    print(f"OK: NL-only sub ({info['nl_count']} NL outbounds @ {NL_IP})")
    print("NL_FAILOVER_SUB_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
