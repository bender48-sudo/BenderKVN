#!/usr/bin/env python3
"""Compare injectHosts UUID count vs live Happ sub vless proxy outbounds.

Exit 0 prints INJECT_SUB_PARITY_OK when counts match and relay-NL inject slots
have isHidden=True (required for Remnawave inject export).

Usage:
    python ops/probe_injecthosts_sub_parity.py
    python ops/probe_injecthosts_sub_parity.py --via-lv
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from patch_add_relay_nl_443_hosts import is_relay_nl_443  # noqa: E402
from panel_client import PanelClient, _load_token  # noqa: E402
from subscription_fetch import (  # noqa: E402
    HAPP_UA,
    decode_subscription,
    fetch_url,
    xray_config_root,
)


def _live_proxy_count(token: str) -> tuple[int, str]:
    panel = site_urls.PANEL_URL
    sub_origin = site_urls.SUB_PUBLIC_ORIGIN
    users_resp = fetch_url(
        f"{panel}/api/users?limit=5&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if users_resp.status != 200:
        raise RuntimeError(f"users HTTP {users_resp.status}")
    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    if not users:
        raise RuntimeError("no users")
    short = users[0].get("shortUuid")
    sub_resp = fetch_url(
        f"{sub_origin}/api/sub/{short}",
        headers={"User-Agent": HAPP_UA},
    )
    if sub_resp.status != 200:
        raise RuntimeError(f"sub HTTP {sub_resp.status}")
    cfg = xray_config_root(decode_subscription(sub_resp.body))
    proxy_n = sum(
        1
        for o in cfg.get("outbounds") or []
        if o.get("protocol") == "vless" and str(o.get("tag") or "").startswith("proxy")
    )
    return proxy_n, short


def _via_lv() -> tuple[int, str]:
    remote = "set -a; . /etc/bvpn/ru-monitor.env; set +a; python3 /opt/scripts/probe_injecthosts_sub_parity.py"
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", "bvpn-lv", remote],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 or "INJECT_SUB_PARITY_OK" not in out:
        raise RuntimeError(out[-800:] if out else "ssh probe failed")
    proxy_n = inject_n = 0
    short = "?"
    for line in out.splitlines():
        if line.startswith("injectHosts:"):
            inject_n = int(line.split(":", 1)[1].strip())
        elif line.startswith("live vless_proxy:"):
            proxy_n = int(line.split(":", 1)[1].split()[0].strip())
            if "(user" in line:
                short = line.split("(user", 1)[1].strip().rstrip(")")
    return proxy_n, short


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--via-lv", action="store_true", help="fetch live sub from LV (RU edge)")
    args = ap.parse_args()

    c = PanelClient()
    tpl = c.get_or_raise(f"/api/subscription-templates/{site_urls.REMNA_TEMPLATE_UUID}")["response"]
    inj_uuids = tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"]["values"]
    inject_n = len(inj_uuids)
    hosts = {h["uuid"]: h for h in c.get_or_raise("/api/hosts")["response"]}

    bad_hidden: list[str] = []
    for uid in inj_uuids:
        h = hosts.get(uid)
        if not h:
            continue
        if is_relay_nl_443(h) and not h.get("isHidden"):
            bad_hidden.append(str(h.get("remark") or uid[:8]))

    try:
        token = _load_token(None)
    except FileNotFoundError:
        token = ""
    if args.via_lv:
        proxy_n, short = _via_lv()
    else:
        if not token:
            print("FAIL: need token or --via-lv", file=sys.stderr)
            return 1
        proxy_n, short = _live_proxy_count(token)

    print(f"injectHosts: {inject_n}")
    print(f"live vless_proxy: {proxy_n} (user {short})")
    if bad_hidden:
        print(f"relay-NL not hidden ({len(bad_hidden)}): {bad_hidden[:3]}...")

    errors: list[str] = []
    if proxy_n != inject_n:
        errors.append(f"parity {proxy_n}!={inject_n}")
    if bad_hidden:
        errors.append(f"relay-NL visible={len(bad_hidden)}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("INJECT_SUB_PARITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
