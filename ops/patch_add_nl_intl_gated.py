#!/usr/bin/env python3
"""VPN-AUD-220: add NL direct :443 to injectHosts + Intl_Direct only (gated by RU probe).

Safe (no gen=33/45/132 footguns):
  - Runs NL reachability probe from RU before any PATCH
  - NL only in Intl_Direct (+ catch-all on Intl) — never Super/LV direct pool
  - Keeps all 6 relay paths; appends 4 NL hosts (proxy-7..10)
  - No observatory, no RELAY_DNS, no TG broadcast
  - pre-verify + post-verify VPN_BALANCER_PROFILE_OK

Usage:
    python ops/patch_add_nl_intl_gated.py
    python ops/patch_add_nl_intl_gated.py --apply
    python ops/patch_add_nl_intl_gated.py --apply --skip-probe  # emergency only
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
    NL_DIRECT_SELECTOR,
    RELAY6_SELECTOR,
    allowed_relay_only_selectors,
    is_relay_nl_intl_profile,
    is_relay_only_profile,
    is_stealth_split_profile,
)
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
NL_IP = "91.90.192.17"
NL_PORT = 443
INTL_TAG = INTL_BALANCER_TAG


def _nl_already_in_inject(doc: dict, nl_uuids: list[str]) -> bool:
    values = [
        str(x)
        for x in (doc.get("remnawave", {}).get("injectHosts") or [{}])[0]
        .get("selector", {})
        .get("values")
        or []
    ]
    return bool(nl_uuids) and all(uid in values for uid in nl_uuids)


def _intl_has_nl_selector(doc: dict) -> bool:
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    intl_b = balancers.get(INTL_BALANCER_TAG)
    if not intl_b:
        return False
    sel = list(intl_b.get("selector") or [])
    return all(tag in sel for tag in NL_DIRECT_SELECTOR)


def vpn_aud_220_satisfied(doc: dict, nl_uuids: list[str]) -> bool:
    """True when NL direct :443 is in injectHosts and Intl pool (incl. stealth split)."""
    if not _nl_already_in_inject(doc, nl_uuids):
        return False
    if is_relay_nl_intl_profile(doc):
        return True
    if is_stealth_split_profile(doc) and _intl_has_nl_selector(doc):
        return True
    return False


def _nl_host_uuids(c: PanelClient) -> list[str]:
    hosts = c.get_or_raise("/api/hosts")["response"]
    nl = [
        h
        for h in hosts
        if str(h.get("address") or "") == NL_IP
        and int(h.get("port") or 0) == NL_PORT
        and "Direct" in (h.get("remark") or "")
        and not h.get("isDisabled")
    ]
    nl.sort(key=lambda x: str(x.get("remark") or ""))
    return [str(h["uuid"]) for h in nl]


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


def _run_nl_probe() -> bool:
    proc = subprocess.run(
        [sys.executable, str(_OPS / "nl_reachability_probe_ru.py")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.rstrip())
    return proc.returncode == 0 and "NL_REACHABILITY_PROBE_RU_OK" in out


def apply_patch(doc: dict, nl_uuids: list[str]) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    if len(nl_uuids) != 4:
        log.append(f"WARN: expected 4 NL UUIDs, got {len(nl_uuids)}")

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = [str(x) for x in (sel.get("values") or [])]
    after = list(before)
    for uid in nl_uuids:
        if uid not in after:
            after.append(uid)
    if after != before:
        sel["values"] = after
        log.append(f"injectHosts {len(before)} -> {len(after)} (+NL direct×{len(nl_uuids)})")
        changed = True

    target_sel = list(INTL_RELAY_NL_SELECTOR)
    balancers = doc.get("routing", {}).get("balancers") or []
    intl_b = next((b for b in balancers if b.get("tag") == INTL_TAG), None)
    if not intl_b:
        log.append(f"missing {INTL_TAG}")
        return False, log
    old = list(intl_b.get("selector") or [])
    if old != target_sel:
        intl_b["selector"] = target_sel
        log.append(f"{INTL_TAG}: {len(old)} -> {len(target_sel)} paths (relay×6 + NL×4)")
        changed = True
    else:
        log.append(f"OK {INTL_TAG}: already relay+NL selector")

    # Ensure catch-all stays on Intl (not Super/LV)
    rules = doc.get("routing", {}).get("rules") or []
    for r in rules:
        if r.get("network") == "tcp,udp" and r.get("balancerTag") and not r.get("port"):
            if r.get("balancerTag") != INTL_TAG:
                r["balancerTag"] = INTL_TAG
                log.append(f"catch-all → {INTL_TAG}")
                changed = True
            break

    balancers_list = doc.get("routing", {}).get("balancers") or []
    if any(b.get("tag") == "Super_Balancer" for b in balancers_list) or any(
        b.get("tag") == "DNS_LV" for b in balancers_list
    ):
        log.append("ERROR: Super_Balancer/DNS_LV present — abort before NL patch")
        return False, log

    return changed, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--status", action="store_true", help="verify VPN-AUD-220 on live template (panel only)")
    ap.add_argument("--skip-probe", action="store_true", help="emergency only")
    ap.add_argument("--skip-pre-verify", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]
    nl_uuids = _nl_host_uuids(c)

    if args.status:
        if not vpn_aud_220_satisfied(doc, nl_uuids):
            print("FAIL: VPN-AUD-220 not satisfied", file=sys.stderr)
            return 1
        print(f"injectHosts={len(doc['remnawave']['injectHosts'][0]['selector']['values'])} NL_uuids={len(nl_uuids)}")
        if not args.skip_probe:
            print("=== NL reachability probe (RU) ===")
            if not _run_nl_probe():
                return 1
        print("VPN_AUD_220_OK")
        return 0

    print("=== pre-verify ===")
    if not args.skip_pre_verify:
        if not _verify_profile():
            print("ABORT: pre-verify failed", file=sys.stderr)
            return 1

    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]

    if is_relay_nl_intl_profile(doc):
        print("OK: NL already in Intl relay profile — nothing to do")
        return 0
    if vpn_aud_220_satisfied(doc, nl_uuids):
        print("OK: VPN-AUD-220 satisfied (NL×4 :443 in injectHosts + Intl_Direct)")
        print("VPN_AUD_220_OK")
        return 0
    if not is_relay_only_profile(doc):
        print("ABORT: expected relay-only gen>=47 before NL add", file=sys.stderr)
        return 1

    if not args.skip_probe:
        print("=== NL reachability probe (RU) ===")
        if not _run_nl_probe():
            print("ABORT: NL probe failed — not patching (NL stays out of pool)", file=sys.stderr)
            return 1
    else:
        print("WARN: --skip-probe")

    print(f"NL host UUIDs ({len(nl_uuids)}):")
    for uid in nl_uuids:
        print(f"  {uid}")

    patched = copy.deepcopy(doc)
    changed, log = apply_patch(patched, nl_uuids)
    for line in log:
        print(line)
    if not changed:
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_add_nl_intl_gated.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-nl-intl-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("patch_add_nl_intl_gated")

    print("=== post-verify ===")
    if not _verify_profile():
        print("FAIL: post-verify — restore from snapshot", file=sys.stderr)
        return 1
    print("Applied NL→Intl only (relay×6+NL×4). Refresh Happ sub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
