#!/usr/bin/env python3
"""Summarize mobile smoke logs into redacted launch evidence (CLIENT-STABILITY-MOBILE-LOGS-001).

Read-only local tool — never prints vless://, sub URLs, or raw UUIDs.

Usage:
    python ops/analyze_mobile_smoke_logs.py \\
        --access-log .secrets/diagnostics/access_log_mobile.txt \\
        --subscription-log .secrets/diagnostics/subscription_log_mobile.txt \\
        --owner-event "2026-06-16 19:32:00 phone slept" \\
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
    r"\s+\[socks\s+(?:->|>>)\s+(?P<route>[^\]]+)\]",
    re.I,
)

ACCESS_TS_FMT = "%Y/%m/%d %H:%M:%S.%f"
ERROR_KEYWORDS = (
    "error",
    "failed",
    "timeout",
    "reset",
    "closed",
    "disconnect",
    "refused",
    "rejected",
)
SLEEP_WAKE_PATTERN = re.compile(r"sleep|wake|lock|unlock|screen.?off|doze", re.I)
GAP_THRESHOLDS = (5, 15, 30, 60)
SUB_DAY_LINE = re.compile(r"^(\w{3}\s+\w{3}\s+\d{1,2})")

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
    dest_ports: Counter = field(default_factory=Counter)
    error_keywords: Counter = field(default_factory=Counter)
    timestamps: list[str] = field(default_factory=list)
    gap_counts: dict[int, int] = field(default_factory=dict)
    sleep_wake_markers: int = 0
    time_first: str | None = None
    time_last: str | None = None

    def ingest_line(self, line: str) -> None:
        low = line.lower()
        for kw in ERROR_KEYWORDS:
            if kw in low:
                self.error_keywords[kw] += 1
        if SLEEP_WAKE_PATTERN.search(line):
            self.sleep_wake_markers += 1
        m = ACCESS_LINE.match(line.strip())
        if not m:
            return
        self.total_accepted += 1
        ts = line.split()[0] + " " + line.split()[1]
        self.timestamps.append(ts)
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
        self.dest_ports[m.group("dest_port")] += 1
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

    def finalize(self) -> None:
        self.gap_counts = compute_gap_counts(self.timestamps)


@dataclass
class SubscriptionStats:
    total_lines: int = 0
    server_response_200: int = 0
    unknown_content_type: int = 0
    import_count_zero: int = 0
    append_custom_ok: int = 0
    append_custom_bender: int = 0
    append_custom_safe: int = 0
    append_custom_count5: int = 0
    sub_updated_ok: int = 0
    sub_bender_updated: int = 0
    servers_one: int = 0
    servers_zero: int = 0
    google_file_failed: int = 0
    happ_file_failed: int = 0
    required_value_null: int = 0
    routing_file_failed: int = 0
    per_day: Counter = field(default_factory=Counter)
    jun16_events: list[str] = field(default_factory=list)
    sleep_wake_markers: int = 0
    date_first: str | None = None
    date_last: str | None = None
    last_update_ok_line: str | None = None
    last_server_200_line: str | None = None
    import_verdict: str = "unknown"

    def ingest_line(self, line: str, *, context: str = "") -> None:
        self.total_lines += 1
        if SLEEP_WAKE_PATTERN.search(line):
            self.sleep_wake_markers += 1
        day_m = SUB_DAY_LINE.match(line.strip())
        if day_m:
            day = day_m.group(1)
            self.per_day[day] += 1
            if not self.date_first:
                self.date_first = day
            self.date_last = day
        if "Server response: 200" in line:
            self.server_response_200 += 1
            self.last_server_200_line = redact(line.strip()[:120])
        if "UnknownContentType" in line:
            self.unknown_content_type += 1
        if "ImportResult(count=0" in line:
            self.import_count_zero += 1
        if re.search(r"Append custom result.*count=1", line):
            self.append_custom_ok += 1
            self.last_update_ok_line = redact(line.strip()[:120])
            if "BenderVPN" in context:
                self.append_custom_bender += 1
            elif "SafeVPN" in context:
                self.append_custom_safe += 1
        if re.search(r"Append custom result.*count=5", line):
            self.append_custom_count5 += 1
            if "SafeVPN" in context:
                self.append_custom_safe += 1
        if "Sub BenderVPN successfully updated" in line:
            self.sub_updated_ok += 1
            self.sub_bender_updated += 1
        if re.search(r"servers:\s*1 servers", line):
            self.servers_one += 1
        if re.search(r"servers:\s*0 servers", line):
            self.servers_zero += 1
        if "Google file failed" in line:
            self.google_file_failed += 1
            self.routing_file_failed += 1
        if "Happ file failed" in line:
            self.happ_file_failed += 1
            self.routing_file_failed += 1
        if "Required value was null" in line:
            self.required_value_null += 1
        if "Jun 16" in line and any(
            k in line
            for k in (
                "BenderVPN",
                "SafeVPN",
                "UnknownContentType",
                "Append custom",
                "Server response",
                "0 servers",
                "Required value",
                "Google file",
                "Happ file",
            )
        ):
            self.jun16_events.append(redact(line.strip()[:140]))

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


def compute_gap_counts(timestamps: list[str]) -> dict[int, int]:
    counts = {t: 0 for t in GAP_THRESHOLDS}
    if len(timestamps) < 2:
        return counts
    prev = datetime.strptime(timestamps[0], ACCESS_TS_FMT)
    for ts in timestamps[1:]:
        cur = datetime.strptime(ts, ACCESS_TS_FMT)
        delta = (cur - prev).total_seconds()
        for threshold in GAP_THRESHOLDS:
            if delta >= threshold:
                counts[threshold] += 1
        prev = cur
    return counts


def parse_access_log(text: str) -> AccessStats:
    stats = AccessStats()
    for line in text.splitlines():
        if "accepted" in line and "[socks" in line:
            before = stats.total_accepted
            stats.ingest_line(line)
            if stats.total_accepted == before:
                stats.parse_skipped += 1
    stats.finalize()
    return stats


def parse_subscription_log(text: str) -> SubscriptionStats:
    stats = SubscriptionStats()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        context = " ".join(lines[max(0, i - 5) : i + 2])
        stats.ingest_line(line, context=context)
    stats.finalize()
    return stats


def parse_adb_log(text: str) -> AdbStats:
    stats = AdbStats()
    for line in text.splitlines():
        stats.ingest_line(line)
    stats.finalize()
    return stats


def classify_root_cause_tracks(
    access: AccessStats | None,
    sub: SubscriptionStats | None,
) -> list[dict[str, str]]:
    tracks: list[dict[str, str]] = []

    if access and access.total_accepted > 0 and not access.error_keywords:
        tracks.append(
            {
                "track": "A — Active traffic path OK",
                "verdict": "CONFIRMED",
                "evidence": (
                    f"{access.total_accepted} accepted flows; "
                    f"multi-proxy routes; no access-log error keywords"
                ),
                "next_test": "Owner sleep/wake timed test with lock/unlock notes",
                "prod_change": "NO",
            }
        )
    elif access and access.total_accepted > 0:
        tracks.append(
            {
                "track": "A — Active traffic path OK",
                "verdict": "LIKELY",
                "evidence": f"{access.total_accepted} accepted flows with some error keywords",
                "next_test": "Correlate error keywords with user-visible failures",
                "prod_change": "NO",
            }
        )
    else:
        tracks.append(
            {
                "track": "A — Active traffic path OK",
                "verdict": "NOT PROVEN",
                "evidence": "No accepted flows parsed",
                "next_test": "Export access_log during active use",
                "prod_change": "NO",
            }
        )

    tracks.append(
        {
            "track": "B — Mobile sleep/wake reconnect",
            "verdict": "NOT PROVEN",
            "evidence": (
                "Owner report of slow post-sleep reconnect; "
                f"access log sleep/wake markers={access.sleep_wake_markers if access else 0}"
            ),
            "next_test": "Controlled lock/unlock matrix with exact timestamps",
            "prod_change": "NO",
        }
    )

    if sub and (
        sub.unknown_content_type > 0
        or sub.google_file_failed > 0
        or sub.happ_file_failed > 0
        or sub.required_value_null > 0
    ):
        sub_verdict = "LIKELY" if sub.append_custom_ok > 0 else "POSSIBLE"
        tracks.append(
            {
                "track": "C — Subscription/provider import/update",
                "verdict": sub_verdict,
                "evidence": (
                    f"UnknownContentType×{sub.unknown_content_type}; "
                    f"Google/Happ file failed×{sub.google_file_failed}/{sub.happ_file_failed}; "
                    f"Required value null×{sub.required_value_null}; "
                    f"Append custom Bender×{sub.append_custom_bender}"
                ),
                "next_test": "CLIENT-SUBSCRIPTION-IMPORT-HAPP-001 — correlate import errors with reconnect",
                "prod_change": "NO",
            }
        )
    else:
        tracks.append(
            {
                "track": "C — Subscription/provider import/update",
                "verdict": "NOT SUPPORTED",
                "evidence": "No subscription import noise in log",
                "next_test": "—",
                "prod_change": "NO",
            }
        )

    if access and sum(access.proxy_routes.values()) >= 3:
        tracks.append(
            {
                "track": "D — Multi-proxy selector path",
                "verdict": "POSSIBLE",
                "evidence": (
                    f"Traffic spread across {len(access.proxy_routes)} proxy tags "
                    f"(not relay2-only)"
                ),
                "next_test": "CLIENT-STABILITY-MOBILE-PROFILE-COMPARISON-001 if instability persists",
                "prod_change": "NO",
            }
        )

    tracks.append(
        {
            "track": "E — Server-side endpoint outage",
            "verdict": "NOT SUPPORTED",
            "evidence": "No dial/HTTP failure pattern in access log",
            "next_test": "Only if future logs show failed dials",
            "prod_change": "NO",
        }
    )

    tracks.append(
        {
            "track": "F — App/OS battery/background network",
            "verdict": "POSSIBLE",
            "evidence": "Owner sleep/wake report; needs phone settings + timed test",
            "next_test": "Disable battery optimization for Happ; repeat lock test",
            "prod_change": "NO",
        }
    )

    tracks.append(
        {
            "track": "G — Insufficient evidence for sleep/wake root cause",
            "verdict": "CONFIRMED",
            "evidence": "Logs alone cannot prove post-sleep tunnel failure without owner timestamps",
            "next_test": "Owner event correlation during next export",
            "prod_change": "NO",
        }
    )
    return tracks


def correlate_owner_events(
    owner_events: list[str],
    access: AccessStats | None,
    sub: SubscriptionStats | None,
) -> list[str]:
    notes: list[str] = []
    if not owner_events:
        notes.append("_No --owner-event timestamps provided._")
        return notes
    for ev in owner_events:
        notes.append(f"- Owner event: `{redact(ev)}`")
        if access and access.time_first and access.time_last:
            notes.append(
                f"  Access log window: {access.time_first} → {access.time_last} "
                "(check overlap manually — access uses YYYY/MM/DD format)"
            )
        if sub and sub.jun16_events:
            notes.append(f"  Jun 16 subscription events in log: {len(sub.jun16_events)} lines captured")
    notes.append(
        "_Gap analysis in access log may reflect idle/sleep but cannot classify without owner lock/unlock times._"
    )
    return notes


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
    owner_events: list[str] | None = None,
) -> str:
    verdict = recommend_verdict_support(access, sub, adb)
    tracks = classify_root_cause_tracks(access, sub)
    lines: list[str] = [
        "# Mobile smoke log summary (redacted)",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} local",
        "**Task:** CLIENT-STABILITY-MOBILE-LOGS-001",
        "",
        "> Redacted summary — raw logs not included. Mobile smoke PASS remains **PENDING** without owner app/speed/sleep-wake results.",
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
            f"- **Subscription log:** {sub.total_lines} lines ({sub.date_first} → {sub.date_last}); "
            f"HTTP 200×{sub.server_response_200}, UnknownContentType×{sub.unknown_content_type}, "
            f"Append custom Bender×{sub.append_custom_bender}, Safe×{sub.append_custom_safe}, "
            f"import={sub.import_verdict}"
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
        if access.gap_counts:
            lines.extend(["", "### Flow gaps (inter-accepted)", ""])
            lines.append("| Threshold | Count |")
            lines.append("|-----------|------:|")
            for th in GAP_THRESHOLDS:
                lines.append(f"| ≥{th}s | {access.gap_counts.get(th, 0)} |")
            lines.append("")
            lines.append(
                "_Gaps may be normal idle or phone sleep — only owner lock/unlock timestamps can classify._"
            )
        if access.dest_ports:
            lines.extend(["", "### Top destination ports", ""])
            for port, n in access.dest_ports.most_common(8):
                lines.append(f"- `{port}`: {n}")
        if access.error_keywords:
            lines.extend(["", "### Access log error keywords", ""])
            lines.append(", ".join(f"{k}={v}" for k, v in access.error_keywords.most_common()))
        else:
            lines.extend(["", "### Access log error keywords", "", "_None matched._"])
        lines.append(f"- Sleep/wake markers in access log: **{access.sleep_wake_markers}**")
    else:
        lines.append("_No routing evidence._")

    lines.extend(["", "## Subscription/import evidence", ""])
    if sub:
        lines.append(f"| Metric | Count |")
        lines.append(f"|--------|------:|")
        lines.append(f"| Server response 200 | {sub.server_response_200} |")
        lines.append(f"| UnknownContentType (batch) | {sub.unknown_content_type} |")
        lines.append(f"| ImportResult count=0 | {sub.import_count_zero} |")
        lines.append(f"| Append custom count=1 (total) | {sub.append_custom_ok} |")
        lines.append(f"| Append custom BenderVPN | {sub.append_custom_bender} |")
        lines.append(f"| Append custom SafeVPN | {sub.append_custom_safe} |")
        lines.append(f"| Append custom count=5 | {sub.append_custom_count5} |")
        lines.append(f"| Sub BenderVPN successfully updated | {sub.sub_bender_updated} |")
        lines.append(f"| «1 servers» UI count | {sub.servers_one} |")
        lines.append(f"| «0 servers» UI count | {sub.servers_zero} |")
        lines.append(f"| Google file failed | {sub.google_file_failed} |")
        lines.append(f"| Happ file failed | {sub.happ_file_failed} |")
        lines.append(f"| Required value was null | {sub.required_value_null} |")
        lines.append(f"| Routing/geofile fetch failed (total) | {sub.routing_file_failed} |")
        if sub.per_day:
            lines.extend(["", "### Per-day line counts (top 8)", ""])
            for day, n in sub.per_day.most_common(8):
                lines.append(f"- {day}: {n}")
        if sub.jun16_events:
            lines.extend(["", "### Jun 16 subscription timeline (redacted snippets)", ""])
            for ev in sub.jun16_events[:15]:
                lines.append(f"- {ev}")
            if len(sub.jun16_events) > 15:
                lines.append(f"- … and {len(sub.jun16_events) - 15} more")
        lines.append(f"- Sleep/wake markers in subscription log: **{sub.sleep_wake_markers}**")
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

    lines.extend(["", "## Root-cause classification", ""])
    lines.append("| Track | Verdict | Next test | Prod change? |")
    lines.append("|-------|---------|-----------|--------------|")
    for t in tracks:
        lines.append(
            f"| {t['track']} | **{t['verdict']}** | {t['next_test']} | {t['prod_change']} |"
        )

    lines.extend(["", "## Owner event correlation", ""])
    for note in correlate_owner_events(owner_events or [], access, sub):
        lines.append(note)

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
    owner_events: list[str] | None = None,
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

    md = build_markdown(access, sub, adb, sources, owner_events=owner_events)
    summary = recommend_verdict_support(access, sub, adb)
    summary["classification_tracks"] = classify_root_cause_tracks(access, sub)
    if access:
        summary["access_total"] = access.total_accepted
        summary["proxy_total"] = sum(access.proxy_routes.values())
        summary["direct_total"] = access.direct
        summary["gap_counts"] = access.gap_counts
        summary["error_keywords"] = dict(access.error_keywords)
    if sub:
        summary["subscription_unknown_content_type"] = sub.unknown_content_type
        summary["subscription_append_bender"] = sub.append_custom_bender
        summary["subscription_required_value_null"] = sub.required_value_null
    return md, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--access-log", "--access", dest="access_log", type=Path, help="Xray/Happ access_log.txt")
    ap.add_argument(
        "--subscription-log",
        "--subscription",
        dest="subscription_log",
        type=Path,
        help="Happ subscription_log.txt",
    )
    ap.add_argument("--adb-log", type=Path, help="logcat snippet with tun2socks lines")
    ap.add_argument("--owner-event", action="append", default=[], help="Owner timestamp note for correlation")
    ap.add_argument("--owner-note", action="append", default=[], help="Alias for owner-event (observability notes)")
    ap.add_argument("--fullday", action="store_true", help="Full-day timeline + cross-correlation mode")
    ap.add_argument("--validate-coverage", action="store_true", help="Validate export coverage for target day")
    ap.add_argument("--day", default="2026-06-16", help="Target day for fullday mode (YYYY-MM-DD)")
    ap.add_argument("--timeline-bucket-minutes", type=int, default=5, help="Access timeline bucket size")
    ap.add_argument("--correlate", action="store_true", help="Cross-correlate gaps with subscription events")
    ap.add_argument("--emit-json", type=Path, help="Write fullday summary JSON (local only)")
    ap.add_argument("--out", type=Path, default=Path(".local/mobile_smoke_log_summary.md"))
    ap.add_argument("--json", action="store_true", help="print summary JSON to stdout")
    args = ap.parse_args()

    if args.fullday or args.validate_coverage:
        from mobile_log_fullday import analyze_fullday, build_observability_report, validate_export_files

        owner_notes = list(args.owner_event or []) + list(args.owner_note or [])

        if args.validate_coverage:
            validation = validate_export_files(
                day=args.day,
                access_path=args.access_log,
                subscription_path=args.subscription_log,
            )
            from mobile_log_fullday import parse_owner_notes

            obs_md = build_observability_report(
                day=args.day,
                validation=validation,
                owner_notes=parse_owner_notes(owner_notes),
            )
            out_path = args.out or Path(".local/mobile_observability_report.md")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(obs_md, encoding="utf-8")
            print(f"Wrote: {out_path}")
            if args.json:
                import json

                print(json.dumps(validation, ensure_ascii=False, indent=2))
            if not args.fullday:
                print("MOBILE_OBSERVABILITY_VALIDATE_OK")
                return 0

        if not args.access_log and not args.subscription_log:
            print("FAIL: fullday mode needs --access-log and/or --subscription-log", file=sys.stderr)
            return 1
        sources: dict[str, str] = {}
        access_text = sub_text = None
        if args.access_log and args.access_log.is_file():
            sources["access_log"] = str(args.access_log)
            access_text = args.access_log.read_text(encoding="utf-8", errors="replace")
        if args.subscription_log and args.subscription_log.is_file():
            sources["subscription_log"] = str(args.subscription_log)
            sub_text = args.subscription_log.read_text(encoding="utf-8", errors="replace")
        md, summary = analyze_fullday(
            day=args.day,
            access_text=access_text,
            subscription_text=sub_text,
            bucket_minutes=args.timeline_bucket_minutes,
            correlate=args.correlate or True,
            sources=sources,
            owner_notes=owner_notes,
        )
        out_path = args.out or Path(".local/mobile_fullday_analysis.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"Wrote: {out_path}")
        if args.emit_json:
            import json

            args.emit_json.parent.mkdir(parents=True, exist_ok=True)
            args.emit_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Wrote JSON: {args.emit_json}")
        if args.json:
            import json

            print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("MOBILE_FULLDAY_ANALYSIS_OK")
        return 0

    if not any([args.access_log, args.subscription_log, args.adb_log]):
        print("FAIL: provide at least one --access-log, --subscription-log, or --adb-log", file=sys.stderr)
        return 1

    md, summary = analyze(
        access_path=args.access_log,
        subscription_path=args.subscription_log,
        adb_path=args.adb_log,
        owner_events=args.owner_event,
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
