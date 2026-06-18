#!/usr/bin/env python3
"""Automated NL Direct Basic connectivity smoke — NL-AUTOMATED-CONNECTIVITY-SMOKE-001.

Starts a local Xray core from the generated DIRECT_BASIC profile, probes
NL_DIRECT_VALIDATION targets through the profile SOCKS inbound, and classifies
PASS / PARTIAL / FAIL / BLOCKED_LOCAL_ENV.

HARD SAFETY:
    * Redacted stdout only (no UUIDs, raw IPs, subscription URLs).
    * Temp runtime config only — never commits profile secrets.
    * No prod/registry mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_OPS = Path(__file__).resolve().parent
ROOT = _OPS.parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from nl_canary_route_classes import (  # noqa: E402
    ROUTE_CLASS_DIRECT_BYPASS,
    ROUTE_CLASS_NL_DIRECT,
    SMOKE_TARGETS_DIRECT_BASIC,
)
from nl_canary_profile_builder import PROFILE_LABEL_DIRECT_BASIC  # noqa: E402
from subscription_fetch import node_label, outbound_endpoint, xray_config_root  # noqa: E402
from validate_happ_importable_profile import validate_nl_canary_variant  # noqa: E402

DEFAULT_PROFILE = ROOT / ".local" / "independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json"

VERDICT_PASS = "PASS"
VERDICT_PARTIAL = "PARTIAL"
VERDICT_FAIL = "FAIL"
VERDICT_BLOCKED = "BLOCKED_LOCAL_ENV"

FAILURE_CLIENT_PROFILE = "CLIENT_PROFILE_ROUTING"
FAILURE_NL_SERVER = "NL_SERVER_PROTOCOL"
FAILURE_LOCAL_ENV = "LOCAL_ENVIRONMENT"

XRAY_BIN_CANDIDATES = (
    os.environ.get("XRAY_BIN"),
    r"C:\Program Files\FlyFrogLLC\Happ\core\xray.exe",
    r"C:\Program Files\FlyFrogLLC\Happ\core\xray",
    "xray",
    "xray.exe",
)

XRAY_ASSET_CANDIDATES = (
    os.environ.get("XRAY_LOCATION_ASSET"),
    r"C:\Program Files\FlyFrogLLC\Happ\core",
    os.path.expandvars(r"%LOCALAPPDATA%\Happ\core"),
    os.path.expandvars(r"%LOCALAPPDATA%\Happ\routing\BenderVPN RU"),
)

CURL_BIN_CANDIDATES = (
    os.environ.get("CURL_BIN"),
    "curl.exe",
    "curl",
)


@dataclass
class ConnectivityTarget:
    target_id: str
    url: str
    route_class: str
    counts_as_nl_proof: bool = True
    expect_http: frozenset[int] = frozenset({200, 204, 301, 302, 303, 307, 308})


@dataclass
class TargetResult:
    target_id: str
    url_host: str
    route_class: str
    ok: bool
    http_code: int | None
    elapsed_ms: int | None
    error_class: str | None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "url_host": self.url_host,
            "route_class": self.route_class,
            "ok": self.ok,
            "http_code": self.http_code,
            "elapsed_ms": self.elapsed_ms,
            "error_class": self.error_class,
            "note": self.note,
        }


@dataclass
class SmokeReport:
    verdict: str
    failure_bucket: str | None = None
    static_validation_ok: bool = False
    core_binary: str | None = None
    core_assets: str | None = None
    socks_ready: bool = False
    core_start_ok: bool = False
    reset_like_errors: int = 0
    target_results: list[TargetResult] = field(default_factory=list)
    nl_proof_pass: int = 0
    nl_proof_total: int = 0
    notes: list[str] = field(default_factory=list)
    endpoint_roles: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "failure_bucket": self.failure_bucket,
            "static_validation_ok": self.static_validation_ok,
            "core_binary": self.core_binary,
            "core_assets": self.core_assets,
            "socks_ready": self.socks_ready,
            "core_start_ok": self.core_start_ok,
            "reset_like_errors": self.reset_like_errors,
            "nl_proof_pass": self.nl_proof_pass,
            "nl_proof_total": self.nl_proof_total,
            "target_results": [t.to_dict() for t in self.target_results],
            "endpoint_roles": self.endpoint_roles,
            "notes": self.notes,
        }


def nl_direct_connectivity_targets() -> list[ConnectivityTarget]:
    """HTTP checks for DIRECT_BASIC NL proof (not direct-bypass RU sites)."""
    return [
        ConnectivityTarget(
            "google_generate_204",
            "https://www.google.com/generate_204",
            ROUTE_CLASS_NL_DIRECT,
        ),
        ConnectivityTarget(
            "gmail",
            "https://mail.google.com/",
            ROUTE_CLASS_NL_DIRECT,
        ),
        ConnectivityTarget(
            "youtube_generate_204",
            "https://www.youtube.com/generate_204",
            ROUTE_CLASS_NL_DIRECT,
        ),
        ConnectivityTarget(
            "x_com",
            "https://x.com/",
            ROUTE_CLASS_NL_DIRECT,
            expect_http=frozenset({200, 204, 301, 302, 303, 307, 308, 403}),
        ),
        ConnectivityTarget(
            "openai",
            "https://openai.com/",
            ROUTE_CLASS_NL_DIRECT,
            expect_http=frozenset({200, 204, 301, 302, 303, 307, 308, 403}),
        ),
        ConnectivityTarget(
            "yandex_ru_control",
            "https://yandex.ru/",
            ROUTE_CLASS_DIRECT_BYPASS,
            counts_as_nl_proof=False,
            expect_http=frozenset({200, 204, 301, 302, 303, 307, 308, 403}),
        ),
    ]


def endpoint_token(ip: str, port: str | int) -> str:
    digest = hashlib.sha1(ip.encode("utf-8")).hexdigest()[:8]
    return f"ep_{digest}:{port}"


def _first_executable(candidates: tuple[str | None, ...]) -> str | None:
    for raw in candidates:
        if not raw:
            continue
        p = Path(raw)
        if p.is_file():
            return str(p)
        found = shutil_which(raw)
        if found:
            return found
    return None


def shutil_which(cmd: str) -> str | None:
    paths = os.environ.get("PATH", "").split(os.pathsep)
    exts = [""]
    if os.name == "nt":
        exts = os.environ.get("PATHEXT", ".EXE;.CMD").split(";")
    for base in paths:
        for ext in exts:
            candidate = Path(base) / f"{cmd}{ext}"
            if candidate.is_file():
                return str(candidate)
    return None


def _first_asset_dir(candidates: tuple[str | None, ...]) -> str | None:
    for raw in candidates:
        if not raw:
            continue
        p = Path(raw)
        if p.is_dir() and (p / "geosite.dat").is_file():
            return str(p)
        if p.is_dir() and any(p.glob("*.dat")):
            return str(p)
    return None


def load_profile(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return xray_config_root(doc)


def static_validate_profile(cfg: dict[str, Any]) -> tuple[bool, list[str]]:
    val = validate_nl_canary_variant(cfg, "direct_basic")
    errors = list(val.errors)
    remarks = str(cfg.get("remarks") or "")
    if PROFILE_LABEL_DIRECT_BASIC not in remarks:
        errors.append("remarks mismatch for DIRECT_BASIC")
    return not errors, errors


def socks_inbound(cfg: dict[str, Any]) -> tuple[str, int]:
    for ib in cfg.get("inbounds") or []:
        if (ib.get("protocol") or "").lower() == "socks":
            return str(ib.get("listen") or "127.0.0.1"), int(ib.get("port") or 10808)
    return "127.0.0.1", 10808


def summarize_outbound_roles(cfg: dict[str, Any]) -> dict[str, int]:
    roles: dict[str, int] = {}
    for ob in cfg.get("outbounds") or []:
        if ob.get("protocol") != "vless":
            continue
        tag = str(ob.get("tag") or "?")
        addr, port = outbound_endpoint(ob)
        label = node_label(addr, port) if addr else "UNKNOWN"
        roles[label] = roles.get(label, 0) + 1
    return roles


def wait_for_port(host: str, port: int, *, timeout_s: float = 12.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def classify_curl_failure(stderr: str, stdout: str) -> str:
    text = f"{stderr}\n{stdout}".lower()
    if "connection was reset" in text or "recv failure" in text and "reset" in text:
        return "connection_reset"
    if "ssl connect error" in text or "ssl routines" in text or "certificate" in text:
        return "tls_handshake"
    if "failed to connect" in text and "127.0.0.1" in text:
        return "proxy_unreachable"
    if "could not resolve host" in text or "resolving timed out" in text:
        return "dns_failure"
    if "timed out" in text or "timeout" in text or "operation timed out" in text:
        return "timeout"
    if "proxy" in text and "refused" in text:
        return "proxy_unreachable"
    return "http_or_unknown"


def classify_overall_verdict(
    *,
    nl_pass: int,
    nl_total: int,
    core_ok: bool,
    reset_errors: int,
) -> tuple[str, str | None]:
    if not core_ok:
        return VERDICT_FAIL, FAILURE_LOCAL_ENV
    if nl_total == 0:
        return VERDICT_FAIL, FAILURE_CLIENT_PROFILE
    ratio = nl_pass / nl_total
    if ratio >= 0.6 and nl_pass >= 3:
        return VERDICT_PASS, None
    if nl_pass >= 1:
        bucket = FAILURE_NL_SERVER if reset_errors >= 2 else FAILURE_CLIENT_PROFILE
        return VERDICT_PARTIAL, bucket
    bucket = FAILURE_NL_SERVER if reset_errors >= 2 else FAILURE_CLIENT_PROFILE
    return VERDICT_FAIL, bucket


def curl_through_proxy(
    curl_bin: str,
    proxy_url: str,
    target: ConnectivityTarget,
    *,
    timeout_s: int = 20,
) -> TargetResult:
    host = urlparse(target.url).hostname or target.url
    cmd = [
        curl_bin,
        "-sS",
        "-o",
        os.devnull,
        "-w",
        "%{http_code}",
        "--max-time",
        str(timeout_s),
        "-x",
        proxy_url,
        target.url,
    ]
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s + 5)
    except subprocess.TimeoutExpired:
        return TargetResult(
            target_id=target.target_id,
            url_host=host,
            route_class=target.route_class,
            ok=False,
            http_code=None,
            elapsed_ms=None,
            error_class="timeout",
            note="curl timeout",
        )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    stderr = proc.stderr or ""
    stdout = (proc.stdout or "").strip()
    http_code: int | None = None
    if stdout.isdigit():
        http_code = int(stdout)
    ok = proc.returncode == 0 and http_code is not None and http_code in target.expect_http
    err_class = None if ok else classify_curl_failure(stderr, stdout)
    note = ""
    if not ok and http_code is not None:
        note = f"http={http_code}"
    elif not ok and stderr:
        note = stderr.strip().splitlines()[-1][:120]
    return TargetResult(
        target_id=target.target_id,
        url_host=host,
        route_class=target.route_class,
        ok=ok,
        http_code=http_code,
        elapsed_ms=elapsed_ms,
        error_class=err_class,
        note=note,
    )


def run_smoke(
    profile_path: Path,
    *,
    skip_live: bool = False,
    startup_wait_s: float = 12.0,
) -> SmokeReport:
    report = SmokeReport(verdict=VERDICT_BLOCKED, failure_bucket=FAILURE_LOCAL_ENV)
    report.notes.append(f"smoke_targets_doc={SMOKE_TARGETS_DIRECT_BASIC}")

    if not profile_path.is_file():
        report.notes.append(f"profile missing: {profile_path.name}")
        return report

    cfg = load_profile(profile_path)
    static_ok, static_errors = static_validate_profile(cfg)
    report.static_validation_ok = static_ok
    report.endpoint_roles = summarize_outbound_roles(cfg)
    if not static_ok:
        report.verdict = VERDICT_FAIL
        report.failure_bucket = FAILURE_CLIENT_PROFILE
        report.notes.extend([f"static: {e}" for e in static_errors[:6]])
        return report

    if skip_live:
        report.verdict = VERDICT_PASS if static_ok else VERDICT_FAIL
        report.notes.append("live core skipped (--static-only)")
        return report

    xray_bin = _first_executable(XRAY_BIN_CANDIDATES)
    curl_bin = _first_executable(CURL_BIN_CANDIDATES)
    assets = _first_asset_dir(XRAY_ASSET_CANDIDATES)
    report.core_binary = xray_bin
    report.core_assets = assets

    if not xray_bin:
        report.notes.append("LOCAL_CORE_UNAVAILABLE: set XRAY_BIN to xray executable")
        return report
    if not curl_bin:
        report.notes.append("LOCAL_CORE_UNAVAILABLE: curl not found")
        return report

    host, port = socks_inbound(cfg)
    proxy_url = f"socks5h://{host}:{port}"

    with tempfile.TemporaryDirectory(prefix="nl-smoke-") as tmp:
        cfg_path = Path(tmp) / "runtime.json"
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        env = os.environ.copy()
        if assets:
            env["XRAY_LOCATION_ASSET"] = assets
        proc = subprocess.Popen(
            [xray_bin, "run", "-config", str(cfg_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        report.core_start_ok = True
        try:
            report.socks_ready = wait_for_port(host, port, timeout_s=startup_wait_s)
            if not report.socks_ready:
                err_tail = ""
                if proc.stderr:
                    try:
                        err_tail = proc.stderr.read(4000) or ""
                    except Exception:
                        pass
                if proc.poll() is not None:
                    report.core_start_ok = False
                report.verdict = VERDICT_FAIL
                report.failure_bucket = FAILURE_LOCAL_ENV
                report.notes.append("SOCKS inbound not ready")
                if "geosite" in err_tail.lower():
                    report.notes.append("hint: XRAY_LOCATION_ASSET may be missing geosite.dat")
                return report

            targets = nl_direct_connectivity_targets()
            nl_total = sum(1 for t in targets if t.counts_as_nl_proof)
            report.nl_proof_total = nl_total
            reset_like = 0

            for target in targets:
                result = curl_through_proxy(curl_bin, proxy_url, target)
                report.target_results.append(result)
                if result.error_class == "connection_reset":
                    reset_like += 1
                if target.counts_as_nl_proof and result.ok:
                    report.nl_proof_pass += 1

            report.reset_like_errors = reset_like
            verdict, bucket = classify_overall_verdict(
                nl_pass=report.nl_proof_pass,
                nl_total=nl_total,
                core_ok=report.core_start_ok and report.socks_ready,
                reset_errors=reset_like,
            )
            report.verdict = verdict
            report.failure_bucket = bucket

            if report.nl_proof_pass == 0 and reset_like >= 2:
                report.notes.append("dominant connection_reset — likely NL REALITY/server path")
            bypass = next((t for t in report.target_results if t.target_id == "yandex_ru_control"), None)
            if bypass and bypass.ok and report.nl_proof_pass == 0:
                report.notes.append("DIRECT_BYPASS_MASKS_SMOKE: RU control ok but NL proof targets failed")

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return report


def print_human(report: SmokeReport) -> None:
    print(f"verdict={report.verdict}")
    if report.failure_bucket:
        print(f"failure_bucket={report.failure_bucket}")
    print(f"static_validation_ok={report.static_validation_ok}")
    print(f"core_binary={report.core_binary or 'MISSING'}")
    print(f"core_assets={report.core_assets or 'MISSING'}")
    print(f"socks_ready={report.socks_ready}")
    print(f"nl_proof_pass={report.nl_proof_pass}/{report.nl_proof_total}")
    print(f"endpoint_roles={json.dumps(report.endpoint_roles, ensure_ascii=False)}")
    print("targets:")
    for t in report.target_results:
        print(
            f"  {t.target_id}: ok={t.ok} http={t.http_code} "
            f"class={t.route_class} err={t.error_class} ms={t.elapsed_ms}"
        )
    for note in report.notes:
        print(f"note: {note}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NL Direct Basic automated connectivity smoke")
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="DIRECT_BASIC importable profile JSON",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="validate profile only; do not start local core",
    )
    args = parser.parse_args(argv)

    report = run_smoke(args.profile, skip_live=args.static_only)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print_human(report)

    if report.verdict == VERDICT_BLOCKED:
        return 2
    if report.verdict == VERDICT_PASS:
        return 0
    if report.verdict == VERDICT_PARTIAL:
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
