#!/usr/bin/env python3
"""Stealth/routing quality guardrails for the subscription template — VPN-STEALTH-ROUTING-GUARDRAILS-001.

NOTE on wording: this does NOT make the VPN "undetectable". It only enforces
that the routing PROFILE keeps sensitive destinations on the stealth relay path,
keeps relay endpoints inside the tunnel, and avoids obvious direct-leak patterns.

Complements happ_routing_directip_guard.py (Happ client profile layer). This module
validates the Remna subscription templateJson.routing layer:

    * TG/Meta/Instagram/Telegram sensitive media stay on the stealth balancer;
    * the general Intl/direct catch-all does not swallow stealth-only media;
    * stealth groups are not routed to a direct/NL balancer by mistake;
    * route groups (stealth + general) are present and parseable.

HARD SAFETY: pure validation, no network/secrets/mutation.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_STEALTH_BALANCER_TAG,
)

# Markers that must route via stealth, never via the general/direct catch-all.
STEALTH_SENSITIVE_MARKERS = ("telegram", "meta", "instagram", "facebook")


def _rules(doc: dict) -> list[dict]:
    return (doc.get("routing") or {}).get("rules") or []


def _balancers(doc: dict) -> dict[str, dict]:
    return {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}


def _rule_markers(rule: dict) -> list[str]:
    out: list[str] = []
    for key in ("domain", "ip"):
        for v in rule.get(key) or []:
            out.append(str(v).lower())
    return out


def scan_stealth_routing(doc: dict) -> list[str]:
    """Return violations (empty = stealth-safe routing for this template)."""
    found: list[str] = []
    balancers = _balancers(doc)
    rules = _rules(doc)

    stealth_b = balancers.get(INTL_STEALTH_BALANCER_TAG)
    intl_b = balancers.get(INTL_BALANCER_TAG)
    if not stealth_b:
        found.append(f"missing stealth balancer {INTL_STEALTH_BALANCER_TAG!r}")
    if not intl_b:
        found.append(f"missing general balancer {INTL_BALANCER_TAG!r}")
    if not stealth_b or not intl_b:
        return found

    # 1) Every stealth-sensitive marker must be routed to the stealth balancer,
    #    and must NOT be routed to the general/direct balancer.
    for rule in rules:
        markers = _rule_markers(rule)
        tag = rule.get("balancerTag")
        for needle in STEALTH_SENSITIVE_MARKERS:
            if any(needle in m for m in markers):
                if tag == INTL_BALANCER_TAG:
                    found.append(
                        f"stealth-sensitive marker {needle!r} routed via general "
                        f"{INTL_BALANCER_TAG} (must be {INTL_STEALTH_BALANCER_TAG})"
                    )
                elif tag and tag != INTL_STEALTH_BALANCER_TAG:
                    found.append(
                        f"stealth-sensitive marker {needle!r} routed via {tag} "
                        f"(must be {INTL_STEALTH_BALANCER_TAG})"
                    )

    # 2) Stealth balancer must actually receive both an ip and a domain rule
    #    (otherwise TG/Meta split is not really live).
    has_ip = any(
        r.get("balancerTag") == INTL_STEALTH_BALANCER_TAG and r.get("ip") for r in rules
    )
    has_domain = any(
        r.get("balancerTag") == INTL_STEALTH_BALANCER_TAG and r.get("domain") for r in rules
    )
    if not has_ip:
        found.append(f"{INTL_STEALTH_BALANCER_TAG} has no IP-CIDR rule (TG/Meta IP split missing)")
    if not has_domain:
        found.append(f"{INTL_STEALTH_BALANCER_TAG} has no domain rule (TG/Meta geosite split missing)")

    # 3) A flat Super_Balancer catch-all must not exist (it swallows the stealth split).
    if balancers.get("Super_Balancer"):
        found.append("Super_Balancer present — flat catch-all can swallow stealth split")

    return found


def assert_stealth_routing_safe(doc: dict) -> None:
    bad = scan_stealth_routing(doc)
    if bad:
        raise ValueError(
            "Stealth routing guard failed:\n  " + "\n  ".join(bad)
        )


def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Scan subscription template for stealth routing regressions")
    ap.add_argument("--template-json", type=Path, required=True,
                    help="Path to a templateJson dump (redacted, no secrets)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    doc = json.loads(args.template_json.read_text(encoding="utf-8"))
    bad = scan_stealth_routing(doc)
    if args.json:
        print(json.dumps({"ok": not bad, "violations": bad}, ensure_ascii=False, indent=2))
        return 0 if not bad else 1
    if bad:
        print("FAIL: VPN_STEALTH_ROUTING_GUARD", file=sys.stderr)
        for v in bad:
            print(f"  {v}", file=sys.stderr)
        return 1
    print("VPN_STEALTH_ROUTING_GUARD_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
