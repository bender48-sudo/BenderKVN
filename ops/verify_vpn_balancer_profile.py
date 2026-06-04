#!/usr/bin/env python3
"""Smoke: live Happ sub matches RU multipath balancer profile (no relay SPOF).

Exit 0 prints VPN_BALANCER_PROFILE_OK. Used before/after template patches.
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
from balancer_selectors import (  # noqa: E402
    INTL_RELAY_NL_443_SELECTOR,
    INTL_RELAY_NL_SELECTOR,
    INTL_STEALTH_BALANCER_TAG,
    RELAY1_SELECTOR,
    RELAY2_SELECTOR,
    RELAY6_SELECTOR,
    is_stealth_split_profile,
    is_stealth_split_relay_nl_443_profile,
    verify_ru_multipath_profile,
)
from dns_split_config import verify_dns_split_config  # noqa: E402
from panel_client import _load_token  # noqa: E402
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
    try:
        token = _load_token(None)
    except FileNotFoundError:
        print(
            "FAIL: set PANEL_TOKEN/REMNA_API_TOKEN or create .secrets/panel-token.txt",
            file=sys.stderr,
        )
        return 1
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
    dns_warn = verify_dns_split_config(cfg)
    if dns_warn:
        for w in dns_warn:
            if "geosite" in w:
                print(f"FAIL: {w}", file=sys.stderr)
                return 1
            print(f"INFO: dns note: {w}")
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

    want_proxy = 16 if is_stealth_split_relay_nl_443_profile(cfg) else None
    if want_proxy is not None and proxy_n != want_proxy:
        print(
            f"FAIL: vless_proxy={proxy_n} want {want_proxy} (injectHosts parity)",
            file=sys.stderr,
        )
        return 1

    balancers = {
        b.get("tag"): b for b in (cfg.get("routing") or {}).get("balancers") or []
    }
    super_len = len((balancers.get("Super_Balancer") or {}).get("selector") or [])
    intl_len = len((balancers.get("Intl_Direct") or {}).get("selector") or [])
    intl_sel = list((balancers.get("Intl_Direct") or {}).get("selector") or [])
    if super_len == 4 and intl_len == 6:
        mode = "split Super=LV×4 Intl=relay×6"
    elif super_len == 0 and intl_sel == list(RELAY6_SELECTOR):
        mode = "relay-only×6"
    elif super_len == 0 and intl_sel == list(RELAY1_SELECTOR):
        mode = "relay-only×3 (relay1 fast path)"
    elif super_len == 0 and intl_sel == list(RELAY2_SELECTOR):
        mode = "relay-only×3 (relay2 fast path)"
    elif super_len == 0 and is_stealth_split_relay_nl_443_profile(cfg):
        stealth_len = len((balancers.get(INTL_STEALTH_BALANCER_TAG) or {}).get("selector") or [])
        mode = f"stealth split Stealth=relay×{stealth_len} Fast=relay+NL+relay-NL×{intl_len}"
    elif super_len == 0 and is_stealth_split_profile(cfg):
        stealth_len = len((balancers.get(INTL_STEALTH_BALANCER_TAG) or {}).get("selector") or [])
        mode = f"stealth split Stealth=relay×{stealth_len} Fast=relay+NL×{intl_len}"
    elif super_len == 0 and intl_sel == list(INTL_RELAY_NL_SELECTOR):
        mode = "relay×6+NL×4 Intl (VPN-AUD-220)"
    elif super_len == 0 and intl_len >= 3:
        mode = f"relay-only×{intl_len}"
    elif super_len == 7 and intl_len == 11:
        mode = "split Super=7 Intl=11"
    else:
        mode = f"Super={super_len} Intl={intl_len}"
    has_dns = bool(cfg.get("dns"))
    dns_ok = not dns_warn
    dns_label = "no" if not has_dns else ("yes" if dns_ok else "BROKEN")
    print(
        f"OK: sub HTTP 200, Super+Intl multipath ({mode}), policy 30/30, "
        f"no observatory, vless_proxy={proxy_n}, dns={dns_label}"
    )
    print("VPN_BALANCER_PROFILE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
