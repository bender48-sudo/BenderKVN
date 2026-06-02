#!/usr/bin/env python3
"""Verify RU domains route direct and intl domains hit balancer in live subscription.

Simulates Xray domain rule matching (exact + regexp; geosite assumed present in template).

Usage:
    python ops/probe_ru_bypass.py
    python ops/probe_ru_bypass.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from ru_bypass_routing import EXTRA_DIRECT_DOMAINS, routing_rule_has_matchers  # noqa: E402
from subscription_fetch import HAPP_UA, decode_subscription, fetch_url, xray_config_root  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = ROOT / ".secrets" / "panel-token.txt"

RU_TEST_DOMAINS = ("yandex.ru", "vk.com", "sberbank.ru", "gosuslugi.ru", "ozon.ru")
INTL_TEST_DOMAINS = ("telegram.org", "instagram.com", "youtube.com", "twitter.com")

GEOSITE_RU_MARKERS = frozenset({"geosite:ru", "geosite:category-ru"})


def _match_pattern(domain: str, pattern: str) -> bool | None:
    """Return True/False if matchable; None if pattern needs geosite DB."""
    if pattern.startswith("regexp:"):
        rx = pattern[7:]
        try:
            return bool(re.search(rx, domain))
        except re.error:
            return False
    if pattern.startswith("geosite:"):
        return None
    if pattern.startswith("domain:"):
        base = pattern[7:]
        return domain == base or domain.endswith("." + base)
    if domain == pattern or domain.endswith("." + pattern):
        return True
    return False


def classify_domain(domain: str, rules: list[dict]) -> str:
    for r in rules:
        if not routing_rule_has_matchers(r):
            continue
        tag = r.get("outboundTag") or r.get("balancerTag") or ""
        if r.get("outboundTag") == "block":
            for p in r.get("domain") or []:
                m = _match_pattern(domain, str(p))
                if m is True:
                    return "block"
            continue
        for p in r.get("domain") or []:
            m = _match_pattern(domain, str(p))
            if m is True:
                return tag or "matched"
            if m is None and str(p) in GEOSITE_RU_MARKERS and domain.endswith(".ru"):
                return r.get("outboundTag") or "geosite-assumed"
        for ip_m in r.get("ip") or []:
            if str(ip_m) == "geoip:ru" and domain.endswith(".ru"):
                return r.get("outboundTag") or "geoip-assumed"
    return "default"


def fetch_live_config() -> tuple[dict, str]:
    token = TOKEN_PATH.read_text(encoding="ascii").strip()
    users_resp = fetch_url(
        f"{site_urls.PANEL_URL}/api/users?limit=5&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if users_resp.status != 200:
        raise SystemExit(f"users HTTP {users_resp.status}")
    users = json.loads(users_resp.body).get("response", {}).get("users") or []
    if not users:
        raise SystemExit("no users")
    short = users[0].get("shortUuid")
    sub_resp = fetch_url(
        f"{site_urls.SUB_PUBLIC_ORIGIN}/api/sub/{short}",
        headers={"User-Agent": HAPP_UA},
    )
    if sub_resp.status != 200:
        raise SystemExit(f"sub HTTP {sub_resp.status}")
    return xray_config_root(decode_subscription(sub_resp.body)), short


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if not TOKEN_PATH.is_file():
        print(f"FAIL: missing {TOKEN_PATH}", file=sys.stderr)
        return 1

    cfg, short = fetch_live_config()
    rules = (cfg.get("routing") or {}).get("rules") or []

    results: list[dict] = []
    failures: list[str] = []

    for d in RU_TEST_DOMAINS:
        tag = classify_domain(d, rules)
        ok = tag == "direct"
        results.append({"domain": d, "expect": "direct", "got": tag, "ok": ok})
        if not ok:
            failures.append(f"{d} -> {tag} (want direct)")

    for d in INTL_TEST_DOMAINS:
        tag = classify_domain(d, rules)
        ok = tag in ("Super_Balancer", "Intl_Direct", "proxy", "default")
        if tag == "direct":
            ok = False
        results.append({"domain": d, "expect": "balancer", "got": tag, "ok": ok})
        if not ok:
            failures.append(f"{d} -> {tag} (want balancer, not direct)")

    missing_extra = []
    direct_set: set[str] = set()
    for r in rules:
        if r.get("outboundTag") == "direct":
            for x in r.get("domain") or []:
                if isinstance(x, str) and not x.startswith(("geosite:", "regexp:")):
                    direct_set.add(x)
    for d in EXTRA_DIRECT_DOMAINS:
        if d not in direct_set:
            missing_extra.append(d)

    report = {
        "sub_short": short,
        "tests": results,
        "missing_extra_in_template": missing_extra,
        "ok": not failures and not missing_extra,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    print(f"sub: {short}")
    for t in results:
        status = "OK" if t["ok"] else "FAIL"
        print(f"  [{status}] {t['domain']} -> {t['got']} (expect {t['expect']})")
    if missing_extra:
        print(f"WARN: {len(missing_extra)} EXTRA_DIRECT_DOMAINS not in template direct rule")
        print("fix: python ops/ru_bypass_routing.py --apply")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("PROBE_RU_BYPASS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
