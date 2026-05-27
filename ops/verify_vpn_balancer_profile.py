#!/usr/bin/env python3
"""Smoke: live Happ sub matches RU multipath balancer profile (no relay SPOF).

Exit 0 prints VPN_BALANCER_PROFILE_OK. Used before/after template patches.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from balancer_selectors import verify_ru_multipath_profile  # noqa: E402
from subscription_fetch import (  # noqa: E402
    HAPP_UA,
    decode_subscription,
    fetch_url,
    happ_batch_parseable,
    outbound_network,
    xray_config_root,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = ROOT / ".secrets" / "panel-token.txt"


def main() -> int:
    if not TOKEN_PATH.is_file():
        print(f"FAIL: missing {TOKEN_PATH}", file=sys.stderr)
        return 1

    token = TOKEN_PATH.read_text(encoding="ascii").strip()
    panel = site_urls.PANEL_URL
    sub_origin = site_urls.SUB_PUBLIC_ORIGIN

    users_resp = fetch_url(
        f"{panel}/api/users?limit=5&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if users_resp.status != 200:
        print(f"FAIL: users HTTP {users_resp.status}", file=sys.stderr)
        return 1

    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    if not users:
        print("FAIL: no users", file=sys.stderr)
        return 1

    short = users[0].get("shortUuid")
    sub_resp = fetch_url(
        f"{sub_origin}/api/sub/{short}",
        headers={"User-Agent": HAPP_UA},
    )
    if sub_resp.status != 200:
        print(f"FAIL: sub HTTP {sub_resp.status}", file=sys.stderr)
        return 1
    if not sub_resp.content_type_ok:
        print(f"FAIL: Content-Type {sub_resp.content_type!r}", file=sys.stderr)
        return 1

    cfg = xray_config_root(decode_subscription(sub_resp.body))
    errs = verify_ru_multipath_profile(cfg)
    if errs:
        print("FAIL:", "; ".join(errs), file=sys.stderr)
        return 1

    xhttp = bad = 0
    proxy_n = 0
    for o in cfg.get("outbounds") or []:
        if o.get("protocol") != "vless":
            continue
        tag = str(o.get("tag") or "")
        if tag.startswith("proxy"):
            proxy_n += 1
        net = outbound_network(o)
        if net == "xhttp":
            xhttp += 1
        ok, _ = happ_batch_parseable(o)
        if not ok:
            bad += 1

    if xhttp or bad:
        print(f"FAIL: xhttp={xhttp} batch_fail={bad}", file=sys.stderr)
        return 1

    print(
        f"OK: sub HTTP 200, Super+Intl multipath (11), policy 30/30, "
        f"no observatory, vless_proxy={proxy_n}"
    )
    print("VPN_BALANCER_PROFILE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
