#!/usr/bin/env python3
"""VPN-AUD-283: sample N active users — sub byte size + vless proxy count vs injectHosts.

Exit 0 prints SUB_SAMPLE_VERIFY_OK when every sampled user matches inject count.

Usage:
    python ops/probe_users_sub_sample.py
    python ops/probe_users_sub_sample.py --via-lv
    python ops/probe_users_sub_sample.py --sample 5
"""
from __future__ import annotations

import argparse
import io
import json
import random
import subprocess
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient, _load_token  # noqa: E402
from subscription_fetch import (  # noqa: E402
    HAPP_UA,
    decode_subscription,
    fetch_url,
    xray_config_root,
)


def _inject_count() -> int:
    c = PanelClient()
    tpl = c.get_or_raise(f"/api/subscription-templates/{site_urls.REMNA_TEMPLATE_UUID}")["response"]
    return len(tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"]["values"])


def _proxy_count(cfg: dict) -> int:
    return sum(
        1
        for o in cfg.get("outbounds") or []
        if o.get("protocol") == "vless" and str(o.get("tag") or "").startswith("proxy")
    )


def _sample_users(token: str, n: int) -> list[dict]:
    panel = site_urls.PANEL_URL
    sub_origin = site_urls.SUB_PUBLIC_ORIGIN
    users_resp = fetch_url(
        f"{panel}/api/users?limit=200&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if users_resp.status != 200:
        raise RuntimeError(f"users HTTP {users_resp.status}")
    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    active = [
        u
        for u in users
        if u.get("status") == "ACTIVE" and (u.get("shortUuid") or u.get("subscriptionUuid"))
    ]
    if not active:
        raise RuntimeError("no ACTIVE users")
    pick = random.sample(active, k=min(n, len(active)))
    rows: list[dict] = []
    for u in pick:
        short = u.get("shortUuid") or u.get("subscriptionUuid")
        sub_resp = fetch_url(
            f"{sub_origin}/api/sub/{short}",
            headers={"User-Agent": HAPP_UA},
        )
        if sub_resp.status != 200:
            raise RuntimeError(f"sub HTTP {sub_resp.status} user {short}")
        raw = sub_resp.body
        cfg = xray_config_root(decode_subscription(raw))
        rows.append(
            {
                "user": (u.get("username") or short)[:32],
                "short": short,
                "bytes": len(raw),
                "proxy_n": _proxy_count(cfg),
            }
        )
    return rows


def _via_lv(n: int) -> list[dict]:
    remote = (
        "set -a; . /etc/bvpn/ru-monitor.env; set +a; "
        f"python3 /opt/scripts/probe_users_sub_sample.py --sample {n} --json"
    )
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", "bvpn-lv", remote],
        capture_output=True,
        text=True,
        timeout=180,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(out[-1200:] if out else "ssh sample failed")
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            return json.loads(line)
    raise RuntimeError(f"no JSON rows in ssh output: {out[-600:]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=5, help="number of users (default 5)")
    ap.add_argument("--via-lv", action="store_true", help="fetch subs from LV (RU edge)")
    ap.add_argument("--json", action="store_true", help="print only JSON rows (for --via-lv remote)")
    args = ap.parse_args()

    expect = _inject_count()
    if args.via_lv:
        rows = _via_lv(args.sample)
    else:
        try:
            token = _load_token(None)
        except FileNotFoundError:
            print("FAIL: need token or --via-lv", file=sys.stderr)
            return 1
        rows = _sample_users(token, args.sample)

    if args.json:
        print(json.dumps(rows))
        return 0

    print(f"injectHosts expect: {expect}")
    print(f"{'user':32s} {'short':10s} {'bytes':>7s} {'proxy':>5s}")
    bad: list[str] = []
    for r in rows:
        ok = r["proxy_n"] == expect
        mark = "" if ok else " MISMATCH"
        print(f"{r['user']:32s} {r['short']:10s} {r['bytes']:7d} {r['proxy_n']:5d}{mark}")
        if not ok:
            bad.append(r["short"])

    if bad:
        print(f"FAIL: {len(bad)}/{len(rows)} users proxy!={expect}: {bad}", file=sys.stderr)
        return 1

    print(f"SUB_SAMPLE_VERIFY_OK sample={len(rows)} expect={expect}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
