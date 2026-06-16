#!/usr/bin/env python3
"""P1-PRO-SUB-DEAD-OUTBOUND-01: keep injectHosts aligned with connected panel nodes.

Removes host UUIDs tied to disconnected/disabled nodes so Happ sub stops advertising
dead LV/NL paths. Does not change routing rules or balancers (E8).

SCRIPT-MIGRATE-INJECTHOSTS-SYNC-001:
  Dry-run is default. Any live apply must pass ops/vpn_production_guardrails.py
  (owner approval, rollback snapshot, explicit mode, capacity minimums).
  Cron ``--apply`` without guarded flags fails closed — no silent injectHosts collapse.
  Transient node disconnect must not shrink the pool without approved degrade/incident.

Usage:
    python ops/sync_injecthosts_connected.py
    python ops/sync_injecthosts_connected.py --json
    python ops/sync_injecthosts_connected.py --apply --mode incident \\
        --incident-ttl-minutes 60 --owner-approved
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import os
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

from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402
from trim_injecthosts_no_xhttp import is_xhttp_host  # noqa: E402
from validate_vpn_node_registry import DEFAULT_REGISTRY  # noqa: E402
from vpn_apply_guard import owner_approval_present, print_guardrail_banner  # noqa: E402
from vpn_node_selector import load_validated_registry  # noqa: E402
from vpn_production_guardrails import (  # noqa: E402
    APPLY_MODES,
    MODE_DEGRADE,
    MODE_DRY_RUN,
    MODE_INCIDENT,
    MODE_MANUAL_EMERGENCY,
    MODE_SCALE,
    CapacityState,
    GuardrailConfig,
    GuardrailResult,
    capacity_reduces,
    capacity_state_from_nodes,
    evaluate_guardrail,
)

SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
DEFAULT_MIN_INJECT = int(os.environ.get("SYNC_INJECTHOSTS_MIN", "3"))

STATUS_DRY_RUN = "DRY_RUN"
STATUS_APPLY_BLOCKED = "APPLY_BLOCKED"
STATUS_APPLY_ALLOWED = "APPLY_ALLOWED"

HOST_ROLE_LV = "lv_direct"
HOST_ROLE_NL = "nl_direct"
HOST_ROLE_RELAY = "relay"
HOST_ROLE_RELAY_NL = "relay_nl"
HOST_ROLE_XHTTP = "xhttp"
HOST_ROLE_UNKNOWN = "unknown"


def host_node_connected(host: dict, nodes_by_uuid: dict[str, dict]) -> tuple[bool, str]:
    if is_xhttp_host(host):
        return False, "xhttp"
    node_ids = host.get("nodes") or []
    if not node_ids:
        return False, "no node"
    node = nodes_by_uuid.get(str(node_ids[0]), {})
    if node.get("isDisabled"):
        return False, "node disabled"
    if not node.get("isConnected"):
        return False, f"node down ({node.get('name') or '?'})"
    return True, "ok"


def compute_connected_inject(
    hosts: list[dict], nodes: list[dict], current: list[str]
) -> tuple[list[str], list[str]]:
    nodes_by_uuid = {n["uuid"]: n for n in nodes}
    host_by_uuid = {str(h.get("uuid")): h for h in hosts if h.get("uuid")}
    log: list[str] = []
    new_vals: list[str] = []
    for uid in current:
        h = host_by_uuid.get(uid)
        if not h:
            log.append(f"  drop {uid[:8]}… (host missing in panel)")
            continue
        ok, reason = host_node_connected(h, nodes_by_uuid)
        if ok:
            new_vals.append(uid)
        else:
            log.append(f"  drop {uid[:8]}… ({reason})")
    return new_vals, log


def classify_inject_host(
    host: dict, nodes_by_uuid: dict[str, dict] | None = None
) -> str:
    if is_xhttp_host(host):
        return HOST_ROLE_XHTTP
    remark = str(host.get("remark") or "").lower()
    try:
        port = int(host.get("port") or host.get("inboundPort") or 0)
    except (TypeError, ValueError):
        port = 0
    if "nl" in remark and (port == 9443 or "9443" in remark):
        return HOST_ROLE_RELAY_NL
    if "relay" in remark:
        return HOST_ROLE_RELAY
    if "nl" in remark:
        return HOST_ROLE_NL
    if "lv" in remark or "direct" in remark:
        return HOST_ROLE_LV
    node_ids = host.get("nodes") or []
    if node_ids and nodes_by_uuid:
        node = nodes_by_uuid.get(str(node_ids[0]), {})
        name = str(node.get("name") or "").lower()
        if "relay" in name:
            return HOST_ROLE_RELAY
        if "nl" in name:
            return HOST_ROLE_NL
        if "lv" in name:
            return HOST_ROLE_LV
    return HOST_ROLE_UNKNOWN


def relay_ip_count_from_inject(
    hosts_by_uuid: dict[str, dict],
    inject_uuids: list[str],
    nodes_by_uuid: dict[str, dict] | None = None,
) -> int:
    addrs: set[str] = set()
    for uid in inject_uuids:
        h = hosts_by_uuid.get(uid)
        if not h:
            continue
        role = classify_inject_host(h, nodes_by_uuid)
        if role in (HOST_ROLE_RELAY, HOST_ROLE_RELAY_NL):
            addr = str(h.get("address") or h.get("host") or "")
            if addr:
                addrs.add(addr)
    return len(addrs)


def geo_count_from_inject(
    hosts_by_uuid: dict[str, dict],
    inject_uuids: list[str],
    nodes_by_uuid: dict[str, dict] | None = None,
) -> int:
    geos: set[str] = set()
    for uid in inject_uuids:
        h = hosts_by_uuid.get(uid)
        if not h:
            continue
        role = classify_inject_host(h, nodes_by_uuid)
        if role == HOST_ROLE_NL:
            geos.add("NL")
        elif role == HOST_ROLE_RELAY_NL:
            geos.add("NL")
        elif role in (HOST_ROLE_LV, HOST_ROLE_RELAY):
            geos.add("LV")
    return len(geos)


def is_relay_only_inject(
    hosts_by_uuid: dict[str, dict],
    inject_uuids: list[str],
    nodes_by_uuid: dict[str, dict] | None = None,
) -> bool:
    if not inject_uuids:
        return False
    has_relay = False
    for uid in inject_uuids:
        h = hosts_by_uuid.get(uid)
        if not h:
            return False
        role = classify_inject_host(h, nodes_by_uuid)
        if role in (HOST_ROLE_LV, HOST_ROLE_NL):
            return False
        if role == HOST_ROLE_UNKNOWN:
            return False
        if role in (HOST_ROLE_RELAY, HOST_ROLE_RELAY_NL):
            has_relay = True
    return has_relay


def inject_proxy_tags(n: int) -> frozenset[str]:
    if n <= 0:
        return frozenset()
    tags = {"proxy"}
    for i in range(2, n + 1):
        tags.add(f"proxy-{i}")
    return frozenset(tags)


def verify_inject_uuid_selector_consistency(
    doc: dict,
    inject_uuids: list[str],
    hosts_by_uuid: dict[str, dict],
) -> list[str]:
    """UUID ↔ host ↔ selector consistency. Count-only checks are insufficient."""
    errors: list[str] = []
    n = len(inject_uuids)
    allowed_tags = inject_proxy_tags(n)

    for uid in inject_uuids:
        if uid not in hosts_by_uuid:
            errors.append(f"inject UUID {uid[:8]}… has no panel host record")

    balancers = (doc.get("routing") or {}).get("balancers") or []
    for bal in balancers:
        btag = str(bal.get("tag") or "")
        for sel_tag in bal.get("selector") or []:
            st = str(sel_tag)
            if not st.startswith("proxy"):
                continue
            if st not in allowed_tags:
                errors.append(
                    f"balancer {btag} references {st} but injectHosts has only "
                    f"{n} slots (count-only OK insufficient)"
                )
    return errors


def _canary_nodes_in_inject(
    registry_nodes: list[dict],
    hosts_by_uuid: dict[str, dict],
    inject_uuids: list[str],
    nodes_by_uuid: dict[str, dict],
) -> frozenset[str]:
    """Registry canary node_ids still represented in injectHosts."""
    canary_ids = {
        str(n.get("node_id"))
        for n in registry_nodes
        if isinstance(n, dict) and n.get("status") == "canary" and n.get("node_id")
    }
    if not canary_ids:
        return frozenset()
    present: set[str] = set()
    for uid in inject_uuids:
        h = hosts_by_uuid.get(uid)
        if not h:
            continue
        for node_uid in h.get("nodes") or []:
            pn = nodes_by_uuid.get(str(node_uid), {})
            pname = str(pn.get("name") or "").lower()
            for cid in canary_ids:
                key = cid.replace("-", "").lower()
                if key in pname.replace("-", "") or cid.lower() in pname:
                    present.add(cid)
    return frozenset(present)


def build_inject_sync_capacity_state(
    registry_nodes: list[dict],
    hosts: list[dict],
    panel_nodes: list[dict],
    inject_uuids: list[str],
) -> CapacityState | None:
    if not registry_nodes:
        return None
    hosts_by_uuid = {str(h.get("uuid")): h for h in hosts if h.get("uuid")}
    nodes_by_uuid = {str(n.get("uuid")): n for n in panel_nodes if n.get("uuid")}
    base = capacity_state_from_nodes(registry_nodes)
    canary_ids = _canary_nodes_in_inject(
        registry_nodes, hosts_by_uuid, inject_uuids, nodes_by_uuid
    )
    return CapacityState(
        delivery_path_nodes=base.delivery_path_nodes,
        production_capacity_nodes=base.production_capacity_nodes,
        relay_ips=relay_ip_count_from_inject(hosts_by_uuid, inject_uuids, nodes_by_uuid),
        geos=geo_count_from_inject(hosts_by_uuid, inject_uuids, nodes_by_uuid),
        selector_total_paths=len(inject_uuids),
        selector_relay_only=is_relay_only_inject(hosts_by_uuid, inject_uuids, nodes_by_uuid),
        canary_node_ids=canary_ids,
        unknown_status_in_capacity=base.unknown_status_in_capacity,
    )


def resolve_apply_mode(
    *,
    applying: bool,
    mode_arg: str | None,
    reduces_capacity: bool,
) -> tuple[str, list[str]]:
    if not applying:
        return MODE_DRY_RUN, []
    blockers: list[str] = []
    if not mode_arg:
        if reduces_capacity:
            blockers.append(
                "injecthosts sync: --apply with capacity reduction requires "
                "--mode degrade|incident|manual_emergency"
            )
            return MODE_DRY_RUN, blockers
        return MODE_SCALE, []
    if mode_arg == MODE_DRY_RUN:
        blockers.append("injecthosts sync: --apply cannot use --mode dry_run")
        return MODE_DRY_RUN, blockers
    if mode_arg not in APPLY_MODES:
        blockers.append(f"injecthosts sync: unknown apply mode {mode_arg!r}")
        return MODE_DRY_RUN, blockers
    return mode_arg, blockers


def evaluate_inject_sync_apply_guard(
    *,
    registry_nodes: list[dict],
    hosts: list[dict],
    panel_nodes: list[dict],
    doc: dict,
    cur_uuids: list[str],
    new_uuids: list[str],
    mode: str,
    owner_approved: bool,
    rollback_snapshot_present: bool,
    incident_ttl_minutes: int | None = None,
    min_inject: int = DEFAULT_MIN_INJECT,
    config: GuardrailConfig | None = None,
) -> GuardrailResult:
    before = build_inject_sync_capacity_state(registry_nodes, hosts, panel_nodes, cur_uuids)
    after = build_inject_sync_capacity_state(registry_nodes, hosts, panel_nodes, new_uuids)
    if before is None or after is None:
        return GuardrailResult(
            allowed=False,
            mode=mode,
            is_live_apply=mode in APPLY_MODES,
            blockers=["guardrail: cannot build before/after capacity state (registry missing)"],
            summary="apply blocked: capacity state unavailable",
        )

    hosts_by_uuid = {str(h.get("uuid")): h for h in hosts if h.get("uuid")}
    pre_blockers: list[str] = []
    if len(new_uuids) < min_inject:
        pre_blockers.append(
            f"injecthosts sync: would leave {len(new_uuids)} injectHosts "
            f"(min {min_inject}) — use lv_node_down_nl_failover for full LV outage"
        )
    for err in verify_inject_uuid_selector_consistency(doc, new_uuids, hosts_by_uuid):
        pre_blockers.append(f"consistency: {err}")

    result = evaluate_guardrail(
        mode=mode,
        before=before,
        after=after,
        owner_approved=owner_approved,
        rollback_snapshot_present=rollback_snapshot_present,
        incident_ttl_minutes=incident_ttl_minutes,
        config=config,
    )
    if pre_blockers:
        result.blockers = pre_blockers + result.blockers
        result.allowed = not result.blockers
        result.summary = (
            f"{result.summary}; pre_blockers={len(pre_blockers)} allowed={result.allowed}"
        )
    return result


def format_inject_sync_result(
    *,
    status: str,
    guard: GuardrailResult,
    cur_count: int,
    new_count: int,
    changed: bool,
    diagnostic_log: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "injectHosts_before": cur_count,
        "injectHosts_after": new_count,
        "changed": changed,
        "guardrail": guard.to_dict(),
        "diagnostic_log": diagnostic_log,
    }


def gate_baseline() -> int:
    py = sys.executable
    for script, label in (
        ("verify_vpn_balancer_profile.py", "verify_vpn_balancer_profile"),
        ("probe_subscription.py", "probe_subscription"),
    ):
        p = _OPS / script
        if not p.is_file():
            continue
        print(f"\n--- gate: {label} ---")
        r = subprocess.run([py, str(p)], cwd=ROOT)
        if r.returncode != 0 and script == "verify_vpn_balancer_profile.py":
            return 1
    print("\nGATE_INJECTHOSTS_SYNC_OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    ap.add_argument(
        "--mode",
        choices=sorted(APPLY_MODES | {MODE_DRY_RUN}),
        help="Apply mode (required for capacity-reducing --apply)",
    )
    ap.add_argument("--incident-ttl-minutes", type=int, default=None)
    ap.add_argument("--owner-approved", action="store_true")
    ap.add_argument("--rollback-snapshot", type=Path, default=None)
    ap.add_argument("--guardrail-min-delivery-paths", type=int, default=2)
    ap.add_argument("--guardrail-min-relay-ips", type=int, default=2)
    ap.add_argument("--guardrail-min-geos", type=int, default=None)
    ap.add_argument("--min-inject", type=int, default=DEFAULT_MIN_INJECT)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    print_guardrail_banner(
        "sync_injecthosts_connected", capacity_reducing=True, cron_managed=True
    )

    try:
        registry = load_validated_registry(args.registry)
    except ValueError as exc:
        print(f"ERROR: registry: {exc}", file=sys.stderr)
        return 1
    registry_nodes = [n for n in (registry.get("nodes") or []) if isinstance(n, dict)]

    guard_cfg = GuardrailConfig(
        minimum_delivery_paths=args.guardrail_min_delivery_paths,
        minimum_relay_ips=args.guardrail_min_relay_ips,
        minimum_geos=args.guardrail_min_geos,
    )

    c = PanelClient(timeout=120)
    nodes = c.get_or_raise("/api/nodes")["response"]
    hosts = c.get_or_raise("/api/hosts")["response"]
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]
    cur = list(doc["remnawave"]["injectHosts"][0]["selector"].get("values") or [])
    new_vals, log = compute_connected_inject(hosts, nodes, cur)
    diagnostic_log = list(log)

    print(f"injectHosts: {len(cur)} -> {len(new_vals)}")
    for ln in log:
        print(ln)

    before_cap = build_inject_sync_capacity_state(registry_nodes, hosts, nodes, cur)
    after_cap = build_inject_sync_capacity_state(registry_nodes, hosts, nodes, new_vals)
    reduces = (
        before_cap is not None
        and after_cap is not None
        and capacity_reduces(before_cap, after_cap)
    )

    apply_mode, mode_blockers = resolve_apply_mode(
        applying=args.apply,
        mode_arg=args.mode,
        reduces_capacity=reduces,
    )

    if new_vals == cur:
        print("no change")
        guard = evaluate_inject_sync_apply_guard(
            registry_nodes=registry_nodes,
            hosts=hosts,
            panel_nodes=nodes,
            doc=doc,
            cur_uuids=cur,
            new_uuids=new_vals,
            mode=MODE_DRY_RUN,
            owner_approved=False,
            rollback_snapshot_present=False,
            min_inject=args.min_inject,
            config=guard_cfg,
        )
        if args.json_out:
            print(
                json.dumps(
                    format_inject_sync_result(
                        status=STATUS_DRY_RUN,
                        guard=guard,
                        cur_count=len(cur),
                        new_count=len(new_vals),
                        changed=False,
                        diagnostic_log=diagnostic_log,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        if args.gate:
            return gate_baseline()
        return 0

    if not args.apply:
        guard = evaluate_inject_sync_apply_guard(
            registry_nodes=registry_nodes,
            hosts=hosts,
            panel_nodes=nodes,
            doc=doc,
            cur_uuids=cur,
            new_uuids=new_vals,
            mode=MODE_DRY_RUN,
            owner_approved=False,
            rollback_snapshot_present=False,
            min_inject=args.min_inject,
            config=guard_cfg,
        )
        payload = format_inject_sync_result(
            status=STATUS_DRY_RUN,
            guard=guard,
            cur_count=len(cur),
            new_count=len(new_vals),
            changed=True,
            diagnostic_log=diagnostic_log,
        )
        if args.json_out:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"\nstatus: {STATUS_DRY_RUN}")
            print(guard.summary)
            if guard.blockers:
                print("guardrail blockers (would block apply):")
                for b in guard.blockers:
                    print(f"  - {b}")
            print(
                "\nDry-run. Guarded apply example:\n"
                "  python ops/sync_injecthosts_connected.py --apply --mode incident "
                "--incident-ttl-minutes 60 --owner-approved"
            )
        return 0

    # --- guarded apply path ---
    all_blockers = list(mode_blockers)
    if all_blockers:
        guard = GuardrailResult(
            allowed=False,
            mode=apply_mode,
            is_live_apply=True,
            blockers=all_blockers,
            summary="apply blocked: mode resolution failed",
        )
        payload = format_inject_sync_result(
            status=STATUS_APPLY_BLOCKED,
            guard=guard,
            cur_count=len(cur),
            new_count=len(new_vals),
            changed=True,
            diagnostic_log=diagnostic_log,
        )
        if args.json_out:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"\nstatus: {STATUS_APPLY_BLOCKED}")
            for b in all_blockers:
                print(f"  - {b}")
        return 2

    rollback_path = args.rollback_snapshot
    rollback_present = bool(rollback_path and rollback_path.is_file())
    if not rollback_present:
        snap = SNAPSHOT_DIR / f"template-before-inject-sync-{time.strftime('%Y%m%d_%H%M%S')}.json"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
        rollback_path = snap
        rollback_present = True
        diagnostic_log.append(f"rollback snapshot created: {rollback_path.name}")

    guard = evaluate_inject_sync_apply_guard(
        registry_nodes=registry_nodes,
        hosts=hosts,
        panel_nodes=nodes,
        doc=doc,
        cur_uuids=cur,
        new_uuids=new_vals,
        mode=apply_mode,
        owner_approved=owner_approval_present(args.owner_approved),
        rollback_snapshot_present=rollback_present,
        incident_ttl_minutes=args.incident_ttl_minutes,
        min_inject=args.min_inject,
        config=guard_cfg,
    )

    if not guard.allowed:
        payload = format_inject_sync_result(
            status=STATUS_APPLY_BLOCKED,
            guard=guard,
            cur_count=len(cur),
            new_count=len(new_vals),
            changed=True,
            diagnostic_log=diagnostic_log,
        )
        if args.json_out:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"\nstatus: {STATUS_APPLY_BLOCKED}")
            print(guard.summary)
            for b in guard.blockers:
                print(f"  - {b}")
        return 2

    if args.gate:
        rc = gate_baseline()
        if rc != 0:
            print("ABORT: pre-apply gate failed", file=sys.stderr)
            return 1

    payload = format_inject_sync_result(
        status=STATUS_APPLY_ALLOWED,
        guard=guard,
        cur_count=len(cur),
        new_count=len(new_vals),
        changed=True,
        diagnostic_log=diagnostic_log,
    )
    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"\nstatus: {STATUS_APPLY_ALLOWED}")
        print(guard.summary)

    doc2 = copy.deepcopy(doc)
    doc2["remnawave"]["injectHosts"][0]["selector"]["values"] = new_vals
    print(f"snapshot: {rollback_path}")

    tpl["templateJson"] = doc2
    minimal: dict[str, Any] = {
        "uuid": tpl.get("uuid") or args.template_uuid,
        "templateJson": tpl["templateJson"],
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    code, body = c.patch("/api/subscription-templates", body=minimal)
    if code not in (200, 201, 204):
        print(f"FAIL PATCH HTTP {code}: {str(body)[:500]}", file=sys.stderr)
        return 1

    after_template_patch("sync_injecthosts_connected", push_ams=True)
    print("Applied injectHosts sync (gen+1).")
    if args.gate:
        return gate_baseline()
    print("INJECTHOSTS_CONNECTED_SYNC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
