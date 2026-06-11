#!/usr/bin/env python3
"""Analyze Happ report.zip for CLIENT-SMOKE-002 Proxy mode diagnostics.

Read-only local tool — does not touch prod. Redacts secrets in all output.

Usage:
    python ops/analyze_happ_report_proxy.py path/to/report.zip
    python ops/analyze_happ_report_proxy.py path/to/report.zip --json
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Files commonly present in Happ report.zip (INCIDENT-DIAG-003-004 inventory).
KNOWN_LOG_FILES = (
    "happd.log",
    "application_log.txt",
    "subscription_log.txt",
    "tun_log.txt",
    "access_log.txt",
    "error_log.txt",
    "versions.txt",
)

REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"vless://[^\s\"']+", re.I), "vless://[REDACTED]"),
    (re.compile(r"https?://[^\s\"']*api/sub/[^\s\"']+", re.I), "https://[REDACTED]/api/sub/[REDACTED]"),
    (re.compile(r"happ://[^\s\"']+", re.I), "happ://[REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{20,}"), "[REDACTED_JWT]"),
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "[REDACTED_UUID]",
    ),
]

# Signal patterns → classification hints (Track B).
SIGNAL_RULES: list[tuple[str, re.Pattern[str], str, str]] = [
    (
        "unknown_content_type",
        re.compile(r"UnknownContentType|lastParseError", re.I),
        "C",
        "Happ batch import parse failure",
    ),
    (
        "zero_servers",
        re.compile(r"0 servers|ImportResult\(count=0", re.I),
        "C",
        "Subscription import yielded zero servers",
    ),
    (
        "geosite_error",
        re.compile(r"geosite\.dat|geosite:|code not found in geosite|Geo file", re.I),
        "C",
        "Geosite/geodata error",
    ),
    (
        "localhost_dns",
        re.compile(r"localhost.*dns|dns.*localhost|127\.0\.0\.1:53|address.*localhost", re.I),
        "A",
        "Localhost DNS resolver referenced or failed",
    ),
    (
        "dns_failure",
        re.compile(r"Cannot set DNS|DNS.*fail|lookup.*fail|i/o timeout.*dns", re.I),
        "A",
        "DNS configuration or resolution failure",
    ),
    (
        "socks_inbound",
        re.compile(r"socks|127\.0\.0\.1:\d+|inbound.*socks|http.*inbound", re.I),
        "B",
        "Local SOCKS/HTTP inbound activity (presence/absence context)",
    ),
    (
        "direct_fallback",
        re.compile(r"\[socks\s*->\s*direct\]|fallbackTag.*direct|outboundTag.*direct", re.I),
        "D",
        "Traffic or config using direct bypass",
    ),
    (
        "proxy_routing",
        re.compile(r"\[socks\s*>>\s*proxy\]|GlobalProxy|routing profile", re.I),
        "D",
        "Proxy routing path in logs",
    ),
    (
        "reality_tls",
        re.compile(r"REALITY|TLS handshake|certificate|X509", re.I),
        "E",
        "TLS/Reality layer error",
    ),
    (
        "connect_refused",
        re.compile(r"connection refused|i/o timeout|deadline exceeded", re.I),
        "E",
        "Outbound connect failure",
    ),
    (
        "tun_mode",
        re.compile(r"happ-tun|sing-box-tun|TUN process|tun mode", re.I),
        "G",
        "TUN lifecycle in report — verify Proxy-mode test setup",
    ),
    (
        "balancer",
        re.compile(r"balancer|Super_Balancer|Intl_Direct|Intl_Stealth", re.I),
        "D",
        "Balancer/routing tags in logs",
    ),
]


def redact_text(text: str) -> str:
    out = text
    for pat, repl in REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def read_zip_text(zf: zipfile.ZipFile, name: str, *, limit: int = 500_000) -> str:
    try:
        raw = zf.read(name)
    except KeyError:
        return ""
    text = raw.decode("utf-8", errors="replace")
    if len(text) > limit:
        text = text[:limit] + "\n... [truncated]"
    return text


def find_member(zf: zipfile.ZipFile, basename: str) -> str | None:
    for name in zf.namelist():
        if name.replace("\\", "/").rstrip("/").endswith(basename):
            return name
    return None


def count_matches(text: str, pattern: re.Pattern[str]) -> int:
    return len(pattern.findall(text))


@dataclass
class SignalHit:
    signal_id: str
    classification: str
    description: str
    count: int
    sample_lines: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    zip_path: str
    files_found: list[str]
    signals: list[SignalHit]
    classifications: list[str]
    versions_excerpt: str
    notes: list[str]


def analyze_report_zip(path: Path) -> AnalysisResult:
    if not path.is_file():
        raise FileNotFoundError(path)

    combined = ""
    files_found: list[str] = []
    versions_excerpt = ""

    with zipfile.ZipFile(path, "r") as zf:
        for basename in KNOWN_LOG_FILES:
            member = find_member(zf, basename)
            if not member:
                continue
            text = read_zip_text(zf, member)
            files_found.append(basename)
            combined += f"\n--- {basename} ---\n{text}"
            if basename == "versions.txt":
                versions_excerpt = redact_text(text.strip()[:800])

    signals: list[SignalHit] = []
    for sig_id, pattern, cls, desc in SIGNAL_RULES:
        n = count_matches(combined, pattern)
        if n == 0:
            continue
        samples: list[str] = []
        for line in combined.splitlines():
            if pattern.search(line):
                samples.append(redact_text(line.strip()[:240]))
            if len(samples) >= 3:
                break
        signals.append(
            SignalHit(
                signal_id=sig_id,
                classification=cls,
                description=desc,
                count=n,
                sample_lines=samples,
            )
        )

    # Primary classification: most frequent non-G signal; prefer C/A/B for Proxy track.
    priority = {"C": 0, "A": 1, "B": 2, "D": 3, "E": 4, "F": 5, "G": 6}
    by_class: dict[str, int] = {}
    for s in signals:
        by_class[s.classification] = by_class.get(s.classification, 0) + s.count

    classifications: list[str] = []
    if not signals:
        classifications = ["G"]
    else:
        ranked = sorted(by_class.items(), key=lambda kv: (-kv[1], priority.get(kv[0], 99)))
        classifications = [c for c, _ in ranked[:3]]

    notes: list[str] = []
    if not files_found:
        notes.append("No known log files found in zip — wrong artifact or empty export")
    if "tun_mode" in {s.signal_id for s in signals} and "socks_inbound" not in {s.signal_id for s in signals}:
        notes.append("TUN signals present — confirm owner disabled TUN for Proxy test")
    if "zero_servers" in {s.signal_id for s in signals} or "unknown_content_type" in {s.signal_id for s in signals}:
        notes.append("Import integrity issue likely — see CLIENT-SMOKE-002 class C")

    return AnalysisResult(
        zip_path=str(path),
        files_found=files_found,
        signals=signals,
        classifications=classifications,
        versions_excerpt=versions_excerpt,
        notes=notes,
    )


def result_to_dict(result: AnalysisResult) -> dict:
    return {
        "zip_path": result.zip_path,
        "files_found": result.files_found,
        "primary_classifications": result.classifications,
        "classification_legend": {
            "A": "DNS localhost / Proxy DNS",
            "B": "Missing local inbound / sniffing",
            "C": "Happ import / profile integrity",
            "D": "Routing profile not applied in Proxy",
            "E": "Relay / VLESS connection",
            "F": "Generic Windows / system proxy",
            "G": "Insufficient evidence",
        },
        "signals": [
            {
                "id": s.signal_id,
                "class": s.classification,
                "description": s.description,
                "count": s.count,
                "sample_lines": s.sample_lines,
            }
            for s in result.signals
        ],
        "versions_excerpt": result.versions_excerpt,
        "notes": result.notes,
    }


def print_human(result: AnalysisResult) -> None:
    print(f"CLIENT_SMOKE_002_PROXY_ANALYSIS zip={Path(result.zip_path).name}")
    print(f"files_found: {', '.join(result.files_found) or '(none)'}")
    if result.versions_excerpt:
        print(f"versions:\n{result.versions_excerpt}\n")
    print(f"primary_classifications: {', '.join(result.classifications)}")
    for s in result.signals:
        print(f"\n[{s.classification}] {s.signal_id} (×{s.count}) — {s.description}")
        for line in s.sample_lines:
            print(f"  | {line}")
    for note in result.notes:
        print(f"\nNOTE: {note}")
    print("\nAll samples above are redacted. Do not commit raw report.zip.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze Happ report.zip for Proxy mode (CLIENT-SMOKE-002)")
    ap.add_argument("report_zip", type=Path, help="Path to Happ report.zip (local, not in repo)")
    ap.add_argument("--json", action="store_true", help="Machine-readable redacted JSON")
    args = ap.parse_args()

    try:
        result = analyze_report_zip(args.report_zip.resolve())
    except FileNotFoundError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    except zipfile.BadZipFile:
        print("FAIL: not a valid zip file", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
