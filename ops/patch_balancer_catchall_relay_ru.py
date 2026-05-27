#!/usr/bin/env python3
"""P1-PRO-VPN-STAB-02: catch-all + policy for RU multipath profile.

Sets **Super_Balancer** to ``RU_MULTIPATH_SELECTOR`` (not relay-only SPOF).
Policy uplinkOnly/downlinkOnly 30/30 for bursty UDP. Intl_Direct owned by
``patch_balancer_direct_first_intl.py``.

Observatory intentionally absent (closed-pipe risk on RU — see incident lessons).

Usage:
    python ops/patch_balancer_catchall_relay_ru.py
    python ops/patch_balancer_catchall_relay_ru.py --apply
    python ops/patch_balancer_catchall_relay_ru.py --verify-only
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

from balancer_selectors import (  # noqa: E402
    POLICY_DOWNLINK_ONLY,
    POLICY_UPLINK_ONLY,
    RU_MULTIPATH_SELECTOR,
    verify_ru_multipath_profile,
)
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_TEMPLATE_UUID = site_urls.REMNA_TEMPLATE_UUID

CATCHALL_BALANCER_TAG = "Super_Balancer"
INTL_BALANCER_TAG = "Intl_Direct"
CATCHALL_SELECTOR = list(RU_MULTIPATH_SELECTOR)


def fetch_template(c: PanelClient, template_uuid: str) -> dict:
    return c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]


def _is_catchall_balancer_rule(rule: dict) -> bool:
    return (
        rule.get("balancerTag") in (CATCHALL_BALANCER_TAG, INTL_BALANCER_TAG)
        and bool(rule.get("network"))
        and not rule.get("domain")
        and not rule.get("ip")
    )


def _ensure_balancer(
    balancers: list[dict],
    tag: str,
    selector: list[str],
) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    found = False
    for b in balancers:
        if b.get("tag") != tag:
            continue
        found = True
        if list(b.get("selector") or []) != selector:
            b["selector"] = list(selector)
            log.append(f"{tag} selector -> {len(selector)} paths")
            changed = True
        b.pop("fallbackTag", None)
        if b.get("strategy", {}).get("type") != "random":
            b["strategy"] = {"type": "random"}
            log.append(f"{tag} strategy -> random")
            changed = True
    if not found:
        balancers.append(
            {
                "tag": tag,
                "selector": list(selector),
                "strategy": {"type": "random"},
            }
        )
        log.append(f"added balancer {tag} selector={len(selector)} paths")
        changed = True
    return changed, log


def _relax_policy(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    levels = doc.setdefault("policy", {}).setdefault("levels", {})
    lv0 = levels.setdefault("0", {})
    changed = False
    if lv0.get("uplinkOnly") != POLICY_UPLINK_ONLY:
        lv0["uplinkOnly"] = POLICY_UPLINK_ONLY
        log.append(f"policy uplinkOnly -> {POLICY_UPLINK_ONLY}")
        changed = True
    if lv0.get("downlinkOnly") != POLICY_DOWNLINK_ONLY:
        lv0["downlinkOnly"] = POLICY_DOWNLINK_ONLY
        log.append(f"policy downlinkOnly -> {POLICY_DOWNLINK_ONLY}")
        changed = True
    return changed, log


def apply_patch(doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False

    rules = doc.get("routing", {}).get("rules") or []
    for r in rules:
        if _is_catchall_balancer_rule(r) and r.get("balancerTag") != CATCHALL_BALANCER_TAG:
            r["balancerTag"] = CATCHALL_BALANCER_TAG
            log.append("catch-all rule -> Super_Balancer")
            changed = True

    balancers = doc.setdefault("routing", {}).setdefault("balancers", [])
    c_changed, c_log = _ensure_balancer(
        balancers, CATCHALL_BALANCER_TAG, CATCHALL_SELECTOR
    )
    log.extend(c_log)
    changed |= c_changed

    p_changed, p_log = _relax_policy(doc)
    log.extend(p_log)
    changed |= p_changed

    for key in ("burstObservatory", "observatory"):
        if key in doc:
            log.append(f"WARN: {key} present — run patch_remove_observatory if unintended")
    return changed, log


def verify_template_json(doc: dict) -> list[str]:
    return verify_ru_multipath_profile(doc)


def patch_template(c: PanelClient, tpl: dict, template_uuid: str) -> None:
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        raise RuntimeError(f"PATCH HTTP {code}: {body!s}"[:500])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--template-uuid", default=DEFAULT_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)
    tpl = fetch_template(c, args.template_uuid)
    doc = tpl["templateJson"]

    if args.verify_only:
        errs = verify_template_json(doc)
        if errs:
            print("FAIL:", "; ".join(errs))
            return 1
        print("OK: template matches RU multipath profile")
        return 0

    changed, log = apply_patch(copy.deepcopy(doc))
    for line in log:
        print(line)
    if not changed:
        errs = verify_template_json(doc)
        if errs:
            print("WARN: no patch needed but verify failed:", errs)
            return 1
        print("OK: already on RU multipath profile")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/patch_balancer_catchall_relay_ru.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-catchall-multipath-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Snapshot: {snap}")

    apply_patch(tpl["templateJson"])
    errs = verify_template_json(tpl["templateJson"])
    if errs:
        print("FAIL post-patch (not sending):", errs, file=sys.stderr)
        return 1

    patch_template(c, tpl, args.template_uuid)
    after_template_patch("patch_balancer_catchall_relay_ru")
    print(
        f"Applied: Super_Balancer multipath ({len(CATCHALL_SELECTOR)} paths); policy 30/30"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
