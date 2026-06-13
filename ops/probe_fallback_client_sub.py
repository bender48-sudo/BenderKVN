#!/usr/bin/env python3
"""Read-only probe: Happ vs Karing vs v2rayN subscription emit shape (CLIENT-STABILITY-DESKTOP-FALLBACK-001).

Does not mutate prod. Prints summary only — no vless:// lines, UUIDs, or full sub URLs.

Usage:
    python ops/probe_fallback_client_sub.py
    python ops/probe_fallback_client_sub.py --short YOUR_SHORT_UUID
    python ops/probe_fallback_client_sub.py --json
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import site_urls  # noqa: E402
from subscription_fetch import (  # noqa: E402
    AMS_IP,
    LV_IP,
    NL_IP,
    RELAY_IP,
    decode_subscription,
    fetch_url,
    outbound_endpoint,
    xray_config_root,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
_token_path = ROOT / ".secrets" / "panel-token.txt"

CLIENT_UAS: dict[str, str] = {
    "happ": "Happ/1.9.4 (iOS)",
    "karing": "Karing/1.0.38 (iOS)",
    "v2rayn": "v2rayN/7.3.6",
}

RELAY2_IP = "46.173.28.252"
VLESS_URI_RE = re.compile(r"vless://", re.I)


def _load_token() -> str:
    token = (os.environ.get("PANEL_TOKEN") or os.environ.get("REMNA_API_TOKEN") or "").strip()
    if not token and _token_path.is_file():
        token = _token_path.read_text(encoding="ascii").strip()
    if not token:
        raise SystemExit("set PANEL_TOKEN/REMNA_API_TOKEN or create .secrets/panel-token.txt")
    return token


def endpoint_label(addr: str | None, port: int | None) -> str:
    if not addr:
        return "UNKNOWN"
    if addr == LV_IP:
        return f"LV:{port or '?'}"
    if addr == NL_IP:
        return f"NL:{port or '?'}"
    if addr == AMS_IP:
        return f"AMS:{port or '?'}"
    if addr == RELAY_IP:
        return f"RELAY1:{port or '?'}"
    if addr == RELAY2_IP:
        return f"RELAY2:{port or '?'}"
    return f"OTHER:{addr}:{port or '?'}"


def summarize_happ_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    balancers = (cfg.get("routing") or {}).get("balancers") or []
    rules = (cfg.get("routing") or {}).get("rules") or []
    bal_tags = [b.get("tag") for b in balancers if isinstance(b, dict)]
    stealth_rules = sum(1 for r in rules if r.get("balancerTag") == "Intl_Stealth")
    proxy_out = [o for o in cfg.get("outbounds") or [] if str(o.get("tag", "")).startswith("proxy")]
    endpoints = [endpoint_label(*outbound_endpoint(o)) for o in proxy_out]
    return {
        "client": "happ",
        "format": "xray_json",
        "proxy_count": len(proxy_out),
        "endpoints": endpoints,
        "balancer_tags": bal_tags,
        "stealth_rules": stealth_rules,
        "candidate_d_shape": len(proxy_out) >= 6 and "Intl_Direct" in bal_tags,
        "auto_equivalent": len(proxy_out) >= 6 and stealth_rules >= 1 and "Intl_Stealth" in bal_tags,
        "fallback_tag_direct": any(r.get("fallbackTag") == "direct" for r in rules),
    }


def summarize_karing_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    outbounds = cfg.get("outbounds") or []
    routes = cfg.get("route") or {}
    rules = routes.get("rules") if isinstance(routes, dict) else []
    if rules is None:
        rules = []
    vless = [o for o in outbounds if o.get("type") == "vless" or o.get("protocol") == "vless"]
    endpoints: list[str] = []
    for o in vless:
        server = o.get("server") or o.get("settings", {}).get("vnext", [{}])[0].get("address")
        port = o.get("server_port") or o.get("settings", {}).get("vnext", [{}])[0].get("port")
        endpoints.append(endpoint_label(server, port))
    return {
        "client": "karing",
        "format": "singbox_json",
        "proxy_count": len(vless),
        "endpoints": endpoints,
        "route_rules": len(rules) if isinstance(rules, list) else 0,
        "candidate_d_shape": False,
        "auto_equivalent": False,
        "fallback_tag_direct": False,
        "note": "stripped LV-centric emit expected",
    }


def summarize_v2rayn_body(body: bytes) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace").strip()
    if VLESS_URI_RE.search(text):
        return {
            "client": "v2rayn",
            "format": "vless_link",
            "proxy_count": 1,
            "endpoints": ["embedded_vless_link"],
            "route_rules": 0,
            "candidate_d_shape": False,
            "auto_equivalent": False,
            "fallback_tag_direct": False,
            "note": "single link — decode not printed",
        }
    try:
        parsed = decode_subscription(body)
        if isinstance(parsed, dict):
            return summarize_happ_cfg(xray_config_root(parsed))
        if isinstance(parsed, list) and parsed:
            return summarize_happ_cfg(xray_config_root(parsed))
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    try:
        decoded = base64.b64decode(text).decode("utf-8", errors="replace")
        if VLESS_URI_RE.search(decoded):
            return summarize_v2rayn_body(decoded.encode())
    except Exception:
        pass
    return {
        "client": "v2rayn",
        "format": "unknown",
        "proxy_count": 0,
        "endpoints": [],
        "route_rules": 0,
        "candidate_d_shape": False,
        "auto_equivalent": False,
        "fallback_tag_direct": False,
        "note": f"unparsed body len={len(body)}",
    }


def summarize_client_response(client: str, body: bytes, content_type: str | None) -> dict[str, Any]:
    ct = (content_type or "").split(";")[0].strip().lower()
    base = {"client": client, "http_bytes": len(body), "content_type": ct}
    if client == "v2rayn" or ct in ("text/plain", "application/octet-stream"):
        summary = summarize_v2rayn_body(body)
    else:
        try:
            parsed = decode_subscription(body)
            root = xray_config_root(parsed)
            if client == "karing" or "outbounds" in root and any(
                isinstance(o, dict) and o.get("type") for o in root.get("outbounds") or []
            ):
                summary = summarize_karing_cfg(root)
            else:
                summary = summarize_happ_cfg(root)
        except (json.JSONDecodeError, ValueError, TypeError):
            summary = summarize_v2rayn_body(body)
    return {**base, **summary}


def pick_short_uuid(explicit: str | None) -> str:
    if explicit:
        return explicit
    token = _load_token()
    resp = fetch_url(
        f"{site_urls.PANEL_URL}/api/users?limit=10&start=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status != 200:
        raise SystemExit(f"FAIL: users HTTP {resp.status}")
    users = json.loads(resp.body).get("response", {}).get("users") or []
    for u in users:
        if u.get("status") in ("ACTIVE", "active"):
            short = u.get("shortUuid") or u.get("subscriptionUuid")
            if short:
                return short
    if users:
        u0 = users[0]
        short = u0.get("shortUuid") or u0.get("subscriptionUuid")
        if short:
            return short
    raise SystemExit("FAIL: no user with shortUuid")


def probe_all(short: str) -> dict[str, Any]:
    origin = site_urls.SUB_PUBLIC_ORIGIN
    results: dict[str, Any] = {"short_uuid_prefix": short[:8] + "…", "clients": {}}
    for name, ua in CLIENT_UAS.items():
        resp = fetch_url(f"{origin}/api/sub/{short}", headers={"User-Agent": ua})
        if resp.status != 200:
            results["clients"][name] = {"error": f"HTTP {resp.status}"}
            continue
        results["clients"][name] = summarize_client_response(name, resp.body, resp.content_type)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--short", help="subscription shortUuid (default: first active user)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    short = pick_short_uuid(args.short)
    report = probe_all(short)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"OK: fallback client probe short={report['short_uuid_prefix']}")
        for name, row in report["clients"].items():
            if "error" in row:
                print(f"  {name}: {row['error']}")
                continue
            auto = "AUTO" if row.get("auto_equivalent") else "strip"
            print(
                f"  {name}: {row.get('format')} proxies={row.get('proxy_count')} "
                f"endpoints={row.get('endpoints')} auto={auto}"
            )
            if row.get("fallback_tag_direct"):
                print(f"    WARN: fallbackTag=direct present")
        happ = report["clients"].get("happ", {})
        v2 = report["clients"].get("v2rayn", {})
        if happ.get("auto_equivalent") and not v2.get("auto_equivalent"):
            print("  parity: Happ full Auto; v2rayN/Karing stripped (expected)")
        print("FALLBACK_CLIENT_PROBE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
