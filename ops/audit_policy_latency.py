#!/usr/bin/env python3
"""VPN-AUD-111: verify live sub policy does not regress latency (handshake/connIdle).

Canonical Happ-stable profile (post gen=26):
  handshake=4, connIdle=300, bufferSize=128, uplink/downlinkOnly=30

NO-GO: handshake=12 (fast-connect experiment — adds connect latency).

Usage:
    python ops/audit_policy_latency.py
    python ops/audit_policy_latency.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from balancer_selectors import POLICY_DOWNLINK_ONLY, POLICY_UPLINK_ONLY  # noqa: E402
from subscription_fetch import HAPP_UA, decode_subscription, fetch_url, xray_config_root  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = ROOT / ".secrets" / "panel-token.txt"

CANONICAL = {
    "handshake": 4,
    "connIdle": 300,
    "bufferSize": 128,
    "uplinkOnly": POLICY_UPLINK_ONLY,
    "downlinkOnly": POLICY_DOWNLINK_ONLY,
}
FORBIDDEN = {12: "handshake=12 (fast-connect regression)"}


def audit_policy(lv0: dict) -> list[str]:
    errors: list[str] = []
    for key, want in CANONICAL.items():
        got = lv0.get(key)
        if got != want:
            errors.append(f"policy.levels.0.{key}={got!r} want {want!r}")
    hs = lv0.get("handshake")
    if hs in FORBIDDEN:
        errors.append(FORBIDDEN[hs])
    return errors


def fetch_live_policy() -> tuple[dict, str]:
    if not TOKEN_PATH.is_file():
        raise SystemExit(f"missing {TOKEN_PATH}")
    token = TOKEN_PATH.read_text(encoding="ascii").strip()
    panel = site_urls.PANEL_URL
    sub_origin = site_urls.SUB_PUBLIC_ORIGIN

    users_resp = fetch_url(
        f"{panel}/api/users?limit=5&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if users_resp.status != 200:
        raise SystemExit(f"users HTTP {users_resp.status}")
    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    if not users:
        raise SystemExit("no users")
    short = users[0].get("shortUuid")
    sub_url = f"{sub_origin}/api/sub/{short}"
    sub_resp = fetch_url(sub_url, headers={"User-Agent": HAPP_UA})
    if sub_resp.status != 200:
        raise SystemExit(f"sub HTTP {sub_resp.status}")
    cfg = xray_config_root(decode_subscription(sub_resp.body))
    lv0 = (cfg.get("policy") or {}).get("levels", {}).get("0") or {}
    return lv0, sub_url


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    lv0, sub_url = fetch_live_policy()
    errors = audit_policy(lv0)

    if args.json:
        print(
            json.dumps(
                {
                    "sub_url": sub_url,
                    "policy_levels_0": lv0,
                    "canonical": CANONICAL,
                    "ok": not errors,
                    "errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if errors else 0

    print(f"sub_url: {sub_url}")
    print("policy.levels.0:", json.dumps(lv0, ensure_ascii=False))
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("AUDIT_POLICY_LATENCY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
