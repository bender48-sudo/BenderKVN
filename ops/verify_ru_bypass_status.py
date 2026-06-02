#!/usr/bin/env python3
"""Report RU bypass mode: normal (geoip:ru direct) vs emergency (tun-all-proxy).

Usage:
    python ops/verify_ru_bypass_status.py
    python ops/verify_ru_bypass_status.py --json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from ru_bypass_routing import EXTRA_DIRECT_DOMAINS, routing_rule_has_matchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def analyze_template(doc: dict) -> dict:
    rules = (doc.get("routing") or {}).get("rules") or []
    has_geoip_ru = any(
        r.get("outboundTag") == "direct" and (r.get("ip") or []) == ["geoip:ru"]
        for r in rules
    )
    has_category_ru = any(
        r.get("outboundTag") == "direct"
        and (
            "geosite:category-ru" in (r.get("domain") or [])
            or "geosite:ru" in (r.get("domain") or [])
            or any("regexp:.*\\.ru$" in str(d) for d in (r.get("domain") or []))
        )
        for r in rules
    )
    has_regexp_ru = any(
        r.get("outboundTag") == "direct"
        and any("regexp:.*\\.ru$" in str(d) for d in (r.get("domain") or []))
        for r in rules
    )
    direct_domains: set[str] = set()
    for r in rules:
        if r.get("outboundTag") == "direct":
            for d in r.get("domain") or []:
                if isinstance(d, str) and not d.startswith(("geosite:", "regexp:")):
                    direct_domains.add(d)

    missing_extra = [d for d in EXTRA_DIRECT_DOMAINS if d not in direct_domains]
    degenerate = sum(
        1
        for r in rules
        if (r.get("outboundTag") or r.get("balancerTag"))
        and not routing_rule_has_matchers(r)
    )

    if not has_geoip_ru:
        mode = "emergency_tun_all_proxy"
    elif has_category_ru and has_regexp_ru:
        mode = "normal"
    else:
        mode = "partial"

    return {
        "mode": mode,
        "has_geoip_ru_direct": has_geoip_ru,
        "has_category_ru": has_category_ru,
        "has_regexp_ru": has_regexp_ru,
        "extra_direct_count": len(direct_domains & set(EXTRA_DIRECT_DOMAINS)),
        "extra_direct_total": len(EXTRA_DIRECT_DOMAINS),
        "missing_extra_domains": missing_extra,
        "degenerate_rules": degenerate,
        "routing_rules_count": len(rules),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=60)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    report = analyze_template(tpl.get("templateJson") or {})

    ok = (
        report["mode"] == "normal"
        and report["degenerate_rules"] == 0
        and not report["missing_extra_domains"]
    )
    report["ok"] = ok

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    print(f"RU bypass mode: {report['mode']}")
    print(f"geoip:ru direct: {report['has_geoip_ru_direct']}")
    print(f"extra domains: {report['extra_direct_count']}/{report['extra_direct_total']}")
    print(f"degenerate rules: {report['degenerate_rules']}")
    if report["missing_extra_domains"]:
        print(f"missing EXTRA_DIRECT_DOMAINS ({len(report['missing_extra_domains'])}): "
              f"{report['missing_extra_domains'][:8]}{'…' if len(report['missing_extra_domains']) > 8 else ''}")
        print("fix: python ops/ru_bypass_routing.py --apply")

    if report["mode"] == "emergency_tun_all_proxy":
        print("WARN: geoip:ru direct removed — emergency tun-all-proxy active")
        print("restore: re-apply stable routing or patch_restore_happ_stable.py")

    if ok:
        print("RU_BYPASS_STATUS_OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
