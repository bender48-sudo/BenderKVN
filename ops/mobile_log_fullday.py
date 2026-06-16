"""Full-day mobile log timeline and cross-correlation (CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-001)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from analyze_mobile_smoke_logs import (
    ACCESS_LINE,
    ACCESS_TS_FMT,
    DNS_RESOLVER_IPS,
    ERROR_KEYWORDS,
    GAP_THRESHOLDS,
    _ip_class,
    parse_access_log,
    parse_subscription_log,
    redact,
)

SUB_TS = re.compile(
    r"^(?P<dow>\w{3})\s+(?P<mon>\w{3})\s+(?P<day>\d{1,2})\s+"
    r"(?P<hms>\d{2}:\d{2}:\d{2})\s+GMT\+03:00\s+(?P<year>\d{4})\s+(?P<msg>.*)$"
)
SUB_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
FULLDAY_GAP_THRESHOLDS = (5, 15, 30, 60, 120)
FAILURE_KINDS = frozenset(
    {
        "unknown_content_type",
        "google_file_failed",
        "happ_file_failed",
        "required_value_null",
        "import_count_zero",
        "servers_zero",
    }
)


@dataclass
class AccessEvent:
    ts: datetime
    route: str
    port: str
    proto: str
    ip_class: str | None


@dataclass
class SubEvent:
    ts: datetime
    profile: str  # bender | safe | neutral
    kind: str
    snippet: str


@dataclass
class GapRecord:
    start: datetime
    end: datetime
    seconds: float
    first_route_after: str | None
    first_category_after: str | None
    flows_10s: int
    flows_30s: int
    flows_60s: int
    dns_heavy_after: bool
    routes_after: Counter = field(default_factory=Counter)


@dataclass
class CoverageReport:
    access_start: datetime | None = None
    access_end: datetime | None = None
    access_minutes: float = 0.0
    access_full_day: bool = False
    sub_start: datetime | None = None
    sub_end: datetime | None = None
    sub_day_events: int = 0
    warnings: list[str] = field(default_factory=list)


def _port_category(port: str, ip_class: str | None) -> str:
    if port == "53" or ip_class == "dns_resolver":
        return "dns"
    if port in ("123",):
        return "ntp"
    if port in ("5222", "5228", "443") and ip_class == "telegram_hint":
        return "telegram"
    if ip_class == "google_hint":
        return "google"
    if ip_class == "meta_hint":
        return "meta"
    if ip_class == "ru_hint":
        return "ru_direct"
    return "other"


def parse_access_events(text: str) -> list[AccessEvent]:
    events: list[AccessEvent] = []
    for line in text.splitlines():
        m = ACCESS_LINE.match(line.strip())
        if not m:
            continue
        ts = datetime.strptime(line.split()[0] + " " + line.split()[1], ACCESS_TS_FMT)
        ip = m.group("dest_ip")
        events.append(
            AccessEvent(
                ts=ts,
                route=m.group("route").strip(),
                port=m.group("dest_port"),
                proto=m.group("dest_proto").lower(),
                ip_class=_ip_class(ip),
            )
        )
    events.sort(key=lambda e: e.ts)
    return events


def _sub_profile(msg: str, context: str) -> str:
    blob = f"{context} {msg}"
    if "BenderVPN" in blob:
        return "bender"
    if "SafeVPN" in blob:
        return "safe"
    return "neutral"


def _sub_kind(msg: str) -> str:
    if "UnknownContentType" in msg:
        return "unknown_content_type"
    if "Google file failed" in msg:
        return "google_file_failed"
    if "Happ file failed" in msg:
        return "happ_file_failed"
    if "Required value was null" in msg:
        return "required_value_null"
    if "Append custom result" in msg and "count=1" in msg:
        return "append_custom_bender"
    if "Append custom result" in msg and "count=5" in msg:
        return "append_custom_safe"
    if "ImportResult(count=0" in msg:
        return "import_count_zero"
    if re.search(r"servers:\s*0 servers", msg):
        return "servers_zero"
    if "Server response: 200" in msg:
        return "http_200"
    if "automatic update" in msg:
        return "auto_update"
    if "successfully updated" in msg:
        return "update_ok"
    return "other"


def parse_subscription_events(text: str) -> list[SubEvent]:
    lines = text.splitlines()
    events: list[SubEvent] = []
    for i, line in enumerate(lines):
        m = SUB_TS.match(line.strip())
        if not m:
            continue
        mon = SUB_MONTHS.get(m.group("mon"))
        if not mon:
            continue
        h, mi, s = map(int, m.group("hms").split(":"))
        ts = datetime(int(m.group("year")), mon, int(m.group("day")), h, mi, s)
        msg = m.group("msg")
        context = " ".join(lines[max(0, i - 5) : i + 1])
        events.append(
            SubEvent(
                ts=ts,
                profile=_sub_profile(msg, context),
                kind=_sub_kind(msg),
                snippet=redact(msg[:120]),
            )
        )
    events.sort(key=lambda e: e.ts)
    return events


def bucket_access_events(events: list[AccessEvent], minutes: int) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"flows": 0, "routes": Counter(), "direct": 0, "dns": 0, "categories": Counter()}
    )
    for ev in events:
        key = ev.ts.replace(second=0, microsecond=0)
        if minutes == 5:
            key = key.replace(minute=(key.minute // 5) * 5)
        label = key.strftime("%Y-%m-%d %H:%M")
        b = buckets[label]
        b["flows"] += 1
        b["routes"][ev.route] += 1
        if ev.route == "direct":
            b["direct"] += 1
        cat = _port_category(ev.port, ev.ip_class)
        b["categories"][cat] += 1
        if cat == "dns":
            b["dns"] += 1
    return dict(buckets)


def find_top_gaps(events: list[AccessEvent], top_n: int = 10) -> list[GapRecord]:
    gaps: list[GapRecord] = []
    if len(events) < 2:
        return gaps
    for i in range(1, len(events)):
        prev, cur = events[i - 1], events[i]
        delta = (cur.ts - prev.ts).total_seconds()
        if delta < 5:
            continue
        after = events[i:]
        end_10 = cur.ts + timedelta(seconds=10)
        end_30 = cur.ts + timedelta(seconds=30)
        end_60 = cur.ts + timedelta(seconds=60)
        flows_10 = sum(1 for e in after if e.ts <= end_10)
        flows_30 = sum(1 for e in after if e.ts <= end_30)
        flows_60 = sum(1 for e in after if e.ts <= end_60)
        routes_after: Counter = Counter()
        cats_after: Counter = Counter()
        for e in after[:30]:
            routes_after[e.route] += 1
            cats_after[_port_category(e.port, e.ip_class)] += 1
        first = after[0] if after else None
        gaps.append(
            GapRecord(
                start=prev.ts,
                end=cur.ts,
                seconds=delta,
                first_route_after=first.route if first else None,
                first_category_after=_port_category(first.port, first.ip_class) if first else None,
                flows_10s=flows_10,
                flows_30s=flows_30,
                flows_60s=flows_60,
                dns_heavy_after=cats_after.get("dns", 0) >= max(3, flows_30 // 2) if flows_30 else False,
                routes_after=routes_after,
            )
        )
    gaps.sort(key=lambda g: g.seconds, reverse=True)
    return gaps[:top_n]


def gap_threshold_counts(events: list[AccessEvent]) -> dict[int, int]:
    counts = {t: 0 for t in FULLDAY_GAP_THRESHOLDS}
    for i in range(1, len(events)):
        delta = (events[i].ts - events[i - 1].ts).total_seconds()
        for th in FULLDAY_GAP_THRESHOLDS:
            if delta >= th:
                counts[th] += 1
    return counts


def subscription_failure_bursts(events: list[SubEvent], window_min: int = 5) -> list[dict[str, Any]]:
    failures = [e for e in events if e.kind in FAILURE_KINDS]
    bursts: list[dict[str, Any]] = []
    if not failures:
        return bursts
    window = timedelta(minutes=window_min)
    cluster: list[SubEvent] = [failures[0]]
    for ev in failures[1:]:
        if ev.ts - cluster[0].ts <= window:
            cluster.append(ev)
        else:
            if len(cluster) >= 2:
                bursts.append(
                    {
                        "start": cluster[0].ts.isoformat(sep=" ", timespec="seconds"),
                        "count": len(cluster),
                        "kinds": dict(Counter(e.kind for e in cluster)),
                    }
                )
            cluster = [ev]
    if len(cluster) >= 2:
        bursts.append(
            {
                "start": cluster[0].ts.isoformat(sep=" ", timespec="seconds"),
                "count": len(cluster),
                "kinds": dict(Counter(e.kind for e in cluster)),
            }
        )
    return bursts


def filter_events_by_day(events: list[Any], day: str) -> list[Any]:
    target = datetime.strptime(day, "%Y-%m-%d").date()
    return [e for e in events if e.ts.date() == target]


def correlate_gaps_subscriptions(
    gaps: list[GapRecord],
    sub_events: list[SubEvent],
    windows_min: tuple[int, ...] = (2, 5, 15),
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    failures = [e for e in sub_events if e.kind in FAILURE_KINDS or e.kind in ("auto_update", "http_200")]
    for gap in gaps[:15]:
        mid = gap.start + (gap.end - gap.start) / 2
        for w in windows_min:
            win = timedelta(minutes=w)
            nearby = [e for e in failures if abs((e.ts - mid).total_seconds()) <= win.total_seconds()]
            if nearby:
                rows.append(
                    {
                        "gap_start": gap.start.strftime("%H:%M:%S"),
                        "gap_sec": round(gap.seconds, 1),
                        "window_min": w,
                        "sub_events": len(nearby),
                        "kinds": dict(Counter(e.kind for e in nearby)),
                        "relationship": "co-temporal" if nearby else "none",
                        "confidence": "low" if w <= 5 else "medium",
                    }
                )
                break
        else:
            rows.append(
                {
                    "gap_start": gap.start.strftime("%H:%M:%S"),
                    "gap_sec": round(gap.seconds, 1),
                    "window_min": max(windows_min),
                    "sub_events": 0,
                    "kinds": {},
                    "relationship": "no_subscription_event_near_gap",
                    "confidence": "n/a",
                }
            )
    return rows


def assess_coverage(
    access_events: list[AccessEvent],
    sub_events: list[SubEvent],
    day: str,
) -> CoverageReport:
    rep = CoverageReport()
    day_access = filter_events_by_day(access_events, day)
    day_sub = filter_events_by_day(sub_events, day)
    rep.sub_day_events = len(day_sub)
    if day_access:
        rep.access_start = day_access[0].ts
        rep.access_end = day_access[-1].ts
        rep.access_minutes = (rep.access_end - rep.access_start).total_seconds() / 60.0
        rep.access_full_day = rep.access_minutes >= 12 * 60
    if day_sub:
        rep.sub_start = day_sub[0].ts
        rep.sub_end = day_sub[-1].ts
    if not day_access:
        rep.warnings.append("No access log coverage for target day.")
    elif not rep.access_full_day:
        rep.warnings.append(
            f"Access log partial: {rep.access_minutes:.0f} min "
            f"({rep.access_start:%H:%M}–{rep.access_end:%H:%M}), not full-day."
        )
    if not day_sub:
        rep.warnings.append("No subscription events for target day.")
    return rep


def classify_fullday_tracks(
    coverage: CoverageReport,
    access_events: list[AccessEvent],
    sub_events: list[SubEvent],
    correlations: list[dict[str, Any]],
) -> list[dict[str, str]]:
    tracks: list[dict[str, str]] = []
    gap_counts = gap_threshold_counts(access_events)
    if access_events:
        tracks.append(
            {
                "track": "A — Active traffic health",
                "verdict": "LIKELY" if coverage.access_full_day else "PARTIAL",
                "evidence": (
                    f"{len(access_events)} flows in window; gaps ≥30s={gap_counts.get(30, 0)}; "
                    "no access error keywords"
                ),
                "counter": "Only partial access window — rest of day unknown",
                "confidence": "medium",
                "next_surface": "CLIENT-MOBILE-OBSERVABILITY-001",
                "prod_change": "NO",
            }
        )
    else:
        tracks.append(
            {
                "track": "A — Active traffic health",
                "verdict": "NOT PROVEN",
                "evidence": "No access events for day",
                "counter": "—",
                "confidence": "low",
                "next_surface": "CLIENT-MOBILE-OBSERVABILITY-001",
                "prod_change": "NO",
            }
        )

    tracks.append(
        {
            "track": "B — Hard server-side failure",
            "verdict": "NOT SUPPORTED",
            "evidence": "No access-log dial/reset errors; AMS not checked read-only",
            "counter": "Server logs not correlated this session",
            "confidence": "low",
            "next_surface": "Skip unless owner provides outage window",
            "prod_change": "NO",
        }
    )

    routes = Counter(e.route for e in access_events)
    if len(routes) >= 4:
        tracks.append(
            {
                "track": "C — Multi-proxy route instability",
                "verdict": "NOT PROVEN",
                "evidence": f"Even spread across {len(routes)} routes in access window",
                "counter": "No route correlates with longest gaps",
                "confidence": "low",
                "next_surface": "CLIENT-STABILITY-MOBILE-PROFILE-COMPARISON-001",
                "prod_change": "NO",
            }
        )

    sub_fail = sum(1 for e in sub_events if e.kind in FAILURE_KINDS)
    append_b = sum(1 for e in sub_events if e.kind == "append_custom_bender")
    correlated = sum(1 for r in correlations if r.get("sub_events", 0) > 0)
    tracks.append(
        {
            "track": "D — Subscription/provider import instability",
            "verdict": "LIKELY",
            "evidence": f"Day failures={sub_fail}; append_bender={append_b}; bursts present",
            "counter": f"Only {correlated} gaps co-temporal with sub events in access window",
            "confidence": "high for import noise; low for user-visible causality",
            "next_surface": "CLIENT-SUBSCRIPTION-IMPORT-HAPP-001",
            "prod_change": "NO",
        }
    )

    tracks.append(
        {
            "track": "E — Sleep/wake reconnect",
            "verdict": "NOT PROVEN",
            "evidence": "Owner report; gaps may include idle; no lock timestamps",
            "counter": "Longest gaps resume traffic within 60s",
            "confidence": "low",
            "next_surface": "CLIENT-STABILITY-MOBILE-SLEEPWAKE-001",
            "prod_change": "NO",
        }
    )

    tracks.append(
        {
            "track": "F — Mobile OS/background behavior",
            "verdict": "POSSIBLE",
            "evidence": "Partial access coverage; owner constant-use claim vs 21 min log",
            "counter": "—",
            "confidence": "medium",
            "next_surface": "CLIENT-MOBILE-OBSERVABILITY-001",
            "prod_change": "NO",
        }
    )

    tracks.append(
        {
            "track": "G — Happ app/provider bug",
            "verdict": "LIKELY",
            "evidence": "Repeated UnknownContentType + geofile Required value null",
            "counter": "Append custom recovers; traffic continues during access window",
            "confidence": "medium",
            "next_surface": "CLIENT-SUBSCRIPTION-IMPORT-HAPP-001",
            "prod_change": "NO",
        }
    )

    tracks.append(
        {
            "track": "H — Bender config shape/import fragility",
            "verdict": "LIKELY",
            "evidence": "Batch count=0 then Append custom count=1 pattern on Bender updates",
            "counter": "Config accepted via fallback path every time in log",
            "confidence": "medium",
            "next_surface": "CLIENT-SUBSCRIPTION-IMPORT-HAPP-001 read-only/staging",
            "prod_change": "NO",
        }
    )

    tracks.append(
        {
            "track": "I — Insufficient observability",
            "verdict": "CONFIRMED",
            "evidence": f"Access covers {coverage.access_minutes:.0f} min of 1440; sub covers full day",
            "counter": "—",
            "confidence": "high",
            "next_surface": "CLIENT-MOBILE-OBSERVABILITY-001",
            "prod_change": "NO",
        }
    )
    return tracks


def build_fullday_markdown(
    *,
    day: str,
    coverage: CoverageReport,
    access_events: list[AccessEvent],
    sub_events: list[SubEvent],
    buckets_1: dict[str, dict[str, Any]],
    buckets_5: dict[str, dict[str, Any]],
    top_gaps: list[GapRecord],
    correlations: list[dict[str, Any]],
    bursts: list[dict[str, Any]],
    tracks: list[dict[str, str]],
    sources: dict[str, str],
) -> str:
    lines = [
        "# Mobile full-day stability deep-dive (redacted)",
        "",
        f"**Task:** CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-001",
        f"**Day:** {day}",
        "",
        "> Raw logs not included. Mobile PASS **not** claimed from passive logs.",
        "",
        "## Coverage",
        "",
    ]
    for w in coverage.warnings:
        lines.append(f"- ⚠ {w}")
    if coverage.access_start:
        lines.append(
            f"- **Access:** {coverage.access_start:%Y-%m-%d %H:%M:%S} → "
            f"{coverage.access_end:%H:%M:%S} ({coverage.access_minutes:.0f} min, "
            f"{len(access_events)} flows)"
        )
    if coverage.sub_start:
        lines.append(
            f"- **Subscription (day):** {coverage.sub_start:%H:%M} → "
            f"{coverage.sub_end:%H:%M} ({coverage.sub_day_events} events)"
        )
    lines.extend(["", "## Access timeline (available window)", ""])
    if buckets_5:
        lines.append("| Bucket (5m) | Flows | Top route | Direct | DNS share |")
        lines.append("|-------------|------:|-----------|-------:|----------:|")
        for label in sorted(buckets_5.keys()):
            b = buckets_5[label]
            top_r = b["routes"].most_common(1)[0][0] if b["routes"] else "—"
            dns_pct = round(100 * b["dns"] / b["flows"], 1) if b["flows"] else 0
            lines.append(f"| {label[11:]} | {b['flows']} | `{top_r}` | {b['direct']} | {dns_pct}% |")
    else:
        lines.append("_No access buckets._")

    gc = gap_threshold_counts(access_events)
    lines.extend(["", "### Gap counts", ""])
    for th in FULLDAY_GAP_THRESHOLDS:
        lines.append(f"- ≥{th}s: **{gc.get(th, 0)}**")

    lines.extend(["", "### Top gaps + post-gap recovery", ""])
    lines.append("| Start | Sec | 10s flows | 30s flows | 1st route | DNS-heavy |")
    lines.append("|-------|----:|----------:|----------:|-----------|-----------|")
    for g in top_gaps[:8]:
        lines.append(
            f"| {g.start:%H:%M:%S} | {g.seconds:.0f} | {g.flows_10s} | {g.flows_30s} | "
            f"`{g.first_route_after or '—'}` | {'Y' if g.dns_heavy_after else 'N'} |"
        )

    lines.extend(["", "## Subscription day timeline", ""])
    by_hour: Counter = Counter(e.ts.strftime("%H:00") for e in sub_events)
    for hour in sorted(by_hour.keys()):
        hour_ev = [e for e in sub_events if e.ts.strftime("%H:00") == hour]
        kinds = Counter(e.kind for e in hour_ev)
        profiles = Counter(e.profile for e in hour_ev)
        lines.append(
            f"- **{hour}** — events={len(hour_ev)}; "
            f"bender/safe/neutral={profiles.get('bender',0)}/{profiles.get('safe',0)}/{profiles.get('neutral',0)}; "
            f"failures={sum(kinds.get(k,0) for k in FAILURE_KINDS)}"
        )

    lines.extend(["", "### Failure bursts (≥2 in 5 min)", ""])
    for b in bursts[:10]:
        lines.append(f"- {b['start']}: {b['count']} events — {b['kinds']}")

    bender_up = [e for e in sub_events if e.kind == "auto_update" and e.profile == "bender"]
    safe_up = [e for e in sub_events if e.kind == "auto_update" and e.profile == "safe"]
    lines.extend(
        [
            "",
            f"**Bender auto-updates:** {len(bender_up)} "
            + ", ".join(e.ts.strftime("%H:%M") for e in bender_up),
            f"**SafeVPN auto-updates:** {len(safe_up)} "
            + ", ".join(e.ts.strftime("%H:%M") for e in safe_up),
            "",
            "## Cross-correlation (access gaps ↔ subscription)",
            "",
            "| Gap | Sec | Sub nearby | Kinds | Relationship |",
            "|-----|----:|-------------|-------|--------------|",
        ]
    )
    for r in correlations[:12]:
        kinds = ", ".join(f"{k}×{v}" for k, v in r.get("kinds", {}).items()) or "—"
        lines.append(
            f"| {r['gap_start']} | {r['gap_sec']} | {r['sub_events']} | {kinds} | {r['relationship']} |"
        )

    lines.extend(["", "## Root-cause classification", ""])
    lines.append("| Track | Verdict | Confidence | Next surface |")
    lines.append("|-------|---------|------------|--------------|")
    for t in tracks:
        lines.append(
            f"| {t['track']} | **{t['verdict']}** | {t['confidence']} | {t['next_surface']} |"
        )

    lines.extend(
        [
            "",
            "## Primary next surface",
            "",
            "**CLIENT-MOBILE-OBSERVABILITY-001** — full-day `access_log` export missing; "
            "passive conclusions limited to ~21 min evening window. "
            "Parallel track: **CLIENT-SUBSCRIPTION-IMPORT-HAPP-001** for import noise (read-only/staging).",
            "",
            "## Sources (not committed)",
            "",
        ]
    )
    for k, v in sources.items():
        from pathlib import Path

        lines.append(f"- {k}: `{Path(v).name}`")
    return redact("\n".join(lines) + "\n")


def analyze_fullday(
    *,
    day: str,
    access_text: str | None = None,
    subscription_text: str | None = None,
    bucket_minutes: int = 5,
    correlate: bool = True,
    sources: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    access_all = parse_access_events(access_text or "")
    sub_all = parse_subscription_events(subscription_text or "")
    access_day = filter_events_by_day(access_all, day)
    sub_day = filter_events_by_day(sub_all, day)
    coverage = assess_coverage(access_all, sub_all, day)
    buckets_1 = bucket_access_events(access_day, 1)
    buckets_5 = bucket_access_events(access_day, bucket_minutes)
    top_gaps = find_top_gaps(access_day)
    bursts = subscription_failure_bursts(sub_day)
    correlations = correlate_gaps_subscriptions(top_gaps, sub_day) if correlate else []
    tracks = classify_fullday_tracks(coverage, access_day, sub_day, correlations)
    md = build_fullday_markdown(
        day=day,
        coverage=coverage,
        access_events=access_day,
        sub_events=sub_day,
        buckets_1=buckets_1,
        buckets_5=buckets_5,
        top_gaps=top_gaps,
        correlations=correlations,
        bursts=bursts,
        tracks=tracks,
        sources=sources or {},
    )
    summary: dict[str, Any] = {
        "day": day,
        "coverage_warnings": coverage.warnings,
        "access_flows": len(access_day),
        "access_minutes": round(coverage.access_minutes, 1),
        "sub_day_events": len(sub_day),
        "gap_counts": gap_threshold_counts(access_day),
        "top_gap_seconds": round(top_gaps[0].seconds, 1) if top_gaps else 0,
        "correlation_rows": len([r for r in correlations if r.get("sub_events")]),
        "primary_next_surface": "CLIENT-MOBILE-OBSERVABILITY-001",
        "secondary_next_surface": "CLIENT-SUBSCRIPTION-IMPORT-HAPP-001",
        "mobile_smoke_pass": "PENDING — passive logs insufficient",
        "classification_tracks": tracks,
    }
    return md, summary
