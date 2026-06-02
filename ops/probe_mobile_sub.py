#!/usr/bin/env python3
"""Quick mobile/desktop subscription sanity (routing + DNS + outbounds)."""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from panel_client import PanelClient  # noqa: E402
from subscription_fetch import decode_subscription, fetch_url, xray_config_root  # noqa: E402

UAS = [
    ("ios", "Happ/1.9.4 (iOS)"),
    ("android", "Happ/2.16.2 (Android)"),
    ("windows", "Happ/2.16.2 (Windows)"),
]


def main() -> int:
    c = PanelClient()
    users = c.get_or_raise("/api/users?limit=50")["response"]["users"]
    active = [u for u in users if u.get("status") == "ACTIVE" and u.get("shortUuid")]
    print(f"active users: {len(active)}")
    if not active:
        return 1

    ok = True
    for label, ua in UAS:
        u = random.choice(active)
        short = u["shortUuid"]
        r = None
        for attempt in range(3):
            try:
                r = fetch_url(
                    f"{site_urls.SUB_PUBLIC_ORIGIN}/api/sub/{short}",
                    headers={"User-Agent": ua},
                )
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                print(f"{label}: retry {attempt + 1} ({exc})")
                time.sleep(1.5)
        assert r is not None
        cfg = xray_config_root(decode_subscription(r.body))
        rules = (cfg.get("routing") or {}).get("rules") or []
        dns = cfg.get("dns") or {}
        servers = dns.get("servers") if isinstance(dns.get("servers"), list) else []
        tg_rule = any(
            "geosite:telegram" in (rule.get("domain") or [])
            for rule in rules
        )
        openai_rule = any(
            "geosite:openai" in (rule.get("domain") or [])
            for rule in rules
        )
        line_ok = r.status == 200 and len(rules) >= 6 and tg_rule and openai_rule
        ok = ok and line_ok
        print(
            f"{label}: HTTP {r.status} rules={len(rules)} "
            f"dns_servers={len(servers)} outbounds={len(cfg.get('outbounds') or [])} "
            f"tg={'yes' if tg_rule else 'NO'} openai={'yes' if openai_rule else 'NO'} "
            f"{'OK' if line_ok else 'FAIL'}"
        )

    s = c.get_or_raise("/api/subscription-settings")["response"]
    hr = s.get("happRouting") or ""
    print(f"happRouting configured: {'yes' if hr else 'no'} ({len(hr)} chars)")
    print(f"happAnnounce: {(s.get('happAnnounce') or '')[:60]!r}")
    print("PROBE_MOBILE_SUB_OK" if ok else "PROBE_MOBILE_SUB_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
