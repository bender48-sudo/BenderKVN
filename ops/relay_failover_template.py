#!/usr/bin/env python3
"""VPN-AUD-202: auto-trim relay outbounds from balancers when RU relay probe fails.

Uses ``tspu_block_probe_ru`` (SSH → relay check.py) as health signal.
Hysteresis: ``--fail-threshold`` consecutive fails → trim proxy-5..7;
``--ok-threshold`` consecutive OK → restore prior selector profile.

Does not touch injectHosts — only balancer selectors (Super_Balancer, Intl_Direct).
No Telegram broadcast (after_template_patch push_ams=False).

Usage:
    python ops/relay_failover_template.py              # probe + dry-run
    python ops/relay_failover_template.py --apply      # PATCH panel on state change
    python ops/relay_failover_template.py --force-trim --apply
    python ops/relay_failover_template.py --force-restore --apply
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
    LV_DIRECT_ONLY_SELECTOR,
    LV_RELAY_SELECTOR,
    RELAY_OUTBOUND_TAGS,
    RU_MULTIPATH_SELECTOR,
)
from panel_client import PanelClient  # noqa: E402
from subscription_config_notify import after_template_patch  # noqa: E402
from vpn_apply_guard import print_guardrail_banner  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = ROOT / ".secrets" / "snapshots"
STATE_FILE = ROOT / ".secrets" / "relay_failover_state.json"

_BALANCER_TAGS = ("Super_Balancer", "Intl_Direct")


def _is_relay_only_gen47(doc: dict) -> bool:
    from balancer_selectors import is_relay_only_profile

    return is_relay_only_profile(doc)


def _load_state() -> dict:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "mode": "normal",
        "fail_streak": 0,
        "ok_streak": 0,
        "saved_super_selector": None,
        "saved_intl_selector": None,
        "last_probe_ok": None,
        "updated_at": "",
    }


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def probe_relay_ok() -> bool:
    script = _OPS / "tspu_block_probe_ru.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0 and "TSPU_BLOCK_PROBE_RU_OK" in out
    print(out.rstrip())
    return ok


def _selector_has_relay(sel: list[str]) -> bool:
    return any(t in sel for t in RELAY_OUTBOUND_TAGS)


def _restore_selector(saved: list[str] | None, fallback: list[str]) -> list[str]:
    if saved and isinstance(saved, list) and saved:
        return list(saved)
    return list(fallback)


def _trim_selectors(doc: dict, state: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    if _is_relay_only_gen47(doc):
        log.append(
            "SKIP trim: gen>=47 relay-only profile — use latency_selector_autotrim.py "
            "(this script must not fall back to LV direct)"
        )
        return False, log
    changed = False
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    super_b = balancers.get("Super_Balancer")
    intl_b = balancers.get("Intl_Direct")
    if not super_b or not intl_b:
        log.append("WARN: Super_Balancer / Intl_Direct missing")
        return False, log

    super_sel = list(super_b.get("selector") or [])
    intl_sel = list(intl_b.get("selector") or [])
    if not _selector_has_relay(super_sel) and not _selector_has_relay(intl_sel):
        log.append("already trimmed (no relay in selectors)")
        return False, log

    if state.get("saved_super_selector") is None:
        state["saved_super_selector"] = super_sel
    if state.get("saved_intl_selector") is None:
        state["saved_intl_selector"] = intl_sel

    for tag, b, trimmed in (
        ("Super_Balancer", super_b, LV_DIRECT_ONLY_SELECTOR),
        ("Intl_Direct", intl_b, LV_DIRECT_ONLY_SELECTOR),
    ):
        old = list(b.get("selector") or [])
        if old != trimmed:
            b["selector"] = list(trimmed)
            log.append(f"{tag}: {len(old)} → {len(trimmed)} paths (relay trimmed)")
            changed = True
        else:
            log.append(f"OK {tag}: already LV-direct-only")
    return changed, log


def _restore_selectors(doc: dict, state: dict) -> tuple[bool, list[str]]:
    log: list[str] = []
    changed = False
    balancers = {b.get("tag"): b for b in (doc.get("routing") or {}).get("balancers") or []}
    super_b = balancers.get("Super_Balancer")
    intl_b = balancers.get("Intl_Direct")
    if not super_b or not intl_b:
        log.append("WARN: Super_Balancer / Intl_Direct missing")
        return False, log

    target_super = _restore_selector(state.get("saved_super_selector"), LV_RELAY_SELECTOR)
    target_intl = _restore_selector(state.get("saved_intl_selector"), LV_RELAY_SELECTOR)

    for tag, b, target in (
        ("Super_Balancer", super_b, target_super),
        ("Intl_Direct", intl_b, target_intl),
    ):
        old = list(b.get("selector") or [])
        if old != target:
            b["selector"] = list(target)
            log.append(f"{tag}: {len(old)} → {len(target)} paths (relay restored)")
            changed = True
        else:
            log.append(f"OK {tag}: already at restore target ({len(target)} paths)")

    if changed:
        state["saved_super_selector"] = None
        state["saved_intl_selector"] = None
    return changed, log


def _patch_template(c: PanelClient, tpl: dict, doc: dict, template_uuid: str) -> int:
    snap = SNAPSHOT_DIR / f"template-before-relay-failover-{time.strftime('%Y%m%d_%H%M%S')}.json"
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
        print(f"FAIL PATCH HTTP {code}: {body!s}"[:400], file=sys.stderr)
        return 1
    after_template_patch("relay_failover_template")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-probe", action="store_true", help="use last state only (testing)")
    ap.add_argument("--force-trim", action="store_true")
    ap.add_argument("--force-restore", action="store_true")
    ap.add_argument("--fail-threshold", type=int, default=2)
    ap.add_argument("--ok-threshold", type=int, default=3)
    ap.add_argument("--template-uuid", default=site_urls.REMNA_TEMPLATE_UUID)
    args = ap.parse_args()

    print_guardrail_banner(
        "relay_failover_template", capacity_reducing=True, cron_managed=True
    )

    if args.force_trim and args.force_restore:
        print("choose --force-trim or --force-restore, not both", file=sys.stderr)
        return 2

    state = _load_state()
    probe_ok: bool | None = None
    if args.force_trim:
        probe_ok = False
        print("[relay-failover] forced TRIM")
    elif args.force_restore:
        probe_ok = True
        print("[relay-failover] forced RESTORE")
    elif args.skip_probe:
        probe_ok = state.get("last_probe_ok")
        print(f"[relay-failover] skip-probe, last_probe_ok={probe_ok!r}")
    else:
        probe_ok = probe_relay_ok()

    state["last_probe_ok"] = probe_ok
    if probe_ok:
        state["ok_streak"] = int(state.get("ok_streak", 0)) + 1
        state["fail_streak"] = 0
    else:
        state["fail_streak"] = int(state.get("fail_streak", 0)) + 1
        state["ok_streak"] = 0

    action: str | None = None
    if args.force_trim:
        action = "trim"
    elif args.force_restore:
        action = "restore"
    elif state.get("mode") == "trimmed":
        if state["ok_streak"] >= args.ok_threshold:
            action = "restore"
    else:
        if state["fail_streak"] >= args.fail_threshold:
            action = "trim"

    print(
        f"[relay-failover] mode={state.get('mode')} fail={state['fail_streak']} "
        f"ok={state['ok_streak']} action={action or 'none'}"
    )

    if not action:
        _save_state(state)
        return 0 if probe_ok else 0  # probe fail alone is not script error

    c = PanelClient(timeout=120)
    tpl = c.get_or_raise(f"/api/subscription-templates/{args.template_uuid}")["response"]
    doc = copy.deepcopy(tpl["templateJson"])

    if action == "trim":
        changed, log = _trim_selectors(doc, state)
        state["mode"] = "trimmed"
    else:
        changed, log = _restore_selectors(doc, state)
        state["mode"] = "normal"
        state["fail_streak"] = 0

    for line in log:
        print(line)

    _save_state(state)

    if not changed:
        return 0
    if not args.apply:
        print("\nDry-run. Apply: python ops/relay_failover_template.py --apply")
        return 0

    rc = _patch_template(c, tpl, doc, args.template_uuid)
    if rc == 0:
        print(f"Applied relay failover: {action} (gen+1, no TG broadcast)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
