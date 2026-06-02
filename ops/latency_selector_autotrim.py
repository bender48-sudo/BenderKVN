#!/usr/bin/env python3
"""VPN-AUD-310/220: server-side Intl_Direct selector autotrim (relay + NL).

Trims bad paths without gen=33/45/132 footguns:
  - Only Intl_Direct selector — never Super/LV direct, never observatory
  - Relay: trim whole slow relay IP (min 3 relay paths)
  - NL: drop proxy-7..10 from selector if RU probe fails (injectHosts unchanged)
  - Hysteresis: 2 bad probes → trim; 3 OK → restore
  - Both relays dead → no PATCH

Usage:
    python ops/latency_selector_autotrim.py
    python ops/latency_selector_autotrim.py --apply
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
    allowed_relay_only_selectors,
    is_relay_nl_intl_profile,
    is_relay_only_profile,
    is_stealth_split_profile,
)
from nl_reachability_probe_ru import NL_IP, probe_nl_from_ru  # noqa: E402
from panel_client import PanelClient  # noqa: E402
from relay_latency_probe import RELAY1_IP, RELAY2_IP, RelayIpProbe, probe_relay_ips  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402

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


def _relay_part(mode: str) -> list[str]:
    if mode == "relay1_only":
        return list(RELAY1_SELECTOR)
    if mode == "relay2_only":
        return list(RELAY2_SELECTOR)
    return list(RELAY6_SELECTOR)


def _build_target(relay_mode: str, include_nl: bool, doc: dict) -> list[str]:
    relay_sel = _relay_part(relay_mode)
    if include_nl and _inject_has_nl(doc):
        return relay_sel + list(NL_DIRECT_SELECTOR)
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
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-probe", action="store_true")
    ap.add_argument("--skip-pre-verify", action="store_true")
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    print("=== pre-verify ===")
    if not args.skip_pre_verify and not _verify_profile():
        print("ABORT: pre-verify failed", file=sys.stderr)
        return 1

    state = _load_state()
    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = tpl["templateJson"]

    if not is_relay_only_profile(doc) and not is_relay_nl_intl_profile(doc) and not is_stealth_split_profile(doc):
        print("ABORT: not relay gen>=47 profile", file=sys.stderr)
        return 1

    relay_probes: list[RelayIpProbe] = []
    nl_probes: list[RelayIpProbe] = []

    if args.skip_probe:
        print("[autotrim] skip-probe")
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
    state["relay_mode"] = relay_mode

    include_nl, nl_log = _evaluate_nl(nl_probes, state, doc)
    for line in nl_log:
        print(line)
    state["nl_in_selector"] = include_nl

    target_sel = _build_target(relay_mode, include_nl, doc)
    stealth_sel: list[str] | None = None
    if is_stealth_split_profile(doc):
        stealth_sel = _stealth_relay_selector(relay_mode)
        print(
            f"target selector: {len(target_sel)} paths (relay={relay_mode} nl={include_nl}); "
            f"stealth relay×{len(stealth_sel)}"
        )
    else:
        print(f"target selector: {len(target_sel)} paths (relay={relay_mode} nl={include_nl})")

    patched = copy.deepcopy(doc)
    changed, patch_log = _apply_selector(patched, target_sel, stealth_relay_sel=stealth_sel)
    for line in patch_log:
        print(line)
    _save_state(state)

    if not changed:
        print("[autotrim] no selector change")
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/latency_selector_autotrim.py --apply")
        return 0

    snap = SNAPSHOT_DIR / f"template-before-autotrim-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
    after_template_patch("latency_selector_autotrim")

    print("=== post-verify ===")
    if not _verify_profile():
        print("FAIL: post-verify — restore snapshot", file=sys.stderr)
        return 1
    print(f"Applied autotrim relay={relay_mode} nl={include_nl} (gen+1, no TG broadcast)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
