#!/usr/bin/env python3
"""Hotfix: geosite:category-ru in direct-rule sends TG/IG/Google to bypass VPN.

Symptom (Happ access_log): sniffed domains match category-ru → [socks -> direct]
while observatory ping to proxy still OK («connected»).

Changes:
  1) Remove geosite:category-ru from the direct domain rule (keep .ru regexp + EXTRA list).
  2) Insert a rule *before* that direct rule: blocked/intl apps → balancer Super_Balancer.

Usage:
    python ops/patch_routing_category_ru_leak.py              # dry-run
    python ops/patch_routing_category_ru_leak.py --apply      # PATCH + sub notify
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
import time
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from panel_client import PanelClient  # noqa: E402
from ru_bypass_routing import strip_degenerate_routing_rules  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID

BALANCER_TAG = "Super_Balancer"
REMOVE_GEOSITE = "geosite:category-ru"

# Must go through VPN even when RU bypass is on (blocked or ISP-throttled on direct).
PROXY_GEOSITES = [
    "geosite:instagram",
    "geosite:facebook",
    "geosite:telegram",
    "geosite:whatsapp",
    "geosite:twitter",
    "geosite:tiktok",
    "geosite:discord",
    "geosite:openai",
    "geosite:google",
    "geosite:youtube",
    "geosite:netflix",
    "geosite:spotify",
    "geosite:apple",
    "geosite:microsoft",
]

PROXY_EXTRA_DOMAINS = [
    "meta.com",
    "fbcdn.net",
    "cdninstagram.com",
    "telegram.org",
    "t.me",
    "telegram.me",
    "telesco.pe",
]


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def find_direct_category_ru_idx(rules: list[dict]) -> int:
    for i, r in enumerate(rules):
        if r.get("outboundTag") == "direct" and REMOVE_GEOSITE in (r.get("domain") or []):
            return i
    return -1


def find_proxy_pre_rule_idx(rules: list[dict]) -> int:
    for i, r in enumerate(rules):
        if r.get("balancerTag") == BALANCER_TAG and REMOVE_GEOSITE in (r.get("domain") or []):
            return i
    return -1


def proxy_rule_domains() -> list[str]:
    return list(PROXY_GEOSITES) + list(PROXY_EXTRA_DOMAINS)


def plan_patch(rules: list[dict]) -> dict:
    direct_idx = find_direct_category_ru_idx(rules)
    proxy_idx = find_proxy_pre_rule_idx(rules)
    has_category_ru = direct_idx >= 0
    has_proxy_rule = proxy_idx >= 0
    return {
        "direct_idx": direct_idx,
        "proxy_idx": proxy_idx,
        "has_category_ru": has_category_ru,
        "has_proxy_rule": has_proxy_rule,
        "needs_patch": has_category_ru or not has_proxy_rule,
    }


def apply_patch(rules: list[dict]) -> tuple[bool, list[str]]:
    """Return (changed, log lines). Mutates rules in place."""
    log: list[str] = []
    plan = plan_patch(rules)
    if not plan["needs_patch"]:
        return False, ["OK: template already patched (no category-ru, proxy rule present)"]

    changed = False

    if plan["has_category_ru"]:
        di = plan["direct_idx"]
        doms = list(rules[di].get("domain") or [])
        if REMOVE_GEOSITE in doms:
            doms.remove(REMOVE_GEOSITE)
            rules[di]["domain"] = doms
            log.append(f"removed {REMOVE_GEOSITE} from direct rule R{di}")
            changed = True

    if not plan["has_proxy_rule"]:
        insert_at = plan["direct_idx"] if plan["direct_idx"] >= 0 else len(rules)
        # If we just removed category-ru, direct_idx still valid; insert before direct domain rule.
        for i, r in enumerate(rules):
            if r.get("outboundTag") == "direct" and (r.get("domain") or r.get("ip")):
                insert_at = i
                break
        new_rule = {
            "domain": proxy_rule_domains(),
            "balancerTag": BALANCER_TAG,
        }
        rules.insert(insert_at, new_rule)
        log.append(f"inserted proxy-apps rule at R{insert_at} ({len(new_rule['domain'])} matchers)")
        changed = True

    n = strip_degenerate_routing_rules(rules)
    if n:
        log.append(f"stripped {n} degenerate rule(s)")
        changed = True

    return changed, log


def patch_template(c: PanelClient, tpl: dict, template_uuid: str) -> None:
    doc = tpl["templateJson"]
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": doc,
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        raise RuntimeError(f"PATCH template HTTP {code}: {body!s}"[:500])


def dump_rules(rules: list[dict]) -> None:
    for i, r in enumerate(rules):
        tag = r.get("outboundTag") or r.get("balancerTag") or "?"
        dom_n = len(r.get("domain") or [])
        ip_n = len(r.get("ip") or [])
        print(f"  R{i}: outbound/balancer={tag} domain={dom_n} ip={ip_n}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    ap.add_argument("--no-sub-notify", action="store_true")
    args = ap.parse_args()

    c = PanelClient()
    tpl = fetch_template(c, args.template_uuid)
    rules = tpl["templateJson"]["routing"]["rules"]

    print("BEFORE:")
    dump_rules(rules)
    plan = plan_patch(rules)
    print(f"plan: {plan}")

    dup = copy.deepcopy(rules)
    changed, log = apply_patch(dup)
    for line in log:
        print(line)

    if not changed:
        return 0

    print("\nAFTER (dry-run preview):")
    dump_rules(dup)
    di = find_direct_category_ru_idx(dup)
    if di >= 0:
        print(f"WARN: {REMOVE_GEOSITE} still in R{di}")
        return 1

    if not args.apply:
        print("\nDry-run only. Apply with:")
        print("  python ops/patch_routing_category_ru_leak.py --apply")
        return 0

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"template-before-category-ru-leak-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl["templateJson"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    apply_patch(rules)
    patch_template(c, tpl, args.template_uuid)

    if not args.no_sub_notify:
        after_template_patch("patch_routing_category_ru_leak")

    print("PATCH OK — users should refresh subscription in Happ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
