#!/usr/bin/env python3
"""Owner-only Happ lab profile: force relay #2 paths only (CLIENT-STABILITY-HAPP-RELAY2-LAB-001).

Transforms a live Happ subscription JSON locally. Does **not** patch prod template,
Remna users, or deploy anything. Owner imports the output JSON manually into Happ.

Usage:
    python ops/generate_happ_relay2_lab_profile.py --from-json owner_sub.json --write-json lab_relay2.json
    python ops/generate_happ_relay2_lab_profile.py --short YOUR_SHORT_UUID --write-json lab_relay2.json
    python ops/generate_happ_relay2_lab_profile.py --from-json owner_sub.json --single --write-json lab_relay2_one.json
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import sys
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from balancer_selectors import (  # noqa: E402
    INTL_BALANCER_TAG,
    INTL_STEALTH_BALANCER_TAG,
    RELAY1_SELECTOR,
    RELAY2_SELECTOR,
)
from relay_latency_probe import RELAY1_IP, RELAY2_IP  # noqa: E402
from subscription_fetch import (  # noqa: E402
    HAPP_UA,
    decode_subscription,
    fetch_url,
    happ_batch_parseable,
    outbound_endpoint,
    simulate_happ_batch,
    xray_config_root,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LAB_REMARKS_RELAY2 = "BenderVPN Auto [LAB relay2-only — do NOT refresh sub]"
LAB_REMARKS_SINGLE = "BenderVPN Auto [LAB relay2×1 — do NOT refresh sub]"

BALANCER_TAGS_TO_PIN = frozenset({INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG})


def _proxy_tag(ob: dict[str, Any]) -> str:
    return str(ob.get("tag") or "")


def _is_vless_proxy(ob: dict[str, Any]) -> bool:
    return ob.get("protocol") == "vless" and _proxy_tag(ob).startswith("proxy")


def target_selector(*, single: bool) -> list[str]:
    if single:
        return [RELAY2_SELECTOR[0]]
    return list(RELAY2_SELECTOR)


def build_relay2_lab_profile(cfg: dict[str, Any], *, single: bool = False) -> dict[str, Any]:
    """Return deep copy with relay #1 / NL proxy outbounds removed; balancers pinned to relay #2."""
    out = copy.deepcopy(cfg)
    keep_tags = set(target_selector(single=single))

    new_outbounds: list[dict[str, Any]] = []
    for ob in out.get("outbounds") or []:
        if _is_vless_proxy(ob):
            tag = _proxy_tag(ob)
            if tag not in keep_tags:
                continue
            addr, _ = outbound_endpoint(ob)
            if addr and addr not in (RELAY2_IP, None):
                continue
        new_outbounds.append(ob)
    out["outbounds"] = new_outbounds

    routing = out.setdefault("routing", {})
    balancers = routing.get("balancers") or []
    selector = target_selector(single=single)
    for bal in balancers:
        tag = bal.get("tag")
        if tag in BALANCER_TAGS_TO_PIN:
            bal["selector"] = list(selector)
            bal.setdefault("strategy", {})["type"] = "random"
        elif tag and str(tag).startswith("Intl"):
            sel = list(bal.get("selector") or [])
            if any(t in RELAY1_SELECTOR or t in RELAY2_SELECTOR for t in sel):
                bal["selector"] = list(selector)
                bal.setdefault("strategy", {})["type"] = "random"

    rules = routing.get("rules") or []
    for rule in rules:
        if rule.get("outboundTag") == "direct" and isinstance(rule.get("ip"), list):
            rule["ip"] = [
                ip
                for ip in rule["ip"]
                if RELAY1_IP not in str(ip) and f"{RELAY1_IP}/32" not in str(ip)
            ]

    out.pop("observatory", None)
    out.pop("burstObservatory", None)
    out["remarks"] = LAB_REMARKS_SINGLE if single else LAB_REMARKS_RELAY2
    return out


def validate_relay2_lab_profile(cfg: dict[str, Any], *, single: bool = False) -> list[str]:
    """Return human-readable validation errors (empty = OK)."""
    errors: list[str] = []
    want_sel = target_selector(single=single)
    want_n = len(want_sel)

    proxy_out: list[dict[str, Any]] = [o for o in cfg.get("outbounds") or [] if _is_vless_proxy(o)]
    if len(proxy_out) != want_n:
        errors.append(f"vless_proxy={len(proxy_out)} want {want_n}")

    relay1_hits: list[str] = []
    relay2_hits: list[str] = []
    for ob in proxy_out:
        tag = _proxy_tag(ob)
        addr, port = outbound_endpoint(ob)
        if addr == RELAY1_IP:
            relay1_hits.append(tag)
        elif addr == RELAY2_IP:
            relay2_hits.append(f"{tag}@{port}")
        else:
            errors.append(f"{tag} endpoint {addr}:{port} not relay2 ({RELAY2_IP})")

    if relay1_hits:
        errors.append(f"relay1 outbounds still present: {relay1_hits}")
    if len(relay2_hits) != want_n:
        errors.append(f"relay2 paths={len(relay2_hits)} want {want_n}")

    for ob in proxy_out:
        ok, err = happ_batch_parseable(ob)
        if not ok:
            errors.append(f"{_proxy_tag(ob)} not Happ-parseable: {err}")

    balancers = {b.get("tag"): b for b in (cfg.get("routing") or {}).get("balancers") or []}
    for tag in (INTL_BALANCER_TAG, INTL_STEALTH_BALANCER_TAG):
        bal = balancers.get(tag)
        if not bal:
            errors.append(f"missing balancer {tag}")
            continue
        sel = list(bal.get("selector") or [])
        if sel != want_sel:
            errors.append(f"{tag} selector={sel} want {want_sel}")

    rules = (cfg.get("routing") or {}).get("rules") or []
    if any(r.get("fallbackTag") == "direct" for r in rules):
        errors.append("fallbackTag=direct present")

    stealth_rules = [r for r in rules if r.get("balancerTag") == INTL_STEALTH_BALANCER_TAG]
    if not stealth_rules:
        errors.append("no Intl_Stealth media rules (TG/IG may bypass relay pool)")

    for rule in rules:
        if rule.get("outboundTag") == "direct" and isinstance(rule.get("ip"), list):
            for ip in rule["ip"]:
                if RELAY1_IP in str(ip):
                    errors.append(f"in-core direct rule still routes relay1: {ip}")

    if cfg.get("observatory") or cfg.get("burstObservatory"):
        errors.append("observatory present")

    if "[LAB" not in str(cfg.get("remarks") or ""):
        errors.append("remarks missing LAB marker")

    return errors


def _load_cfg_from_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return xray_config_root(raw)


def _fetch_cfg(short: str) -> dict[str, Any]:
    sub_origin = site_urls.SUB_PUBLIC_ORIGIN
    sub_resp = fetch_url(
        f"{sub_origin}/api/sub/{short}",
        headers={"User-Agent": HAPP_UA},
    )
    if sub_resp.status != 200:
        raise SystemExit(f"FAIL: sub HTTP {sub_resp.status}")
    return xray_config_root(decode_subscription(sub_resp.body))


def _summary(cfg: dict[str, Any]) -> dict[str, Any]:
    proxies = [o for o in cfg.get("outbounds") or [] if _is_vless_proxy(o)]
    balancers = {b.get("tag"): b for b in (cfg.get("routing") or {}).get("balancers") or []}
    sim = simulate_happ_batch(cfg.get("outbounds") or [])
    return {
        "remarks": cfg.get("remarks"),
        "proxy_count": len(proxies),
        "proxy_tags": [_proxy_tag(o) for o in proxies],
        "relay2_endpoints": [
            f"{_proxy_tag(o)}:{outbound_endpoint(o)[1]}" for o in proxies
        ],
        "Intl_Direct_selector": list((balancers.get(INTL_BALANCER_TAG) or {}).get("selector") or []),
        "Intl_Stealth_selector": list(
            (balancers.get(INTL_STEALTH_BALANCER_TAG) or {}).get("selector") or []
        ),
        "happ_batch_risk": sim["batch_risk"],
        "happ_parseable": sim["parseable"],
        "happ_total": sim["total"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-json", type=Path, help="path to exported Happ sub JSON (root or [root])")
    src.add_argument("--short", help="fetch live Happ sub by shortUuid")
    ap.add_argument("--single", action="store_true", help="single outbound proxy-4 only (deterministic)")
    ap.add_argument("--write-json", type=Path, help="write lab profile JSON (Happ import)")
    ap.add_argument("--validate-only", action="store_true", help="validate input only, no transform")
    ap.add_argument("--json", action="store_true", help="machine-readable summary on stdout")
    args = ap.parse_args()

    if args.from_json:
        if not args.from_json.is_file():
            print(f"FAIL: not found: {args.from_json}", file=sys.stderr)
            return 1
        base = _load_cfg_from_json(args.from_json)
    else:
        base = _fetch_cfg(args.short)

    if args.validate_only:
        errs = validate_relay2_lab_profile(base, single=args.single)
        if errs:
            print("FAIL:", "; ".join(errs), file=sys.stderr)
            return 1
        print("OK: input already matches relay2 lab profile")
        return 0

    lab = build_relay2_lab_profile(base, single=args.single)
    errs = validate_relay2_lab_profile(lab, single=args.single)
    if errs:
        print("FAIL: lab validation:", "; ".join(errs), file=sys.stderr)
        return 1

    summary = _summary(lab)
    if args.json:
        print(json.dumps({"ok": True, "lab": summary}, ensure_ascii=False, indent=2))
    else:
        mode = "relay2×1" if args.single else "relay2×3"
        print(f"OK: lab profile {mode} — {summary['proxy_count']} proxy outbounds")
        print(f"  remarks: {summary['remarks']}")
        print(f"  Intl_Direct: {summary['Intl_Direct_selector']}")
        print(f"  Intl_Stealth: {summary['Intl_Stealth_selector']}")
        print(f"  endpoints: {', '.join(summary['relay2_endpoints'])}")
        print(f"  Happ batch: {summary['happ_parseable']}/{summary['happ_total']} parseable ({summary['happ_batch_risk']})")
        print("HAPP_RELAY2_LAB_PROFILE_OK")

    if args.write_json:
        payload = lab if isinstance(lab, dict) else lab
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote: {args.write_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
