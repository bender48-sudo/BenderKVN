"""Shared fetch/decode helpers for subscription probe scripts (Q-VPN-STAB-001/002)."""
from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

import site_urls

HAPP_UA = "Happ/1.9.4 (iOS)"

LV_IP = "176.126.162.158"
AMS_IP = "168.100.11.140"
NL_IP = "91.90.192.17"
RELAY_IP = site_urls.RU_RELAY_HOST

# Happ batch-import accepts common Xray networks; xhttp triggers UnknownContentType in logs.
HAPP_BATCH_NETWORKS = frozenset({"tcp", "ws", "grpc", "http", "h2", "kcp", "quic"})


@dataclass
class FetchResult:
    status: int
    body: bytes
    content_type: str | None
    content_type_ok: bool


def ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def fetch_url(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> FetchResult:
    req = urllib.request.Request(url)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout) as resp:
            ct = resp.headers.get("Content-Type")
            body = resp.read()
            ct_ok = bool(ct and ct.lower().split(";")[0].strip() == "application/json")
            return FetchResult(resp.status, body, ct, ct_ok)
    except urllib.error.HTTPError as e:
        ct = e.headers.get("Content-Type") if e.headers else None
        body = e.read()
        ct_ok = bool(ct and ct.lower().split(";")[0].strip() == "application/json")
        return FetchResult(e.code, body, ct, ct_ok)


def decode_subscription(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(base64.b64decode(text).decode("utf-8", errors="replace"))


def xray_config_root(sub: Any) -> dict[str, Any]:
    if isinstance(sub, list) and sub and isinstance(sub[0], dict):
        return sub[0]
    if isinstance(sub, dict):
        return sub
    raise ValueError(f"unexpected subscription root: {type(sub).__name__}")


def extract_outbounds(sub: Any) -> list[dict[str, Any]]:
    root = xray_config_root(sub)
    obs = root.get("outbounds")
    return obs if isinstance(obs, list) else []


def outbound_network(o: dict[str, Any]) -> str:
    rs = o.get("streamSettings") or {}
    return str(rs.get("network") or "tcp").lower()


def outbound_endpoint(o: dict[str, Any]) -> tuple[str | None, int | None]:
    s = o.get("settings") or {}
    vnext = s.get("vnext")
    if isinstance(vnext, list) and vnext:
        v0 = vnext[0]
        return v0.get("address"), v0.get("port")
    servers = s.get("servers")
    if isinstance(servers, list) and servers:
        s0 = servers[0]
        return s0.get("address"), s0.get("port")
    return None, None


def node_label(addr: str | None, port: int | None) -> str:
    if not addr or port is None:
        return "UNKNOWN"
    if addr == LV_IP:
        return "LV"
    if addr == NL_IP:
        return "NL"
    if addr == AMS_IP:
        return "AMS"
    if addr == RELAY_IP:
        if port == 443:
            return "RELAY→LV"
        if port == 9443:
            return "RELAY→NL"
        if port == 8443:
            return "RELAY→AMS"
        return f"RELAY:{port}"
    return f"OTHER:{addr}"


def happ_batch_parseable(o: dict[str, Any]) -> tuple[bool, str | None]:
    """Simulate Happ per-outbound batch import (UnknownContentType heuristic)."""
    tag = str(o.get("tag") or "")
    if tag in ("direct", "block", "dns-out", "dns", "freedom"):
        return True, None
    net = outbound_network(o)
    if net in HAPP_BATCH_NETWORKS:
        return True, None
    return False, f"UnknownContentType(network={net})"


def simulate_happ_batch(outbounds: list[dict[str, Any]]) -> dict[str, Any]:
    proxy_tags = []
    rows = []
    ok = 0
    fail = 0
    for o in outbounds:
        tag = str(o.get("tag") or "?")
        net = outbound_network(o)
        addr, port = outbound_endpoint(o)
        parseable, err = happ_batch_parseable(o)
        if parseable:
            ok += 1
        else:
            fail += 1
        if o.get("protocol") == "vless" and tag.startswith("proxy"):
            proxy_tags.append(tag)
        rows.append(
            {
                "tag": tag,
                "protocol": o.get("protocol"),
                "network": net,
                "node": node_label(addr, port if port is not None else None),
                "parseable": parseable,
                "error": err,
            }
        )
    xhttp_n = sum(1 for r in rows if r["network"] == "xhttp")
    # Happ logs: one bad type can zero a batch; conservative if any xhttp in proxy set.
    batch_risk = "HIGH" if xhttp_n > 0 else ("MEDIUM" if fail else "LOW")
    return {
        "total": len(outbounds),
        "parseable": ok,
        "failed": fail,
        "xhttp_count": xhttp_n,
        "proxy_tags": len(proxy_tags),
        "batch_risk": batch_risk,
        "rows": rows,
    }


def strip_xhttp_outbounds(sub: Any) -> Any:
    """Variant B for A/B: same config without xhttp proxy outbounds."""
    if isinstance(sub, list):
        return [strip_xhttp_outbounds(sub[0])] if sub else sub
    root = dict(xray_config_root(sub))
    outbounds = []
    for o in root.get("outbounds") or []:
        if outbound_network(o) == "xhttp":
            continue
        outbounds.append(o)
    root["outbounds"] = outbounds
    return root if isinstance(sub, dict) else [root]
