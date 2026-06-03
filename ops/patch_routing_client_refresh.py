#!/usr/bin/env python3
"""Fix iOS Xray clients: routing works after subscription refresh only.

1. Template: replace ``geoip:private`` with RFC1918/link-local CIDRs (no PRIVATE in geoip.dat).
2. Subscription response rules: Streisand + Hiddify → XRAY_JSON (like Happ), not base64-only.

After ``--apply``: users pull subscription and reconnect — no manual geo file update.

Usage:
    python ops/patch_routing_client_refresh.py
    python ops/patch_routing_client_refresh.py --apply
    python ops/patch_routing_client_refresh.py --apply --template-only
    python ops/patch_routing_client_refresh.py --apply --rules-only
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
from routing_geo_common import (  # noqa: E402
    expand_geoip_private,
    routing_rules_use_geoip_private,
)
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

# Insert before fallback (XRAY_BASE64). UA patterns match Remnawave Happ rule style.
# Match Remnawave Happ rule style (^/[Hh]app) — inline (?i) is not reliable in panel REGEX.
XRAY_JSON_CLIENT_RULES = (
    ("Streisand (iOS)", r"^[Ss]treisand"),
    ("Hiddify (iOS/Android)", r"^[Hh]iddify"),
)


def patch_template_routing(doc: dict) -> tuple[bool, list[str]]:
    rules = doc.setdefault("routing", {}).setdefault("rules", [])
    log: list[str] = []
    changed = False
    for i, rule in enumerate(rules):
        new_ips, rule_changed = expand_geoip_private(list(rule.get("ip") or []))
        if rule_changed:
            rule["ip"] = new_ips
            tag = rule.get("outboundTag") or rule.get("balancerTag") or "?"
            log.append(f"R{i}: geoip:private -> {len(new_ips)} CIDRs ({tag})")
            changed = True
    if not changed and routing_rules_use_geoip_private(rules):
        log.append("WARN: geoip:private still present after patch attempt")
    elif not changed:
        log.append("OK: template has no geoip:private")
    return changed, log


def _happ_xray_json_template(rules: list[dict]) -> dict | None:
    for r in rules:
        if r.get("responseType") != "XRAY_JSON":
            continue
        for c in r.get("conditions") or []:
            val = str(c.get("value") or "")
            if "happ" in val.lower():
                return r
    for r in rules:
        if r.get("responseType") == "XRAY_JSON":
            return r
    return None


def _rule_matches_ua_pattern(rule: dict, pattern: str) -> bool:
    for c in rule.get("conditions") or []:
        if (c.get("headerName") or "").lower() != "user-agent":
            continue
        if str(c.get("value") or "") == pattern:
            return True
    return False


def _fallback_index(rules: list[dict]) -> int:
    for i, r in enumerate(rules):
        if r.get("responseType") == "XRAY_BASE64":
            return i
    for i, r in enumerate(rules):
        if not r.get("conditions"):
            return i
    return len(rules)


def _client_rule_from_template(template: dict, name: str, ua_pattern: str) -> dict:
    rule = copy.deepcopy(template)
    rule["name"] = name
    rule["enabled"] = True
    rule["responseType"] = "XRAY_JSON"
    rule.pop("uuid", None)
    for c in rule.get("conditions") or []:
        if (c.get("headerName") or "").lower() == "user-agent":
            c["value"] = ua_pattern
    if not rule.get("conditions"):
        rule["operator"] = "AND"
        rule["conditions"] = [
            {
                "headerName": "user-agent",
                "operator": "REGEX",
                "value": ua_pattern,
                "caseSensitive": False,
            }
        ]
    return rule


def _response_rules_list(settings: dict) -> tuple[dict, list[dict]]:
    """Return (container, rules list). Remnawave stores {rules, version}."""
    container = settings.get("responseRules")
    if isinstance(container, dict):
        return container, list(container.get("rules") or [])
    if isinstance(container, list):
        return {"rules": container}, list(container)
    return {"rules": []}, []


def _rule_by_name(rules: list[dict], name: str) -> dict | None:
    for r in rules:
        if r.get("name") == name:
            return r
    return None


def _set_rule_ua_pattern(rule: dict, pattern: str) -> bool:
    for c in rule.get("conditions") or []:
        if (c.get("headerName") or "").lower() == "user-agent":
            if c.get("value") == pattern:
                return False
            c["value"] = pattern
            c["operator"] = c.get("operator") or "REGEX"
            c["caseSensitive"] = False
            return True
    rule.setdefault("operator", "AND")
    rule.setdefault("conditions", []).append(
        {
            "headerName": "user-agent",
            "operator": "REGEX",
            "value": pattern,
            "caseSensitive": False,
        }
    )
    return True


def patch_response_rules(rules: list[dict]) -> tuple[bool, list[str]]:
    log: list[str] = []
    template = _happ_xray_json_template(rules)
    if template is None:
        template = {
            "enabled": True,
            "operator": "AND",
            "conditions": [
                {
                    "headerName": "user-agent",
                    "operator": "REGEX",
                    "value": r"^[Hh]app",
                    "caseSensitive": False,
                }
            ],
            "responseType": "XRAY_JSON",
        }
        log.append("WARN: no Happ XRAY_JSON rule found; using default condition shape")

    changed = False
    to_add: list[dict] = []
    for name, pattern in XRAY_JSON_CLIENT_RULES:
        existing = _rule_by_name(rules, name)
        if existing:
            if _set_rule_ua_pattern(existing, pattern):
                log.append(f"updated: {name} UA -> {pattern!r}")
                changed = True
            else:
                log.append(f"OK: {name} UA pattern {pattern!r}")
            continue
        if any(_rule_matches_ua_pattern(r, pattern) for r in rules):
            log.append(f"OK: response rule already has UA {pattern!r}")
            continue
        to_add.append(_client_rule_from_template(template, name, pattern))
        log.append(f"will add: {name} -> XRAY_JSON ({pattern})")

    if to_add:
        idx = _fallback_index(rules)
        for offset, rule in enumerate(to_add):
            rules.insert(idx + offset, rule)
        changed = True

    return changed, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--template-only", action="store_true")
    ap.add_argument("--rules-only", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()
    do_template = not args.rules_only
    do_rules = not args.template_only

    c = PanelClient(timeout=120)
    tpl_changed = rules_changed = False

    if do_template:
        tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
        doc = copy.deepcopy(tpl["templateJson"])
        tpl_changed, lines = patch_template_routing(doc)
        for line in lines:
            print(line)
        if tpl_changed and args.apply:
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            snap = SNAPSHOT_DIR / f"template-before-no-geoip-private-{time.strftime('%Y%m%d_%H%M%S')}.json"
            snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
            tpl["templateJson"] = doc
            minimal = {
                "uuid": tpl.get("uuid") or args.template_uuid,
                "templateJson": tpl["templateJson"],
                "viewPosition": tpl.get("viewPosition"),
                "templateType": tpl.get("templateType"),
            }
            code, body = c.patch("/api/subscription-templates", body=minimal)
            if code not in (200, 201, 204):
                print(f"FAIL template PATCH HTTP {code}: {str(body)[:500]}", file=sys.stderr)
                return 1
            after_template_patch("patch_routing_client_refresh")
            print("Applied template: geoip:private -> CIDR")
        elif tpl_changed:
            print("Template dry-run. Apply: --apply")

    if do_rules:
        settings = c.get_or_raise("/api/subscription-settings")["response"]
        rr_container, rules = _response_rules_list(settings)
        rules_changed, lines = patch_response_rules(rules)
        for line in lines:
            print(line)
        if rules_changed and args.apply:
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            snap = SNAPSHOT_DIR / f"subscription-settings-before-xray-json-clients-{time.strftime('%Y%m%d_%H%M%S')}.json"
            snap.write_text(json.dumps({"response": settings}, ensure_ascii=False, indent=2), encoding="utf-8")
            payload = copy.deepcopy(settings)
            rr_out = copy.deepcopy(rr_container)
            rr_out["rules"] = rules
            payload["responseRules"] = rr_out
            code, body = c.patch("/api/subscription-settings", body=payload)
            if code not in (200, 201, 204):
                print(f"FAIL settings PATCH HTTP {code}: {str(body)[:500]}", file=sys.stderr)
                return 1
            print("Applied subscription response rules (Streisand/Hiddify -> XRAY_JSON)")
        elif rules_changed:
            print("Response rules dry-run. Apply: --apply")

    if not tpl_changed and not rules_changed:
        print("Nothing to change.")
        return 0
    if not args.apply:
        print("\nDry-run complete. Apply: python ops/patch_routing_client_refresh.py --apply")
        return 0
    print("Done. Users: refresh subscription in the app, then reconnect VPN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
