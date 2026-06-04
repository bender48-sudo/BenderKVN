#!/usr/bin/env python3
"""VPN-AUD-279: enable relay-NL :443 hosts + injectHosts + Intl_Direct (stealth split safe).

Stealth (TG/IG) stays relay×6 only. Intl_Direct catch-all → relay×6 + NL×4 + relay-NL×6.

Pre: RELAY_NL_443_POC_OK, stealth split live, vpn_verify_gate, happ_geosite_guard.

Usage:
    python ops/patch_add_relay_nl_443_inject.py
    python ops/patch_add_relay_nl_443_inject.py --apply
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
    INTL_RELAY_NL_443_SELECTOR,
    INTL_RELAY_NL_SELECTOR,
    INTL_STEALTH_BALANCER_TAG,
    RELAY6_SELECTOR,
    is_stealth_split_profile,
    is_stealth_split_relay_nl_443_profile,
)
from panel_client import PanelClient  # noqa: E402
from patch_add_relay_nl_443_hosts import is_relay_nl_443  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
INTL_TAG = INTL_BALANCER_TAG
STEALTH_TAG = INTL_STEALTH_BALANCER_TAG


def _relay_nl_443_uuids(c: PanelClient) -> list[str]:
    hosts = c.get_or_raise("/api/hosts")["response"]
    rows = [h for h in hosts if is_relay_nl_443(h)]
    rows.sort(key=lambda x: (x.get("address") or "", x.get("remark") or ""))
    return [str(h["uuid"]) for h in rows]


def _verify_gate(script: str, token: str, *, via_lv: bool = False) -> bool:
    if via_lv:
        remote = f"set -a; . /etc/bvpn/ru-monitor.env; set +a; python3 /opt/scripts/{script}"
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=25", "bvpn-lv", remote]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    else:
        proc = subprocess.run(
            [sys.executable, str(_OPS / script)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(ROOT),
        )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.rstrip())
    return proc.returncode == 0 and token in out


def _enable_hosts(c: PanelClient, uuids: list[str], *, apply: bool) -> list[str]:
    hosts = {h["uuid"]: h for h in c.get_or_raise("/api/hosts")["response"]}
    log: list[str] = []
    for uid in uuids:
        h = hosts.get(uid)
        if not h:
            log.append(f"WARN missing host {uid[:8]}")
            continue
        if not h.get("isDisabled") and not h.get("isHidden"):
            log.append(f"OK enabled: {h.get('remark')!r}")
            continue
        if not apply:
            log.append(f"dry-run enable: {h.get('remark')!r}")
            continue
        code, body = c.patch(
            "/api/hosts",
            body={"uuid": uid, "isDisabled": False, "isHidden": False},
        )
        if code != 200:
            log.append(f"FAIL enable {uid[:8]} HTTP {code}")
        else:
            log.append(f"enabled: {h.get('remark')!r}")
    return log


def apply_template_patch(doc: dict, relay_nl_uuids: list[str]) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    if len(relay_nl_uuids) != 6:
        log.append(f"WARN: expected 6 relay-NL :443 UUIDs, got {len(relay_nl_uuids)}")

    sel = doc["remnawave"]["injectHosts"][0]["selector"]
    before = [str(x) for x in (sel.get("values") or [])]
    after = list(before)
    for uid in relay_nl_uuids:
        if uid not in after:
            after.append(uid)
    if after != before:
        sel["values"] = after
        log.append(f"injectHosts {len(before)} -> {len(after)} (+relay-NL×{len(relay_nl_uuids)})")
        changed = True
    else:
        log.append(f"OK injectHosts already {len(after)}")

    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    stealth_b = balancers.get(STEALTH_TAG)
    intl_b = balancers.get(INTL_TAG)
    if not stealth_b or not intl_b:
        log.append("ERROR: missing Intl_Stealth or Intl_Direct")
        return False, log

    stealth_sel = list(stealth_b.get("selector") or [])
    if stealth_sel not in (list(RELAY6_SELECTOR),) and stealth_sel not in (
        ["proxy", "proxy-2", "proxy-3", "proxy-4", "proxy-5", "proxy-6"],
    ):
        if stealth_sel != list(RELAY6_SELECTOR):
            log.append(f"WARN Intl_Stealth selector len={len(stealth_sel)} (expect relay×6)")

    want_intl = list(INTL_RELAY_NL_443_SELECTOR)
    old_intl = list(intl_b.get("selector") or [])
    if old_intl != want_intl:
        intl_b["selector"] = want_intl
        log.append(f"{INTL_TAG}: {len(old_intl)} -> {len(want_intl)} (relay×6+NL×4+relay-NL×6)")
        changed = True
    else:
        log.append(f"OK {INTL_TAG}: already {len(want_intl)} paths")

    if any(b.get("tag") == "Super_Balancer" for b in (doc.get("routing") or {}).get("balancers") or []):
        log.append("ERROR: Super_Balancer present — abort")
        return False, log

    return changed, log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-pre-verify", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    relay_uuids = _relay_nl_443_uuids(c)
    if len(relay_uuids) < 6:
        print(f"FAIL: need 6 relay-NL :443 hosts, got {len(relay_uuids)}", file=sys.stderr)
        print("Run: python ops/patch_add_relay_nl_443_hosts.py --apply", file=sys.stderr)
        return 1

    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]

    if is_stealth_split_relay_nl_443_profile(doc):
        print("OK: VPN-AUD-279 already applied (stealth + Intl relay-NL×6)")
        print("VPN_AUD_279_OK")
        return 0

    if not is_stealth_split_profile(doc):
        balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
        intl_sel = list((balancers.get(INTL_TAG) or {}).get("selector") or [])
        if intl_sel != list(INTL_RELAY_NL_SELECTOR):
            print("ABORT: expected stealth split (Intl=relay×6+NL×4)", file=sys.stderr)
            return 1

    print("=== PoC probe ===")
    if not _verify_gate("probe_relay_nl_443_poc.py", "RELAY_NL_443_POC_OK"):
        print("ABORT: PoC probe failed", file=sys.stderr)
        return 1

    if not args.skip_pre_verify:
        print("=== pre-verify (live sub on LV) ===")
        if not _verify_gate("vpn_verify_gate.py", "VPN_VERIFY_GATE_OK", via_lv=True):
            return 1

    for line in _enable_hosts(c, relay_uuids, apply=args.apply):
        print(line)

    patched = copy.deepcopy(doc)
    changed, log = apply_template_patch(patched, relay_uuids)
    for line in log:
        print(line)
    if not changed:
        print("VPN_AUD_279_OK (no template change)")
        return 0

    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_add_relay_nl_443_inject.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-relay-nl-443-inject-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap.name}")

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
    after_template_patch("patch_add_relay_nl_443_inject", push_ams=True)

    print("=== post-verify (LV gate) ===")
    if not _verify_gate("vpn_verify_gate.py", "VPN_VERIFY_GATE_OK", via_lv=True):
        print("FAIL: post-verify — restore snapshot", file=sys.stderr)
        return 1

    print("VPN_AUD_279_OK — relay-NL :443 in inject; notify users to refresh sub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
