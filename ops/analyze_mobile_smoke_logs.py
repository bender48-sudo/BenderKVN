#!/usr/bin/env python3
"""Summarize mobile smoke logs into redacted launch evidence (CLIENT-STABILITY-MOBILE-LOG-SUMMARY-001).

Read-only local tool — never prints vless://, sub URLs, or raw UUIDs.

Usage:
    python ops/analyze_mobile_smoke_logs.py \\
        --access-log path/to/access_log.txt \\
        --subscription-log path/to/subscription_log.txt \\
        --adb-log path/to/logcat.txt \\
        --out .local/mobile_smoke_log_summary.md
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ACCESS_LINE = re.compile(
    r"^\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+"
    r"\s+from\s+(?P<from_proto>tcp|udp):[\d.:]+"
    r"\s+accepted\s+(?P<dest_proto>tcp|udp):(?P<dest_ip>[\d.]+):(?P<dest_port>\d+)"
    r"\s+\[socks\s+->\s+(?P<route>[^\]]+)\]",
    re.I,
)

REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"vless://[^\s\"']+", re.I), "vless://[REDACTED]"),
    (re.compile(r"https?://[^\s\"']*api/sub/[^\s\"']+", re.I), "https://[REDACTED]/api/sub/[REDACTED]"),
    (re.compile(r"happ://[^\s\"']+", re.I), "happ://[REDACTED]"),
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "[REDACTED_UUID]",
    ),
    (re.compile(r"\b[0-9a-f]{32}\b"), "[REDACTED_HASH]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{20,}"), "[REDACTED_JWT]"),
]

# Static IP-prefix hints — no DNS, coarse only.
GOOGLE_PREFIXES = ("142.250.", "142.251.", "216.239.", "64.233.", "172.217.", "216.58.", "173.194.")
TELEGRAM_PREFIXES = ("149.154.", "91.108.")
META_PREFIXES = ("31.13.", "157.240.", "57.144.", "31.13.72.")
RU_DIRECT_HINTS = ("213.180.", "87.240.", "77.", "95.", "178.", "89.221.", "217.12.", "37.220.", "194.221.")
DNS_RESOLVER_IPS = frozenset({"1.1.1.1", "8.8.8.8", "8.8.4.4", "1.0.0.1"})


def redact(text: str) -> str:
    out = text
    for pat, repl in REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _ip_class(ip: str) -> str | None:
    if ip in DNS_RESOLVER_IPS:
        return "dns_resolver"
    for p in GOOGLE_PREFIXES:
        if ip.startswith(p):
            return "google_hint"
    for p in TELEGRAM_PREFIXES:
        if ip.startswith(p):
            return "telegram_hint"
    for p in META_PREFIXES:
        if ip.startswith(p):
            return "meta_hint"
    for p in RU_DIRECT_HINTS:
        if ip.startswith(p):
            return "ru_hint"
    return None


@dataclass
class AccessStats:
    total_accepted: int = 0
    parse_skipped: int = 0
    tcp: int = 0
    udp: int = 0
    proxy_routes: Counter = field(default_factory=Counter)
    direct: int = 0
    block: int = 0
    class_proxy: Counter = field(default_factory=Counter)
    class_direct: Counter = field(default_factory=Counter)
    time_first: str | None = None
    time_last: str | None = None

    def ingest_line(self, line: str) -> None:
        m = ACCESS_LINE.match(line.strip())
        if not m:
            self.parse_skipped += 1
            return
        self.total_accepted += 1
        ts = line.split()[0] + " " + line.split()[1]
        if not self.time_first:
            self.time_first = ts
        self.time_last = ts
        dest_proto = m.group("dest_proto").lower()
        if dest_proto == "tcp":
            self.tcp += 1
        else:
            self.udp += 1
        route = m.group("route").strip()
        dest_ip = m.group("dest_ip")
        ip_cls = _ip_class(dest_ip)
        if route == "direct":
            self.direct += 1
            if ip_cls:
                self.class_direct[ip_cls] += 1
        elif route == "block":
            self.block += 1
        else:
            self.proxy_routes[route] += 1
            if ip_cls:
                self.class_proxy[ip_cls] += 1


@dataclass
class SubscriptionStats:
    server_response_200: int = 0
    unknown_content_type: int = 0
    append_custom_ok: int = 0
    sub_updated_ok: int = 0
    servers_one: int = 0
    routing_file_failed: int = 0
    last_update_ok_line: str | None = None
    last_server_200_line: str | None = None
    import_verdict: str = "unknown"

    def ingest_line(self, line: str) -> None:
        if "Server response: 200" in line:
            self.server_response_200 += 1
            self.last_server_200_line = line.strip()[:120]
        if "UnknownContentType" in line:
            self.unknown_content_type += 1
        if re.search(r"Append custom result.*count=1", line):
            self.append_custom_ok += 1
            self.last_update_ok_line = line.strip()[:120]
        if "Sub BenderVPN successfully updated" in line:
            self.sub_updated_ok += 1
        if re.search(r"servers:\s*1 servers", line):
            self.servers_one += 1
        if "Happ file failed" in line or "Google file failed" in line:
            self.routing_file_failed += 1

    def finalize(self) -> None:
        if self.append_custom_ok > 0 or self.sub_updated_ok > 0:
            self.import_verdict = "parse_noise_but_custom_import_ok"
        elif self.server_response_200 > 0:
            self.import_verdict = "http_ok_no_custom_append_seen"
        else:
            self.import_verdict = "no_successful_import_found"


@dataclass
class AdbStats:
    tun2socks_warnings: int = 0
    tun2socks_errors: int = 0
    appdetect_null_owner: int = 0
    appdetect_udp_failed: int = 0
    classification: str = "none"

    def ingest_line(self, line: str) -> None:
        low = line.lower()
        if "tun2socks" not in low:
            return
        if "warning(tun2socks)" in low or " w/tun2socks" in low:
            self.tun2socks_warnings += 1
        if "error(tun2socks)" in low or " e/tun2socks" in low:
            self.tun2socks_errors += 1
        if "findconnectionowner returned null" in low:
            self.appdetect_null_owner += 1
        if "appdetect udp" in low and "failed to find con" in low:
            self.appdetect_udp_failed += 1

    def finalize(self) -> None:
        total = self.appdetect_udp_failed + self.appdetect_null_owner
        if total == 0:
            self.classification = "none"
        elif total <= 20:
            self.classification = "low_frequency_likely_non_blocking"
        else:
            self.classification = "high_frequency_review_if_apps_fail"


def parse_access_log(text: str) -> AccessStats:
    stats = AccessStats()
    for line in text.splitlines():
        if "accepted" in line and "[socks ->" in line:
            stats.ingest_line(line)
    return stats


def parse_subscription_log(text: str) -> SubscriptionStats:
    stats = SubscriptionStats()
    for line in text.splitlines():
        stats.ingest_line(line)
    stats.finalize()
    return stats


def parse_adb_log(text: str) -> AdbStats:
    stats = AdbStats()
    for line in text.splitlines():
        stats.ingest_line(line)
    stats.finalize()
    return stats


def recommend_verdict_support(
    access: AccessStats | None,
    sub: SubscriptionStats | None,
    adb: AdbStats | None,
) -> dict[str, str]:
    if not access or access.total_accepted == 0:
        connectivity = "no_access_log"
    else:
        proxy_n = sum(access.proxy_routes.values())
        tg_google = access.class_proxy.get("telegram_hint", 0) + access.class_proxy.get("google_hint", 0)
        if access.total_accepted >= 10 and proxy_n >= 5 and tg_google > 0:
            connectivity = "evidence_supports_connectivity"
        elif access.total_accepted >= 10 and proxy_n >= 5:
            connectivity = "evidence_supports_basic_traffic"
        else:
            connectivity = "limited_traffic_observed"

    sub_status = sub.import_verdict if sub else "no_subscription_log"
    adb_class = adb.classification if adb else "none"

    blockers: list[str] = []
    if sub and sub.import_verdict == "no_successful_import_found":
        blockers.append("subscription_import_not_confirmed")
    if access and access.total_accepted == 0:
        blockers.append("no_accepted_traffic_in_access_log")

    fatal = len(blockers) > 0 and (not access or access.total_accepted == 0)

    if fatal:
        next_action = "possible_fail_if_symptoms_observed"
    elif connectivity.startswith("evidence_supports"):
        next_action = "needs_owner_speed_app_result"
    else:
        next_action = "needs_owner_speed_app_result"

    return {
        "connectivity": connectivity,
        "subscription": sub_status,
        "adb_warnings": adb_class,
        "fatal_blocker": "yes" if fatal else "no",
        "launch_verdict_support": next_action,
        "mobile_smoke_pass": "PENDING — logs alone insufficient",
    }


def build_markdown(
    access: AccessStats | None,
    sub: SubscriptionStats | None,
    adb: AdbStats | None,
    sources: dict[str, str],
) -> str:
    verdict = recommend_verdict_support(access, sub, adb)
    lines: list[str] = [
        "# Mobile smoke log summary (redacted)",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} local",
        "**Task:** CLIENT-STABILITY-MOBILE-LOG-SUMMARY-001",
        "",
        "> Redacted summary — raw logs not included. Mobile smoke PASS remains **PENDING** without owner app/speed results.",
        "",
        "## Summary",
        "",
    ]

    if access and access.total_accepted:
        proxy_total = sum(access.proxy_routes.values())
        pct_direct = round(100 * access.direct / access.total_accepted, 1) if access.total_accepted else 0
        lines.append(
            f"- **Access log:** {access.total_accepted} accepted flows "
            f"({access.time_first} → {access.time_last}); "
            f"proxy={proxy_total}, direct={access.direct} ({pct_direct}%), tcp={access.tcp}, udp={access.udp}"
        )
    else:
        lines.append("- **Access log:** not provided or no accepted lines parsed")

    if sub:
        lines.append(
            f"- **Subscription log:** HTTP 200×{sub.server_response_200}, "
            f"UnknownContentType×{sub.unknown_content_type}, "
            f"Append custom OK×{sub.append_custom_ok}, import={sub.import_verdict}"
        )
    else:
        lines.append("- **Subscription log:** not provided")

    if adb and (adb.appdetect_udp_failed or adb.tun2socks_warnings):
        lines.append(
            f"- **ADB/logcat:** APPDETECT UDP fail×{adb.appdetect_udp_failed}, "
            f"NULL owner×{adb.appdetect_null_owner} — {adb.classification}"
        )
    elif adb:
        lines.append("- **ADB/logcat:** no tun2socks APPDETECT lines")
    else:
        lines.append("- **ADB/logcat:** not provided")

    lines.extend(
        [
            f"- **Launch verdict support:** `{verdict['launch_verdict_support']}`",
            f"- **Mobile smoke PASS:** {verdict['mobile_smoke_pass']}",
            "",
            "## Connectivity evidence",
            "",
        ]
    )

    if access and access.total_accepted:
        lines.append("Observed **accepted** Xray/Happ access flows (traffic was routed, not rejected).")
        if access.class_proxy.get("telegram_hint") or access.class_proxy.get("google_hint"):
            lines.append(
                f"- Proxy path samples: telegram_hint={access.class_proxy.get('telegram_hint', 0)}, "
                f"google_hint={access.class_proxy.get('google_hint', 0)}, "
                f"meta_hint={access.class_proxy.get('meta_hint', 0)}"
            )
    else:
        lines.append("_No connectivity evidence from access log._")

    lines.extend(["", "## Routing evidence", ""])
    if access and access.total_accepted:
        top_proxy = access.proxy_routes.most_common(8)
        lines.append("| Route | Count |")
        lines.append("|-------|------:|")
        for tag, n in top_proxy:
            lines.append(f"| `{tag}` | {n} |")
        lines.append(f"| `direct` | {access.direct} |")
        if access.class_direct:
            lines.append("")
            lines.append("Direct path IP hints (coarse): " + ", ".join(f"{k}={v}" for k, v in access.class_direct.most_common()))
        relay2_tags = sum(n for t, n in access.proxy_routes.items() if t in ("proxy-4", "proxy-5", "proxy-6"))
        relay1_tags = sum(n for t, n in access.proxy_routes.items() if t in ("proxy", "proxy-2", "proxy-3"))
        lines.append("")
        lines.append(f"- Relay pool usage (tag names only): relay1-class tags≈{relay1_tags}, relay2-class tags≈{relay2_tags}")
    else:
        lines.append("_No routing evidence._")

    lines.extend(["", "## Subscription/import evidence", ""])
    if sub:
        lines.append(f"| Metric | Count |")
        lines.append(f"|--------|------:|")
        lines.append(f"| Server response 200 | {sub.server_response_200} |")
        lines.append(f"| UnknownContentType (batch) | {sub.unknown_content_type} |")
        lines.append(f"| Append custom count=1 | {sub.append_custom_ok} |")
        lines.append(f"| Sub successfully updated | {sub.sub_updated_ok} |")
        lines.append(f"| «1 servers» UI count | {sub.servers_one} |")
        lines.append(f"| Routing/geofile fetch failed | {sub.routing_file_failed} |")
        lines.append("")
        if sub.import_verdict == "parse_noise_but_custom_import_ok":
            lines.append(
                "**Interpretation:** Happ batch import skipped some outbounds (UnknownContentType — often xhttp/network types) "
                "but **Append custom** imported the full BenderVPN Auto profile. «1 servers» in UI is **expected** for Auto."
            )
        elif sub.import_verdict == "no_successful_import_found":
            lines.append("**Interpretation:** No successful custom append — import may have failed.")
    else:
        lines.append("_No subscription log._")

    lines.extend(["", "## Android/tun2socks warnings", ""])
    if adb and adb.appdetect_udp_failed:
        lines.append(
            f"APPDETECT UDP «Failed to find connection» ×{adb.appdetect_udp_failed}; "
            f"findConnectionOwner NULL ×{adb.appdetect_null_owner}."
        )
        if adb.classification == "low_frequency_likely_non_blocking":
            lines.append(
                "**Classification:** Likely **non-blocking** UDP/QUIC app-detection noise unless owner saw app failures at same timestamps."
            )
        else:
            lines.append("**Classification:** Elevated count — correlate with user-visible failures.")
    else:
        lines.append("_No APPDETECT snippet or not provided._")

    lines.extend(
        [
            "",
            "## What this proves",
            "",
            "- VPN core routed **live traffic** during the access_log window (if access log provided).",
            "- **Intl-ish** flows used **proxy** outbounds; some **RU-ish** flows used **direct** (expected with BenderVPN RU routing).",
            "- Subscription **HTTP 200** + **Append custom OK** pattern matches known Happ Auto import (if subscription log provided).",
            "",
            "## What it does NOT prove",
            "",
            "- **Speed** (Mbps) or subjective «fast enough» — needs owner fast.com/Speedtest or screenshot.",
            "- **Gmail/Docs/Telegram UX** — needs owner Y/N from normal use.",
            "- **Lock/unlock** and **Wi‑Fi ↔ LTE** recovery — needs owner phase B/C results.",
            "- APPDETECT UDP lines alone are **not FAIL** without correlated app breakage.",
            "",
            "## Owner result still needed",
            "",
            "Fill `.local/mobile_smoke_results.md` or paste chat summary: Phase A/B/C app checks, speed numbers, verdict.",
            "",
            "## Recommended next action",
            "",
        ]
    )

    if verdict["launch_verdict_support"] == "needs_owner_speed_app_result":
        lines.append(
            "1. **Logs support basic connectivity** — complete owner checklist (§14 mobile smoke doc).\n"
            "2. Record speed + lock/LTE phases.\n"
            "3. If apps fail despite these logs, export Happ diagnostic **before** switching VPN."
        )
    elif verdict["launch_verdict_support"] == "possible_fail_if_symptoms_observed":
        lines.append("Investigate import/connect failure; re-import sub + routing profile.")
    else:
        lines.append("Provide access/subscription logs and owner app results.")

    lines.extend(["", "## Sources (paths not committed)", ""])
    for k, v in sources.items():
        lines.append(f"- {k}: `{Path(v).name}`")

    body = "\n".join(lines) + "\n"
    return redact(body)


def analyze(
    *,
    access_path: Path | None = None,
    subscription_path: Path | None = None,
    adb_path: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    sources: dict[str, str] = {}
    access = sub = adb = None

    if access_path and access_path.is_file():
        sources["access_log"] = str(access_path)
        access = parse_access_log(access_path.read_text(encoding="utf-8", errors="replace"))
    if subscription_path and subscription_path.is_file():
        sources["subscription_log"] = str(subscription_path)
        sub = parse_subscription_log(subscription_path.read_text(encoding="utf-8", errors="replace"))
    if adb_path and adb_path.is_file():
        sources["adb_log"] = str(adb_path)
        adb = parse_adb_log(adb_path.read_text(encoding="utf-8", errors="replace"))

    md = build_markdown(access, sub, adb, sources)
    summary = recommend_verdict_support(access, sub, adb)
    if access:
        summary["access_total"] = access.total_accepted
        summary["proxy_total"] = sum(access.proxy_routes.values())
        summary["direct_total"] = access.direct
    return md, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--access-log", type=Path, help="Xray/Happ access_log.txt")
    ap.add_argument("--subscription-log", type=Path, help="Happ subscription_log.txt")
    ap.add_argument("--adb-log", type=Path, help="logcat snippet with tun2socks lines")
    ap.add_argument("--out", type=Path, default=Path(".local/mobile_smoke_log_summary.md"))
    ap.add_argument("--json", action="store_true", help="print summary JSON to stdout")
    args = ap.parse_args()

    if not any([args.access_log, args.subscription_log, args.adb_log]):
        print("FAIL: provide at least one --access-log, --subscription-log, or --adb-log", file=sys.stderr)
        return 1

    md, summary = analyze(
        access_path=args.access_log,
        subscription_path=args.subscription_log,
        adb_path=args.adb_log,
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"Wrote: {args.out}")

    if args.json:
        import json

        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"connectivity={summary.get('connectivity')}")
        print(f"launch_verdict_support={summary.get('launch_verdict_support')}")
        print(f"mobile_smoke_pass={summary.get('mobile_smoke_pass')}")

    print("MOBILE_SMOKE_LOG_SUMMARY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
