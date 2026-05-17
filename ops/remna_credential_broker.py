#!/usr/bin/env python3
"""P1-RED-SEC-01: short-lived panel API token cache + audit (LV pilot).

Consumers (ru-monitor, balancer) read cached JWT with TTL instead of embedding
year-long tokens in process env. Master token stays in root-only source env;
future: replace source with Vault/SPIFFE (see docs/RUNBOOK-SHORT-LIVED-CREDS.md).
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CACHE_DIR = Path("/var/lib/bvpn/credentials")
AUDIT_LOG = Path("/var/log/bvpn-credential-audit.log")
SOURCE_ENV = Path("/etc/bvpn/remna-credential-source.env")
FALLBACK_ENV = Path("/etc/bvpn/ru-monitor.env")
DEFAULT_TTL = int(os.environ.get("REMNA_CRED_TTL_SEC", "3600"))
ALLOWED_CONSUMERS = frozenset({"ru-monitor", "balancer", "smoke"})


def _audit(event: str, consumer: str, **extra: Any) -> None:
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
        "consumer": consumer,
        "pid": os.getpid(),
        **extra,
    }
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        env[k.strip()] = v
    return env


def read_master_token() -> str:
    for path in (SOURCE_ENV, FALLBACK_ENV):
        env = _load_env_file(path)
        tok = env.get("REMNA_API_TOKEN") or env.get("PANEL_TOKEN")
        if tok:
            return tok.strip()
    raise RuntimeError(
        f"no REMNA_API_TOKEN in {SOURCE_ENV} or {FALLBACK_ENV}"
    )


def _cache_path(consumer: str) -> Path:
    if consumer not in ALLOWED_CONSUMERS:
        raise ValueError(f"unknown consumer: {consumer}")
    return CACHE_DIR / f"{consumer}.json"


def _read_cache(consumer: str) -> dict[str, Any] | None:
    p = _cache_path(consumer)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("consumer") != consumer:
            return None
        if float(data.get("expires_at", 0)) <= time.time():
            return None
        return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _write_cache(consumer: str, token: str, ttl: int) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    payload = {
        "consumer": consumer,
        "token_fp": token[-12:] if len(token) > 12 else "***",
        "issued_at": time.time(),
        "expires_at": time.time() + ttl,
        "ttl_sec": ttl,
        "token": token,
    }
    p = _cache_path(consumer)
    p.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(p, 0o600)


def get_panel_token(consumer: str, ttl: int = DEFAULT_TTL, force: bool = False) -> str:
    if not force:
        cached = _read_cache(consumer)
        if cached and cached.get("token"):
            _audit("cache_hit", consumer, ttl_left=int(cached["expires_at"] - time.time()))
            return str(cached["token"])
    token = read_master_token()
    _write_cache(consumer, token, ttl)
    _audit("issue", consumer, ttl_sec=ttl)
    return token


def refresh_consumers(consumers: list[str], ttl: int = DEFAULT_TTL) -> None:
    for c in consumers:
        get_panel_token(c, ttl=ttl, force=True)
        _audit("refresh", c, ttl_sec=ttl)


def verify_panel_api(token: str, api_url: str | None = None) -> bool:
    base = (api_url or os.environ.get("REMNA_API_URL") or "https://k9x2m1.conntest.xyz:2053").rstrip(
        "/"
    )
    url = f"{base}/api/hosts"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Remnawave short-lived credential broker")
    ap.add_argument("command", choices=("get", "refresh", "verify", "audit-tail"))
    ap.add_argument("--consumer", default="ru-monitor")
    ap.add_argument("--ttl", type=int, default=DEFAULT_TTL)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--consumers", default="ru-monitor,balancer")
    ap.add_argument("--lines", type=int, default=5)
    args = ap.parse_args()

    if args.command == "get":
        print(get_panel_token(args.consumer, ttl=args.ttl, force=args.force))
        return 0
    if args.command == "refresh":
        refresh_consumers([c.strip() for c in args.consumers.split(",") if c.strip()], ttl=args.ttl)
        print("OK: refreshed", args.consumers)
        return 0
    if args.command == "verify":
        tok = get_panel_token(args.consumer, force=args.force)
        ok = verify_panel_api(tok)
        if ok:
            print("OK: panel API accepts token")
            return 0
        print("FAIL: panel API rejected token", file=sys.stderr)
        return 2
    if args.command == "audit-tail":
        if not AUDIT_LOG.is_file():
            print("(no audit log yet)")
            return 0
        lines = AUDIT_LOG.read_text(encoding="utf-8").splitlines()
        for line in lines[-args.lines :]:
            print(line)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
