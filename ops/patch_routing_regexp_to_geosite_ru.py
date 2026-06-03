#!/usr/bin/env python3
"""VPN-AUD-210: replace broad regexp:.*\\.ru$ direct matchers with geosite:ru.

Keeps TG/IG via proxy: requires a balancer rule with geosite:telegram *before*
the RU direct domain rule (Intl_Stealth or Super_Balancer — already on prod).

Does NOT re-add geosite:category-ru (leaked TG/IG to direct — see category-ru-leak patch).

Usage:
    python ops/patch_routing_regexp_to_geosite_ru.py              # dry-run A/B preview
    python ops/patch_routing_regexp_to_geosite_ru.py --apply     # snapshot + PATCH + notify
    python ops/patch_routing_regexp_to_geosite_ru.py --rollback .secrets/snapshots/template-before-....json
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

ADD_GEOSITE = "geosite:ru"
FORBIDDEN_GEOSITE = "geosite:category-ru"

REGEXP_RU_PATTERNS = (
    "regexp:.*\\.ru$",
    "regexp:.*\\.xn--p1ai$",
    "regexp:.*\\.xn--p1acf$",
    "regexp:.*\\.xn--p1ag$",
)

PROXY_GEOSITE_MARKERS = frozenset(
    {
        "geosite:telegram",
        "geosite:instagram",
        "geosite:facebook",
    }
)


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def find_direct_ru_rule_idx(rules: list[dict]) -> int:
    for i, r in enumerate(rules):
        if r.get("outboundTag") != "direct":
            continue
        doms = r.get("domain") or []
        if ADD_GEOSITE in doms or any(p in doms for p in REGEXP_RU_PATTERNS):
            return i
    return -1


def find_proxy_pre_rule_idx(rules: list[dict], before_idx: int) -> int:
    for i, r in enumerate(rules):
        if i >= before_idx:
            break
        if not r.get("balancerTag"):
            continue
        doms = set(r.get("domain") or [])
        if doms & PROXY_GEOSITE_MARKERS:
            return i
    return -1


def plan_patch(rules: list[dict]) -> dict:
    direct_idx = find_direct_ru_rule_idx(rules)
    if direct_idx < 0:
        return {"direct_idx": -1, "needs_patch": False, "error": "no direct RU rule"}

    doms = list(rules[direct_idx].get("domain") or [])
    has_regexp = any(p in doms for p in REGEXP_RU_PATTERNS)
    has_geosite_ru = ADD_GEOSITE in doms
    has_category = FORBIDDEN_GEOSITE in doms
    proxy_idx = find_proxy_pre_rule_idx(rules, direct_idx)

    remove = [p for p in REGEXP_RU_PATTERNS if p in doms]
    add_geosite = not has_geosite_ru

    return {
        "direct_idx": direct_idx,
        "proxy_idx": proxy_idx,
        "has_regexp": has_regexp,
        "has_geosite_ru": has_geosite_ru,
        "has_category": has_category,
        "remove_regexp": remove,
        "add_geosite": add_geosite,
        "needs_patch": bool(remove or add_geosite or has_category),
        "proxy_ok": proxy_idx >= 0,
    }


def apply_patch(rules: list[dict]) -> tuple[bool, list[str]]:
    log: list[str] = []
    plan = plan_patch(rules)
    if plan.get("error"):
        return False, [f"skip: {plan['error']}"]
    if not plan["needs_patch"]:
        return False, ["OK: template already uses geosite:ru (no regexp.ru)"]

    if not plan["proxy_ok"]:
        return False, [
            "FATAL: no proxy-apps balancer rule before RU direct rule "
            "(need geosite:telegram/instagram — run patch_routing_category_ru_leak or Intl_Stealth rule)"
        ]

    changed = False
    di = plan["direct_idx"]
    doms = list(rules[di].get("domain") or [])

    if plan["has_category"]:
        doms.remove(FORBIDDEN_GEOSITE)
        log.append(f"removed forbidden {FORBIDDEN_GEOSITE} from R{di}")
        changed = True

    for p in plan["remove_regexp"]:
        doms.remove(p)
        log.append(f"removed {p} from R{di}")
        changed = True

    if plan["add_geosite"]:
        doms.insert(0, ADD_GEOSITE)
        log.append(f"added {ADD_GEOSITE} to R{di}")
        changed = True

    rules[di]["domain"] = doms

    n = strip_degenerate_routing_rules(rules)
    if n:
        log.append(f"stripped {n} degenerate rule(s)")
        changed = True

    return changed, log


def patch_template(c: PanelClient, tpl: dict, template_uuid: str) -> None:
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        raise RuntimeError(f"PATCH template HTTP {code}: {body!s}"[:500])


def dump_rules(rules: list[dict]) -> None:
    for i, r in enumerate(rules):
        tag = r.get("outboundTag") or r.get("balancerTag") or "?"
        doms = r.get("domain") or []
        markers = [d for d in doms if str(d).startswith(("geosite:", "regexp:"))]
        extra = f" markers={markers[:6]}" if markers else ""
        print(f"  R{i}: {tag} domain={len(doms)}{extra}")


def save_snapshot(tpl_json: dict, prefix: str) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / f"{prefix}-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl_json, ensure_ascii=False, indent=2), encoding="utf-8")
    return snap


def rollback_from_snapshot(c: PanelClient, snap_path: Path, template_uuid: str) -> int:
    raw = json.loads(snap_path.read_text(encoding="utf-8"))
    doc = raw.get("templateJson") or raw.get("response", {}).get("templateJson") or raw
    tpl = fetch_template(c, template_uuid)
    tpl["templateJson"] = doc
    patch_template(c, tpl, template_uuid)
    after_template_patch("rollback_regexp_to_geosite_ru")
    print(f"ROLLBACK OK from {snap_path}")
    return 0


def verify_post_patch(rules: list[dict]) -> list[str]:
    errs: list[str] = []
    plan = plan_patch(rules)
    if plan.get("remove_regexp"):
        errs.append(f"regexp still present: {plan.get('remove_regexp')}")
    if not plan.get("has_geosite_ru") and plan.get("add_geosite"):
        errs.append(f"missing {ADD_GEOSITE}")
    di = find_direct_ru_rule_idx(rules)
    if di >= 0:
        doms = rules[di].get("domain") or []
        if FORBIDDEN_GEOSITE in doms:
            errs.append(FORBIDDEN_GEOSITE)
    if di >= 0 and find_proxy_pre_rule_idx(rules, di) < 0:
        errs.append("proxy pre-rule missing after patch")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", metavar="SNAPSHOT.json")
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    ap.add_argument("--no-sub-notify", action="store_true")
    args = ap.parse_args()

    c = PanelClient()
    if args.rollback:
        return rollback_from_snapshot(c, Path(args.rollback), args.template_uuid)

    tpl = fetch_template(c, args.template_uuid)
    rules = tpl["templateJson"]["routing"]["rules"]

    print("BEFORE:")
    dump_rules(rules)
    plan = plan_patch(rules)
    print(f"plan: {json.dumps({k: v for k, v in plan.items() if k != 'error'}, ensure_ascii=False)}")

    dup = copy.deepcopy(rules)
    changed, log = apply_patch(dup)
    for line in log:
        print(line)

    if not changed:
        if any(line.startswith("FATAL") for line in log):
            return 1
        return 0

    print("\nAFTER (dry-run preview):")
    dump_rules(dup)
    errs = verify_post_patch(dup)
    if errs:
        for e in errs:
            print(f"VERIFY FAIL: {e}")
        return 1

    if not args.apply:
        print("\nDry-run only. Apply with:")
        print("  python ops/patch_routing_regexp_to_geosite_ru.py --apply")
        return 0

    snap = save_snapshot(tpl["templateJson"], "template-before-regexp-to-geosite-ru")
    print(f"snapshot: {snap}")

    ok, log2 = apply_patch(rules)
    if not ok:
        print("\n".join(log2))
        return 1
    patch_template(c, tpl, args.template_uuid)

    re_tpl = fetch_template(c, args.template_uuid)
    re_rules = re_tpl["templateJson"]["routing"]["rules"]
    errs = verify_post_patch(re_rules)
    if errs:
        print("POST-PATCH VERIFY FAILED — rollback with:")
        print(f"  python ops/patch_routing_regexp_to_geosite_ru.py --rollback {snap}")
        for e in errs:
            print(f"  {e}")
        return 1

    if not args.no_sub_notify:
        after_template_patch("patch_routing_regexp_to_geosite_ru")

    print("PATCH OK — users should refresh subscription in Happ")
    print(f"rollback: python ops/patch_routing_regexp_to_geosite_ru.py --rollback {snap}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
