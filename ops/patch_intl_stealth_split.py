#!/usr/bin/env python3
"""VPN-AUD-221: stealth split — TG/Meta via relay-only; catch-all keeps relay+NL.

Safe (no gen=33/45/132 footguns):
  - Intl_Stealth = RELAY6_SELECTOR (rules R1 IP-CIDR + R2 geosite)
  - Intl_Direct = INTL_RELAY_NL_SELECTOR (catch-all speedtest/general)
  - No Super/LV direct, no observatory, no injectHosts change
  - pre-verify + post-verify VPN_BALANCER_PROFILE_OK

Usage:
    python ops/patch_intl_stealth_split.py
    python ops/patch_intl_stealth_split.py --apply
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import subprocess
import sys
import time
from pathlib import Path

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_RELAY_NL_SELECTOR,
    INTL_STEALTH_BALANCER_TAG,
    RELAY6_SELECTOR,
    is_relay_nl_intl_profile,
    is_stealth_split_profile,
)
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"

STEALTH_TAG = INTL_STEALTH_BALANCER_TAG
FAST_TAG = INTL_BALANCER_TAG
INTL_IP_MARKER = "149.154.0.0/16"


def _verify_profile() -> bool:
    proc = subprocess.run(
        [sys.executable, str(_OPS / "verify_vpn_balancer_profile.py")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.rstrip())
    return proc.returncode == 0 and "VPN_BALANCER_PROFILE_OK" in out


def _find_media_rule_indices(rules: list[dict]) -> tuple[int, int]:
    ip_idx = -1
    domain_idx = -1
    for i, r in enumerate(rules):
        if r.get("balancerTag") != FAST_TAG:
            continue
        if r.get("ip") and INTL_IP_MARKER in (r.get("ip") or []):
            ip_idx = i
        elif r.get("domain") and not r.get("ip"):
            domain_idx = i
    if ip_idx < 0:
        for i, r in enumerate(rules):
            if r.get("balancerTag") == FAST_TAG and r.get("ip"):
                ip_idx = i
                break
    if domain_idx < 0:
        for i, r in enumerate(rules):
            if r.get("balancerTag") == FAST_TAG and r.get("domain"):
                domain_idx = i
                break
    return ip_idx, domain_idx


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    routing = doc.setdefault("routing", {})
    balancers: list[dict] = routing.setdefault("balancers", [])
    bal_by_tag = {b.get("tag"): b for b in balancers}

    if bal_by_tag.get("Super_Balancer") or bal_by_tag.get("DNS_LV"):
        log.append("ERROR: Super_Balancer/DNS_LV present — abort")
        return False, log

    stealth_b = bal_by_tag.get(STEALTH_TAG)
    if not stealth_b:
        stealth_b = {"tag": STEALTH_TAG, "selector": list(RELAY6_SELECTOR), "strategy": {"type": "random"}}
        balancers.append(stealth_b)
        log.append(f"added {STEALTH_TAG} relay×{len(RELAY6_SELECTOR)}")
        changed = True
    else:
        old = list(stealth_b.get("selector") or [])
        if old != list(RELAY6_SELECTOR):
            stealth_b["selector"] = list(RELAY6_SELECTOR)
            log.append(f"{STEALTH_TAG}: {len(old)} -> {len(RELAY6_SELECTOR)} paths")
            changed = True
        else:
            log.append(f"OK {STEALTH_TAG}: relay×{len(RELAY6_SELECTOR)}")
    if (stealth_b.get("strategy") or {}).get("type") != "random":
        stealth_b.setdefault("strategy", {})["type"] = "random"
        changed = True

    intl_b = bal_by_tag.get(FAST_TAG)
    if not intl_b:
        log.append(f"ERROR: missing {FAST_TAG}")
        return False, log
    old_fast = list(intl_b.get("selector") or [])
    if old_fast != list(INTL_RELAY_NL_SELECTOR):
        intl_b["selector"] = list(INTL_RELAY_NL_SELECTOR)
        log.append(f"{FAST_TAG}: {len(old_fast)} -> {len(INTL_RELAY_NL_SELECTOR)} paths (catch-all fast pool)")
        changed = True
    else:
        log.append(f"OK {FAST_TAG}: relay+NL catch-all pool")
    if (intl_b.get("strategy") or {}).get("type") != "random":
        intl_b.setdefault("strategy", {})["type"] = "random"
        changed = True

    rules = routing.get("rules") or []
    ip_idx, domain_idx = _find_media_rule_indices(rules)
    if ip_idx < 0 or domain_idx < 0:
        log.append(f"ERROR: media rules not found (ip_idx={ip_idx} domain_idx={domain_idx})")
        return False, log

    for idx, label in ((ip_idx, "IP-CIDR"), (domain_idx, "geosite")):
        if rules[idx].get("balancerTag") != STEALTH_TAG:
            rules[idx]["balancerTag"] = STEALTH_TAG
            log.append(f"rule R{idx} ({label}) -> {STEALTH_TAG}")
            changed = True
        else:
            log.append(f"OK rule R{idx} ({label}) -> {STEALTH_TAG}")

    for r in rules:
        if r.get("network") == "tcp,udp" and r.get("balancerTag") and not r.get("port"):
            if r.get("balancerTag") != FAST_TAG:
                r["balancerTag"] = FAST_TAG
                log.append(f"catch-all -> {FAST_TAG}")
                changed = True
            break

    if doc.get("burstObservatory") or doc.get("observatory"):
        log.append("ERROR: observatory present — abort")
        return False, log

    return changed, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-pre-verify", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    print("=== pre-verify ===")
    if not args.skip_pre_verify:
        if not _verify_profile():
            print("ABORT: pre-verify failed", file=sys.stderr)
            return 1

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]

    if is_stealth_split_profile(doc):
        print("OK: stealth split already applied")
        return 0
    if not is_relay_nl_intl_profile(doc):
        print("ABORT: expected relay+NL Intl profile before stealth split", file=sys.stderr)
        return 1

    patched = copy.deepcopy(doc)
    changed, log = apply_patch(patched)
    for line in log:
        print(line)
    if not changed:
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_intl_stealth_split.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-stealth-split-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    tpl["templateJson"] = patched
    minimal = {
        "uuid": tpl.get("uuid") or args.template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        print(f"FAIL PATCH HTTP {code}: {body!s}"[:400], file=sys.stderr)
        return 1
    after_template_patch("patch_intl_stealth_split")

    print("=== post-verify ===")
    if not _verify_profile():
        print("FAIL: post-verify — restore from snapshot", file=sys.stderr)
        return 1
    print("Applied stealth split: TG/Meta->Intl_Stealth relay×6; catch-all->Intl_Direct relay+NL. Refresh Happ sub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
