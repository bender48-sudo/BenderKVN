#!/usr/bin/env python3
"""Happ client compatibility guards for subscription templateJson.

Happ ships a bundled geosite.dat without many v2fly/Loyalsoldier codes (notably **RU**).
Using ``geosite:ru`` in routing or dns crashes the core:

  infra/conf: code not found in geosite.dat: RU

Canonical doc: docs/VPN-ROUTING-GEO-GUARDRAILS.md
"""
from __future__ import annotations

from typing import Any

# Routing/dns matchers that break Happ core (confirmed incidents gen=39, gen=50).
HAPP_FORBIDDEN_DOMAIN_MATCHERS = frozenset({"geosite:ru"})

# geosite:category-ru exists in Happ but leaked TG/IG to direct — see category-ru-leak patch.
HAPP_ROUTING_CAUTION = frozenset({"geosite:category-ru"})


def scan_template_json(doc: dict[str, Any]) -> list[str]:
    """Return human-readable violations (empty = Happ-safe for geosite:ru)."""
    found: list[str] = []
    routing = doc.get("routing") or {}
    for i, rule in enumerate(routing.get("rules") or []):
        if not isinstance(rule, dict):
            continue
        for d in rule.get("domain") or []:
            s = str(d)
            if s in HAPP_FORBIDDEN_DOMAIN_MATCHERS:
                found.append(f"routing.rules[{i}].domain contains {s}")
            elif s in HAPP_ROUTING_CAUTION:
                found.append(
                    f"routing.rules[{i}].domain contains {s} "
                    "(TG/IG leak risk — need Intl_Stealth pre-rule)"
                )

    dns = doc.get("dns") or {}
    for j, srv in enumerate(dns.get("servers") or []):
        if not isinstance(srv, dict):
            continue
        geosite = srv.get("geosite")
        if geosite == "ru" or geosite == ["ru"]:
            found.append(f"dns.servers[{j}] geosite=ru")
        for key in ("domains", "domain"):
            val = srv.get(key)
            if not isinstance(val, list):
                continue
            for item in val:
                if str(item) in HAPP_FORBIDDEN_DOMAIN_MATCHERS:
                    found.append(f"dns.servers[{j}] {key} contains {item}")

    return found


def assert_happ_geosite_safe(doc: dict[str, Any]) -> None:
    bad = scan_template_json(doc)
    if bad:
        raise ValueError(
            "Happ-incompatible geosite markers:\n  "
            + "\n  ".join(bad)
            + "\nSee docs/VPN-ROUTING-GEO-GUARDRAILS.md"
        )


def main() -> int:
    import argparse
    import json
    import sys
    from pathlib import Path

    _OPS = Path(__file__).resolve().parent
    if str(_OPS) not in sys.path:
        sys.path.insert(0, str(_OPS))

    import site_urls  # noqa: E402
    from panel_client import PanelClient  # noqa: E402

    ap = argparse.ArgumentParser(description="Scan live template for Happ geosite:ru violations")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient()
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl.get("templateJson") or {}
    bad = scan_template_json(doc)

    if args.json:
        print(json.dumps({"ok": not bad, "violations": bad}, ensure_ascii=False, indent=2))
        return 0 if not bad else 1

    if bad:
        print("FAIL: HAPP_GEOSITE_GUARD", file=sys.stderr)
        for v in bad:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("HAPP_GEOSITE_GUARD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
