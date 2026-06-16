#!/usr/bin/env python3
"""VPN-AUD-310/220: server-side Intl_Direct selector autotrim (relay + NL).

Trims bad paths without gen=33/45/132 footguns:
  - Only Intl_Direct selector — never Super/LV direct, never observatory
  - Relay: trim whole slow relay IP (min 3 relay paths)
  - NL: drop proxy-7..10 from selector if RU probe fails (injectHosts unchanged)
  - Hysteresis: 2 bad probes → trim; 3 OK → restore
  - Both relays dead → no PATCH

SCRIPT-MIGRATE-LATENCY-AUTOTRIM-001:
  Dry-run is default. Any live apply must pass ops/vpn_production_guardrails.py
  (owner approval, rollback snapshot, explicit mode, capacity minimums).
  Cron ``--apply`` without guarded flags fails closed — no silent pool collapse.

Usage:
    python ops/latency_selector_autotrim.py
    python ops/latency_selector_autotrim.py --json
    python ops/latency_selector_autotrim.py --apply --mode incident \\
        --incident-ttl-minutes 60 --owner-approved
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
    NL_DIRECT_SELECTOR,
    RELAY1_SELECTOR,
    RELAY2_SELECTOR,
    RELAY6_SELECTOR,
    RELAY_NL443_SELECTOR,
    allowed_relay_only_selectors,
    is_relay_nl_intl_profile,
    is_relay_only_profile,
    is_stealth_split_profile,
    is_stealth_split_relay_nl_443_profile,
)
from nl_reachability_probe_ru import NL_IP, probe_nl_from_ru  # noqa: E402
from panel_client import PanelClient  # noqa: E402
from relay_latency_probe import RELAY1_IP, RELAY2_IP, RelayIpProbe, probe_relay_ips  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402
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
    capacity_state_from_nodes,
    capacity_reduces,
    evaluate_guardrail,
)

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
STATE_FILE = ROOT / ".secrets" / "latency_selector_state.json"

INTL_TAG = INTL_BALANCER_TAG
MIN_PATHS = 3
SLOW_RATIO = 2.0
RELAY_SLOW_ABS_MS = 80.0
NL_MAX_TCP_MS = 120.0
TRIM_FAIL_STREAK = 2
RESTORE_OK_STREAK = 3

STATUS_DRY_RUN = "DRY_RUN"
STATUS_APPLY_BLOCKED = "APPLY_BLOCKED"
STATUS_APPLY_ALLOWED = "APPLY_ALLOWED"


def relay_ips_for_mode(relay_mode: str) -> int:
    if relay_mode == "full":
        return 2
    if relay_mode in ("relay1_only", "relay2_only"):
        return 1
    return 0


def is_relay_only_pool(relay_mode: str, include_nl: bool, doc: dict) -> bool:
    if include_nl and _inject_has_nl(doc):
        return False
    return relay_mode in ("relay1_only", "relay2_only")


def build_autotrim_capacity_state(
    registry_nodes: list[dict],
    doc: dict,
    relay_mode: str,
    include_nl: bool,
) -> CapacityState | None:
    if not registry_nodes:
        return None
    base = capacity_state_from_nodes(registry_nodes)
    return CapacityState(
        delivery_path_nodes=base.delivery_path_nodes,
        production_capacity_nodes=base.production_capacity_nodes,
        relay_ips=relay_ips_for_mode(relay_mode),
        geos=base.geos,
        selector_total_paths=len(_build_target(relay_mode, include_nl, doc)),
        selector_relay_only=is_relay_only_pool(relay_mode, include_nl, doc),
        canary_node_ids=base.canary_node_ids,
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
                "autotrim: --apply with capacity reduction requires "
                "--mode degrade|incident|manual_emergency"
            )
            return MODE_DRY_RUN, blockers
        return MODE_SCALE, []
    if mode_arg == MODE_DRY_RUN:
        blockers.append("autotrim: --apply cannot use --mode dry_run")
        return MODE_DRY_RUN, blockers
    if mode_arg not in APPLY_MODES:
        blockers.append(f"autotrim: unknown apply mode {mode_arg!r}")
        return MODE_DRY_RUN, blockers
    return mode_arg, blockers


def evaluate_autotrim_apply_guard(
    *,
    registry_nodes: list[dict],
    doc: dict,
    relay_mode_before: str,
    relay_mode_after: str,
    include_nl_before: bool,
    include_nl_after: bool,
    mode: str,
    owner_approved: bool,
    rollback_snapshot_present: bool,
    incident_ttl_minutes: int | None = None,
    config: GuardrailConfig | None = None,
) -> GuardrailResult:
    before = build_autotrim_capacity_state(
        registry_nodes, doc, relay_mode_before, include_nl_before
    )
    after = build_autotrim_capacity_state(
        registry_nodes, doc, relay_mode_after, include_nl_after
    )
    if before is None or after is None:
        return GuardrailResult(
            allowed=False,
            mode=mode,
            is_live_apply=mode in APPLY_MODES,
            blockers=["guardrail: cannot build before/after capacity state (registry missing)"],
            summary="apply blocked: capacity state unavailable",
        )
    return evaluate_guardrail(
        mode=mode,
        before=before,
        after=after,
        owner_approved=owner_approved,
        rollback_snapshot_present=rollback_snapshot_present,
        incident_ttl_minutes=incident_ttl_minutes,
        config=config,
    )


def format_autotrim_result(
    *,
    status: str,
    guard: GuardrailResult,
    relay_mode_before: str,
    relay_mode_after: str,
    include_nl_before: bool,
    include_nl_after: bool,
    changed: bool,
    diagnostic_log: list[str],
) -> dict:
    return {
        "status": status,
        "changed": changed,
        "relay_mode_before": relay_mode_before,
        "relay_mode_after": relay_mode_after,
        "include_nl_before": include_nl_before,
        "include_nl_after": include_nl_after,
        "blockers": guard.blockers,
        "warnings": guard.warnings,
        "guardrail_summary": guard.summary,
        "guardrail_mode": guard.mode,
        "capacity_before": guard.capacity_before,
        "capacity_after": guard.capacity_after,
        "diagnostic_log": diagnostic_log,
    }


def _load_state() -> dict:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "relay_mode": "full",
        "nl_in_selector": True,
        "relay2_slow_streak": 0,
        "relay1_slow_streak": 0,
        "relay2_ok_streak": 0,
        "relay1_ok_streak": 0,
        "nl_fail_streak": 0,
        "nl_ok_streak": 0,
        "last_relay_probe": None,
        "last_nl_probe": None,
        "updated_at": "",
    }


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _probe_by_ip(results: list[RelayIpProbe]) -> dict[str, RelayIpProbe]:
    return {r.ip: r for r in results}


def _inject_has_nl(doc: dict) -> bool:
    n = len(doc.get("remnawave", {}).get("injectHosts", [{}])[0].get("selector", {}).get("values") or [])
    return n >= 10


def _inject_has_relay_nl_443(doc: dict) -> bool:
    n = len(doc.get("remnawave", {}).get("injectHosts", [{}])[0].get("selector", {}).get("values") or [])
    return n >= 16


def _relay_part(mode: str) -> list[str]:
    if mode == "relay1_only":
        return list(RELAY1_SELECTOR)
    if mode == "relay2_only":
        return list(RELAY2_SELECTOR)
    return list(RELAY6_SELECTOR)


def _build_target(relay_mode: str, include_nl: bool, doc: dict) -> list[str]:
    relay_sel = _relay_part(relay_mode)
    nl_part = list(NL_DIRECT_SELECTOR) if include_nl and _inject_has_nl(doc) else []
    if _inject_has_relay_nl_443(doc):
        return relay_sel + nl_part + list(RELAY_NL443_SELECTOR)
    if nl_part:
        return relay_sel + nl_part
    return relay_sel


def _evaluate_relay(probes: dict[str, RelayIpProbe], state: dict) -> tuple[str, list[str]]:
    log: list[str] = []
    r1 = probes.get(RELAY1_IP)
    r2 = probes.get(RELAY2_IP)
    if not r1 or not r2:
        log.append("WARN: missing relay probe — relay mode unchanged")
        return str(state.get("relay_mode") or "full"), log

    for r in (r1, r2):
        label = "relay1" if r.ip == RELAY1_IP else "relay2"
        if r.ok and r.tcp_connect_ms is not None:
            log.append(f"{label} {r.ip} OK tcp={r.tcp_connect_ms}ms")
        else:
            log.append(f"{label} {r.ip} FAIL ({r.error})")

    if not r1.ok and not r2.ok:
        log.append("both relays failed — keep selector")
        return str(state.get("relay_mode") or "full"), log

    if r1.ok and not r2.ok:
        state["relay2_slow_streak"] = int(state.get("relay2_slow_streak", 0)) + 1
        state["relay2_ok_streak"] = 0
        state["relay1_ok_streak"] = int(state.get("relay1_ok_streak", 0)) + 1
        state["relay1_slow_streak"] = 0
        if state["relay2_slow_streak"] >= TRIM_FAIL_STREAK:
            log.append("relay2 fail → relay1_only")
            return "relay1_only", log
        return str(state.get("relay_mode") or "full"), log

    if r2.ok and not r1.ok:
        state["relay1_slow_streak"] = int(state.get("relay1_slow_streak", 0)) + 1
        state["relay1_ok_streak"] = 0
        state["relay2_ok_streak"] = int(state.get("relay2_ok_streak", 0)) + 1
        state["relay2_slow_streak"] = 0
        if state["relay1_slow_streak"] >= TRIM_FAIL_STREAK:
            log.append("relay1 fail → relay2_only")
            return "relay2_only", log
        return str(state.get("relay_mode") or "full"), log

    assert r1.tcp_connect_ms is not None and r2.tcp_connect_ms is not None
    fast_ms = min(r1.tcp_connect_ms, r2.tcp_connect_ms)
    slow_ms = max(r1.tcp_connect_ms, r2.tcp_connect_ms)
    slow_is_r2 = r2.tcp_connect_ms >= r1.tcp_connect_ms
    threshold = max(fast_ms * SLOW_RATIO, RELAY_SLOW_ABS_MS)
    log.append(f"relay fast={fast_ms}ms slow={slow_ms}ms threshold={threshold:.0f}ms")

    if slow_ms > threshold:
        if slow_is_r2:
            state["relay2_slow_streak"] = int(state.get("relay2_slow_streak", 0)) + 1
            state["relay2_ok_streak"] = 0
            state["relay1_ok_streak"] = int(state.get("relay1_ok_streak", 0)) + 1
            state["relay1_slow_streak"] = 0
            if state["relay2_slow_streak"] >= TRIM_FAIL_STREAK:
                log.append("relay2 slow → relay1_only")
                return "relay1_only", log
        else:
            state["relay1_slow_streak"] = int(state.get("relay1_slow_streak", 0)) + 1
            state["relay1_ok_streak"] = 0
            state["relay2_ok_streak"] = int(state.get("relay2_ok_streak", 0)) + 1
            state["relay2_slow_streak"] = 0
            if state["relay1_slow_streak"] >= TRIM_FAIL_STREAK:
                log.append("relay1 slow → relay2_only")
                return "relay2_only", log
        return str(state.get("relay_mode") or "full"), log

    state["relay1_slow_streak"] = 0
    state["relay2_slow_streak"] = 0
    state["relay1_ok_streak"] = int(state.get("relay1_ok_streak", 0)) + 1
    state["relay2_ok_streak"] = int(state.get("relay2_ok_streak", 0)) + 1
    cur = str(state.get("relay_mode") or "full")
    if cur != "full" and state["relay1_ok_streak"] >= RESTORE_OK_STREAK and state["relay2_ok_streak"] >= RESTORE_OK_STREAK:
        log.append(f"relays OK streak ≥{RESTORE_OK_STREAK} → full relay pool")
        state["relay1_ok_streak"] = 0
        state["relay2_ok_streak"] = 0
        return "full", log
    return cur, log


def _evaluate_nl(nl_results: list[RelayIpProbe], state: dict, doc: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    if not _inject_has_nl(doc):
        state["nl_in_selector"] = False
        log.append("NL: not in injectHosts — skip")
        return False, log

    r = nl_results[0] if nl_results else None
    if not r:
        log.append("NL: no probe result — unchanged")
        return bool(state.get("nl_in_selector", True)), log

    ok = r.ok and r.tcp_connect_ms is not None and r.tcp_connect_ms <= NL_MAX_TCP_MS
    if ok:
        log.append(f"NL {NL_IP} OK tcp={r.tcp_connect_ms}ms")
        state["nl_fail_streak"] = 0
        state["nl_ok_streak"] = int(state.get("nl_ok_streak", 0)) + 1
        if not state.get("nl_in_selector", True) and state["nl_ok_streak"] >= RESTORE_OK_STREAK:
            log.append(f"NL OK streak ≥{RESTORE_OK_STREAK} → restore in selector")
            state["nl_ok_streak"] = 0
            return True, log
        return True, log

    reason = r.error or f"tcp={r.tcp_connect_ms}ms"
    log.append(f"NL {NL_IP} FAIL ({reason})")
    state["nl_ok_streak"] = 0
    state["nl_fail_streak"] = int(state.get("nl_fail_streak", 0)) + 1
    if state["nl_fail_streak"] >= TRIM_FAIL_STREAK:
        log.append("NL fail streak → drop from selector (injectHosts kept)")
        return False, log
    return bool(state.get("nl_in_selector", True)), log


def _allowed_target_selector(target_sel: list[str]) -> bool:
    if target_sel in allowed_relay_only_selectors() or target_sel == INTL_RELAY_NL_SELECTOR:
        return True
    nl_tags = [t for t in target_sel if t not in RELAY6_SELECTOR]
    relay_tags = [t for t in target_sel if t in RELAY6_SELECTOR]
    if not nl_tags:
        return True
    return relay_tags in (list(RELAY1_SELECTOR), list(RELAY2_SELECTOR), list(RELAY6_SELECTOR))


def _stealth_relay_selector(relay_mode: str) -> list[str]:
    """TG/Meta (Intl_Stealth): same relay pool as autotrim, never NL."""
    return _relay_part(relay_mode)


def _apply_selector(
    doc: dict, target_sel: list[str], *, stealth_relay_sel: list[str] | None = None
) -> tuple[bool, list[str]]:
    log: list[str] = []
    if len(target_sel) < MIN_PATHS:
        log.append(f"refuse: selector len {len(target_sel)} < {MIN_PATHS}")
        return False, log
    if not _allowed_target_selector(target_sel):
        log.append(f"refuse: selector not allowed: {target_sel}")
        return False, log

    changed = False
    intl_b = next((b for b in (doc.get("routing") or {}).get("balancers") or [] if b.get("tag") == INTL_TAG), None)
    if not intl_b:
        log.append(f"missing {INTL_TAG}")
        return False, log

    old = list(intl_b.get("selector") or [])
    if old != target_sel:
        intl_b["selector"] = list(target_sel)
        log.append(f"{INTL_TAG}: {len(old)} paths → {len(target_sel)} paths")
        changed = True
    else:
        log.append(f"OK {INTL_TAG}: already {len(target_sel)} paths")

    if stealth_relay_sel is not None:
        stealth_b = next(
            (b for b in (doc.get("routing") or {}).get("balancers") or [] if b.get("tag") == INTL_STEALTH_BALANCER_TAG),
            None,
        )
        if not stealth_b:
            log.append(f"missing {INTL_STEALTH_BALANCER_TAG}")
            return False, log
        if len(stealth_relay_sel) < MIN_PATHS:
            log.append(f"refuse: {INTL_STEALTH_BALANCER_TAG} len {len(stealth_relay_sel)} < {MIN_PATHS}")
            return False, log
        if stealth_relay_sel not in allowed_relay_only_selectors():
            log.append(f"refuse: stealth selector not allowed: {stealth_relay_sel}")
            return False, log
        old_s = list(stealth_b.get("selector") or [])
        if old_s != stealth_relay_sel:
            stealth_b["selector"] = list(stealth_relay_sel)
            log.append(f"{INTL_STEALTH_BALANCER_TAG}: {len(old_s)} → {len(stealth_relay_sel)} paths (TG/Meta)")
            changed = True
        else:
            log.append(f"OK {INTL_STEALTH_BALANCER_TAG}: already {len(stealth_relay_sel)} paths")

    return changed, log


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Attempt guarded live apply (default: dry-run)")
    ap.add_argument(
        "--mode",
        choices=[MODE_DRY_RUN, MODE_SCALE, MODE_DEGRADE, MODE_INCIDENT, MODE_MANUAL_EMERGENCY],
        default=None,
        help="Guardrail mode for --apply (required when apply would reduce capacity)",
    )
    ap.add_argument("--incident-ttl-minutes", type=int, default=None)
    ap.add_argument("--owner-approved", action="store_true")
    ap.add_argument(
        "--rollback-snapshot",
        type=Path,
        default=None,
        help="Pre-captured rollback snapshot path (else created on apply before PATCH)",
    )
    ap.add_argument("--guardrail-min-delivery-paths", type=int, default=2)
    ap.add_argument("--guardrail-min-relay-ips", type=int, default=2)
    ap.add_argument("--guardrail-min-geos", type=int, default=None)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--json", action="store_true", dest="json_out")
    ap.add_argument("--skip-probe", action="store_true")
    ap.add_argument("--skip-pre-verify", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    print_guardrail_banner(
        "latency_selector_autotrim", capacity_reducing=True, cron_managed=True
    )

    guard_cfg = GuardrailConfig(
        minimum_delivery_paths=args.guardrail_min_delivery_paths,
        minimum_relay_ips=args.guardrail_min_relay_ips,
        minimum_geos=args.guardrail_min_geos,
    )
    diagnostic_log: list[str] = []

    try:
        registry = load_validated_registry(args.registry)
        registry_nodes = [n for n in (registry.get("nodes") or []) if isinstance(n, dict)]
    except Exception as exc:
        registry_nodes = []
        diagnostic_log.append(f"registry load failed: {exc}")
        if args.apply:
            guard = GuardrailResult(
                allowed=False,
                mode=MODE_DRY_RUN,
                is_live_apply=False,
                blockers=["guardrail: cannot build before/after capacity state (registry missing)"],
                summary="apply blocked: registry unavailable",
            )
            payload = format_autotrim_result(
                status=STATUS_APPLY_BLOCKED,
                guard=guard,
                relay_mode_before="full",
                relay_mode_after="full",
                include_nl_before=True,
                include_nl_after=True,
                changed=False,
                diagnostic_log=diagnostic_log,
            )
            if args.json_out:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"status: {STATUS_APPLY_BLOCKED}")
                for b in guard.blockers:
                    print(f"  - {b}")
            return 2

    print("=== pre-verify ===")
    if not args.skip_pre_verify and not _verify_profile():
        print("ABORT: pre-verify failed", file=sys.stderr)
        return 1

    state = _load_state()
    relay_mode_before = str(state.get("relay_mode") or "full")
    include_nl_before = bool(state.get("nl_in_selector", True))

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]

    if (
        not is_relay_only_profile(doc)
        and not is_relay_nl_intl_profile(doc)
        and not is_stealth_split_profile(doc)
        and not is_stealth_split_relay_nl_443_profile(doc)
    ):
        print("ABORT: not relay gen>=47 profile", file=sys.stderr)
        return 1

    relay_probes: list[RelayIpProbe] = []
    nl_probes: list[RelayIpProbe] = []

    if args.skip_probe:
        print("[autotrim] skip-probe")
        diagnostic_log.append("[autotrim] skip-probe")
        for row in (state.get("last_relay_probe") or {}).get("results") or []:
            relay_probes.append(
                RelayIpProbe(
                    ip=str(row["ip"]),
                    ok=bool(row["ok"]),
                    tcp_connect_ms=row.get("tcp_connect_ms"),
                    tls_ok=False,
                    error=row.get("error"),
                )
            )
        for row in (state.get("last_nl_probe") or {}).get("results") or []:
            nl_probes.append(
                RelayIpProbe(
                    ip=str(row["ip"]),
                    ok=bool(row["ok"]),
                    tcp_connect_ms=row.get("tcp_connect_ms"),
                    tls_ok=False,
                    error=row.get("error"),
                )
            )
    else:
        print("=== relay latency probe ===")
        relay_probes, err = probe_relay_ips()
        if err and not any(r.ok for r in relay_probes):
            print(f"PROBE_FAIL: {err}", file=sys.stderr)
            return 1
        state["last_relay_probe"] = {
            "results": [
                {"ip": r.ip, "ok": r.ok, "tcp_connect_ms": r.tcp_connect_ms, "error": r.error}
                for r in relay_probes
            ]
        }
        if _inject_has_nl(doc):
            print("=== NL reachability probe ===")
            nl_probes, nl_err = probe_nl_from_ru()
            if nl_probes:
                state["last_nl_probe"] = {
                    "results": [
                        {"ip": r.ip, "ok": r.ok, "tcp_connect_ms": r.tcp_connect_ms, "error": r.error}
                        for r in nl_probes
                    ]
                }
            if nl_err and not nl_probes:
                print(f"NL probe warn: {nl_err}")

    relay_mode, relay_log = _evaluate_relay(_probe_by_ip(relay_probes), state)
    for line in relay_log:
        print(line)
        diagnostic_log.append(line)
    state["relay_mode"] = relay_mode

    include_nl, nl_log = _evaluate_nl(nl_probes, state, doc)
    for line in nl_log:
        print(line)
        diagnostic_log.append(line)
    state["nl_in_selector"] = include_nl

    target_sel = _build_target(relay_mode, include_nl, doc)
    stealth_sel: list[str] | None = None
    if is_stealth_split_profile(doc):
        stealth_sel = _stealth_relay_selector(relay_mode)
        msg = (
            f"target selector: {len(target_sel)} paths (relay={relay_mode} nl={include_nl}); "
            f"stealth relay×{len(stealth_sel)}"
        )
        print(msg)
        diagnostic_log.append(msg)
    else:
        msg = f"target selector: {len(target_sel)} paths (relay={relay_mode} nl={include_nl})"
        print(msg)
        diagnostic_log.append(msg)

    patched = copy.deepcopy(doc)
    changed, patch_log = _apply_selector(patched, target_sel, stealth_relay_sel=stealth_sel)
    for line in patch_log:
        print(line)
        diagnostic_log.append(line)
    _save_state(state)

    before_cap = build_autotrim_capacity_state(registry_nodes, doc, relay_mode_before, include_nl_before)
    after_cap = build_autotrim_capacity_state(registry_nodes, doc, relay_mode, include_nl)
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

    if not changed:
        guard = evaluate_autotrim_apply_guard(
            registry_nodes=registry_nodes,
            doc=doc,
            relay_mode_before=relay_mode_before,
            relay_mode_after=relay_mode,
            include_nl_before=include_nl_before,
            include_nl_after=include_nl,
            mode=MODE_DRY_RUN,
            owner_approved=False,
            rollback_snapshot_present=False,
            config=guard_cfg,
        )
        status = STATUS_DRY_RUN
        print("[autotrim] no selector change")
        payload = format_autotrim_result(
            status=status,
            guard=guard,
            relay_mode_before=relay_mode_before,
            relay_mode_after=relay_mode,
            include_nl_before=include_nl_before,
            include_nl_after=include_nl,
            changed=False,
            diagnostic_log=diagnostic_log,
        )
        if args.json_out:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"\nstatus: {status}")
            print(guard.summary)
        return 0

    if not args.apply:
        guard = evaluate_autotrim_apply_guard(
            registry_nodes=registry_nodes,
            doc=doc,
            relay_mode_before=relay_mode_before,
            relay_mode_after=relay_mode,
            include_nl_before=include_nl_before,
            include_nl_after=include_nl,
            mode=MODE_DRY_RUN,
            owner_approved=False,
            rollback_snapshot_present=False,
            config=guard_cfg,
        )
        payload = format_autotrim_result(
            status=STATUS_DRY_RUN,
            guard=guard,
            relay_mode_before=relay_mode_before,
            relay_mode_after=relay_mode,
            include_nl_before=include_nl_before,
            include_nl_after=include_nl,
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
                "  python ops/latency_selector_autotrim.py --apply --mode incident "
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
        payload = format_autotrim_result(
            status=STATUS_APPLY_BLOCKED,
            guard=guard,
            relay_mode_before=relay_mode_before,
            relay_mode_after=relay_mode,
            include_nl_before=include_nl_before,
            include_nl_after=include_nl,
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
        snap = SNAPSHOT_DIR / f"template-before-autotrim-{time.strftime('%Y%m%d_%H%M%S')}.json"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
        rollback_path = snap
        rollback_present = True
        diagnostic_log.append(f"rollback snapshot created: {rollback_path.name}")

    guard = evaluate_autotrim_apply_guard(
        registry_nodes=registry_nodes,
        doc=doc,
        relay_mode_before=relay_mode_before,
        relay_mode_after=relay_mode,
        include_nl_before=include_nl_before,
        include_nl_after=include_nl,
        mode=apply_mode,
        owner_approved=owner_approval_present(args.owner_approved),
        rollback_snapshot_present=rollback_present,
        incident_ttl_minutes=args.incident_ttl_minutes,
        config=guard_cfg,
    )

    if not guard.allowed:
        payload = format_autotrim_result(
            status=STATUS_APPLY_BLOCKED,
            guard=guard,
            relay_mode_before=relay_mode_before,
            relay_mode_after=relay_mode,
            include_nl_before=include_nl_before,
            include_nl_after=include_nl,
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

    payload = format_autotrim_result(
        status=STATUS_APPLY_ALLOWED,
        guard=guard,
        relay_mode_before=relay_mode_before,
        relay_mode_after=relay_mode,
        include_nl_before=include_nl_before,
        include_nl_after=include_nl,
        changed=True,
        diagnostic_log=diagnostic_log,
    )
    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"\nstatus: {STATUS_APPLY_ALLOWED}")
        print(guard.summary)

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
    after_template_patch("latency_selector_autotrim")

    print("=== post-verify ===")
    if not _verify_profile():
        print("FAIL: post-verify — restore snapshot", file=sys.stderr)
        return 1
    print(f"Applied autotrim relay={relay_mode} nl={include_nl} (gen+1, no TG broadcast)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
