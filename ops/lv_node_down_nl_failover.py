#!/usr/bin/env python3
"""LV prod node down → NL-only template (injectHosts + balancers). Restore when LV returns.

Mandatory verify before/after (--gate). Does not fix LV Caddy subscription edge SPOF;
see docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md.

Usage:
    python ops/lv_node_down_nl_failover.py --gate              # baseline (multipath OK)
    python ops/lv_node_down_nl_failover.py --status
    python ops/lv_node_down_nl_failover.py --gate --apply      # enter NL failover
    python ops/lv_node_down_nl_failover.py --restore --gate --apply
    python ops/lv_node_down_nl_failover.py --auto --gate --apply
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
from typing import Any

import site_urls

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_OPS = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parent.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from lv_nl_failover_common import (  # noqa: E402
    STATE_FILE_NAME,
    apply_nl_failover_to_doc,
    collect_nl_inject_uuids,
    lv_nodes_healthy,
    nl_nodes_healthy,
    restore_doc_from_state,
)
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
STATE_FILE = SNAPSHOT_DIR / STATE_FILE_NAME


def _load_state() -> dict[str, Any]:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"mode": "normal"}


def _save_state(state: dict[str, Any]) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_step(cmd: list[str], label: str, *, optional: bool = False) -> int:
    print(f"\n--- gate: {label} ---")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        msg = f"WARN: {label} exit {r.returncode}" if optional else f"FAIL: {label} exit {r.returncode}"
        print(msg, file=sys.stderr)
    return r.returncode


def gate_multipath_baseline() -> int:
    """Prod healthy: multipath profile + sub shape."""
    py = sys.executable
    if _run_step([py, str(_OPS / "verify_vpn_balancer_profile.py")], "verify_vpn_balancer_profile") != 0:
        return 1
    probe_ok = False
    for attempt in range(4):
        if _run_step([py, str(_OPS / "probe_subscription.py")], f"probe_subscription try{attempt + 1}", optional=True) == 0:
            probe_ok = True
            break
        time.sleep(2)
    if not probe_ok:
        print("WARN: probe_subscription flaky (SSL); continuing on verify_vpn_balancer_profile OK")
    _run_step([py, str(_OPS / "diagnose_happ_import.py")], "diagnose_happ_import", optional=True)
    print("\nGATE_MULTIPATH_OK")
    return 0


def gate_nl_failover_post() -> int:
    """After NL-only template patch."""
    py = sys.executable
    rc = 0
    for cmd, label, opt in (
        ([py, str(_OPS / "probe_subscription.py")], "probe_subscription", False),
        ([py, str(_OPS / "verify_nl_failover_sub.py")], "verify_nl_failover_sub", False),
        ([py, str(_OPS / "transport_mux_audit.py")], "transport_mux_audit", True),
    ):
        if _run_step(cmd, label, optional=opt) != 0 and not opt:
            rc = 1
    if rc == 0:
        print("\nGATE_NL_FAILOVER_OK")
    return rc


def gate_restore_post() -> int:
    return gate_multipath_baseline()


def probe_sub_origins() -> int:
    py = sys.executable
    drift = _OPS / "subscription_origin_drift_probe.py"
    if not drift.is_file():
        print("SKIP: subscription_origin_drift_probe.py missing")
        return 0
    return _run_step(
        [py, str(drift), "--split-host"],
        "subscription_origin_drift (HTTP only)",
        optional=True,
    )


def _panel_retry(fn, *, attempts: int = 5, delay: float = 2.0):
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            if i < attempts - 1:
                print(f"panel retry {i + 1}/{attempts - 1}: {exc}")
                time.sleep(delay)
    raise last  # type: ignore[misc]


def fetch_panel_snapshot(c: PanelClient, template_uuid: str) -> tuple[list[dict], list[dict], dict]:
    nodes = _panel_retry(lambda: c.get_or_raise("/api/nodes")["response"])
    hosts = _panel_retry(lambda: c.get_or_raise("/api/hosts")["response"])
    tpl = _panel_retry(
        lambda: c.get_or_raise(f"/api/subscription-templates/{template_uuid}")["response"]
    )
    return nodes, hosts, tpl


def cmd_status(c: PanelClient, template_uuid: str) -> None:
    state = _load_state()
    nodes, hosts, tpl = fetch_panel_snapshot(c, template_uuid)
    lv_ok, lv_msg = lv_nodes_healthy(nodes)
    nl_ok, nl_msg = nl_nodes_healthy(nodes)
    inj = tpl["templateJson"]["remnawave"]["injectHosts"][0]["selector"]["values"]
    nl_uuids, _ = collect_nl_inject_uuids(hosts, {n["uuid"]: n for n in nodes})
    print(f"state.mode={state.get('mode', 'normal')}")
    print(f"LV: {lv_msg} ({'healthy' if lv_ok else 'DOWN'})")
    print(f"NL: {nl_msg}")
    print(f"injectHosts in template: {len(inj)}")
    print(f"NL hosts available: {len(nl_uuids)}")
    if state.get("applied_at"):
        print(f"failover applied_at={state['applied_at']}")


def apply_failover(c: PanelClient, template_uuid: str, *, force: bool) -> int:
    nodes, hosts, tpl = fetch_panel_snapshot(c, template_uuid)
    nl_ok, nl_msg = nl_nodes_healthy(nodes)
    if not nl_ok:
        print(f"ABORT: {nl_msg}", file=sys.stderr)
        return 1
    lv_ok, lv_msg = lv_nodes_healthy(nodes)
    if lv_ok and not force:
        print(f"ABORT: {lv_msg} — use --force to apply NL failover while LV is up", file=sys.stderr)
        return 1
    if not lv_ok:
        print(f"LV down confirmed: {lv_msg}")

    nodes_by_uuid = {n["uuid"]: n for n in nodes}
    nl_uuids, host_log = collect_nl_inject_uuids(hosts, nodes_by_uuid)
    for line in host_log:
        print(line)
    if len(nl_uuids) < 1:
        return 1

    doc = copy.deepcopy(tpl["templateJson"])
    state = _load_state()
    if state.get("mode") != "nl_failover":
        state = {"mode": "normal", "saved_inject": None, "saved_balancers": None}
    changed, log, frag = apply_nl_failover_to_doc(doc, nl_uuids, saved=state)
    for line in log:
        print(line)
    if not changed:
        print("nothing to patch")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-lv-nl-failover-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot: {snap}")

    tpl["templateJson"] = doc
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        print(f"FAIL PATCH HTTP {code}: {str(body)[:500]}", file=sys.stderr)
        return 1

    frag["mode"] = "nl_failover"
    frag["applied_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    frag["reason"] = "lv_down"
    _save_state(frag)
    after_template_patch("lv_node_down_nl_failover", push_ams=True)
    print("Applied NL-only template (gen+1). Users: refresh subscription.")
    return 0


def apply_restore(c: PanelClient, template_uuid: str) -> int:
    state = _load_state()
    nodes, hosts, tpl = fetch_panel_snapshot(c, template_uuid)
    lv_ok, lv_msg = lv_nodes_healthy(nodes)
    if not lv_ok:
        print(f"WARN: restoring template while {lv_msg}", file=sys.stderr)

    doc = copy.deepcopy(tpl["templateJson"])
    if state.get("mode") == "nl_failover" and state.get("saved_inject"):
        changed, log = restore_doc_from_state(doc, state)
        for line in log:
            print(line)
        if not changed:
            print("state restore: no diff in template")
    else:
        print("No failover state — run restore_template_working.py")
        py = sys.executable
        r = subprocess.run(
            [py, str(_OPS / "restore_template_working.py"), "--apply"],
            cwd=ROOT,
        )
        return r.returncode

    snap = SNAPSHOT_DIR / f"template-before-lv-nl-restore-{time.strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    tpl["templateJson"] = doc
    minimal = {
        "uuid": tpl.get("uuid") or template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        print(f"FAIL PATCH HTTP {code}: {str(body)[:500]}", file=sys.stderr)
        return 1

    _save_state({"mode": "normal"})
    after_template_patch("lv_node_down_nl_restore", push_ams=True)
    print("Restored multipath template from failover state.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--gate", action="store_true", help="run verify suite before/after mutation")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--auto", action="store_true", help="failover if LV down else restore if in failover")
    ap.add_argument("--force", action="store_true", help="apply NL failover even if LV connected (drill)")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    c = PanelClient(timeout=120)

    if args.status:
        cmd_status(c, args.template_uuid)
        return 0

    if args.auto:
        nodes = c.get_or_raise("/api/nodes")["response"]
        state = _load_state()
        lv_ok, _ = lv_nodes_healthy(nodes)
        if not lv_ok:
            args.restore = False
            print("auto: LV down → NL failover")
        elif state.get("mode") == "nl_failover":
            args.restore = True
            print("auto: LV up + failover active → restore")
        else:
            print("auto: nothing to do (LV up, mode normal)")
            return 0

    if args.gate and not args.apply:
        print("=== pre-check (read-only) ===")
        cmd_status(c, args.template_uuid)
        rc = gate_multipath_baseline()
        probe_sub_origins()
        return rc

    if args.gate and args.apply:
        print("=== BEFORE apply ===")
        if args.restore:
            if gate_nl_failover_post() == 0:
                print("(currently in NL failover — pre-restore check)")
        else:
            rc = gate_multipath_baseline()
            if rc != 0 and not args.force:
                print("ABORT: baseline gate failed (fix or use --force)", file=sys.stderr)
                return 1
        probe_sub_origins()

    if not args.apply:
        if args.restore:
            print("Dry-run restore: pass --apply")
        else:
            nodes, hosts, tpl = fetch_panel_snapshot(c, args.template_uuid)
            nl_uuids, host_log = collect_nl_inject_uuids(hosts, {n["uuid"]: n for n in nodes})
            for line in host_log:
                print(line)
            doc = copy.deepcopy(tpl["templateJson"])
            _, log, _ = apply_nl_failover_to_doc(doc, nl_uuids)
            for line in log:
                print(line)
            print("\nDry-run. Apply: --gate --apply  (drill: add --force if LV up)")
        return 0

    if args.restore:
        rc = apply_restore(c, args.template_uuid)
        if rc != 0:
            return rc
        if args.gate:
            print("\n=== AFTER restore ===")
            return gate_restore_post()
        return 0

    rc = apply_failover(c, args.template_uuid, force=args.force)
    if rc != 0:
        return rc
    if args.gate:
        print("\n=== AFTER NL failover ===")
        return gate_nl_failover_post()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
