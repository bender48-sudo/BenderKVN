#!/usr/bin/env python3
"""Analyze Happ report.zip for NL canary smoke validity — NL-DIRECT-BASIC-SMOKE-GUARD-001.

Extends analyze_happ_report_tun with fail-fast preflight before NL PASS/FAIL claims.

Usage:
    python ops/analyze_nl_canary_smoke.py --report path/to/report.zip --variant direct_basic
    python ops/analyze_nl_canary_smoke.py --report path/to/report.zip --variant direct_basic --json
    python ops/analyze_nl_canary_smoke.py --report path/to/report.zip --variant direct_basic --evaluate
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from analyze_happ_report_tun import analyze_report_zip, read_zip_text  # noqa: E402
import zipfile
from nl_canary_smoke_guard import (  # noqa: E402
    VERDICT_NOT_TESTED,
    evaluate_nl_canary_smoke,
)


def analyze_nl_canary_smoke_report(
    report_path: Path,
    *,
    variant: str = "direct_basic",
    evaluate: bool = False,
) -> dict:
    tun = analyze_report_zip(report_path)
    with zipfile.ZipFile(report_path) as zf:
        app_log = read_zip_text(zf, "application_log.txt", limit=500_000)
        tun_log = read_zip_text(zf, "tun_log.txt", limit=2_000_000)
        tasklist = read_zip_text(zf, "tasklist.txt", limit=200_000)
    profile_name = tun.profile.get("profile_name") or tun.final_state_guard.get("final_selected_name")
    guard = evaluate_nl_canary_smoke(
        variant=variant,
        profile_name=profile_name,
        profile=tun.profile,
        mode=tun.mode,
        tun_lifecycle=tun.tun_lifecycle,
        tun_log_stats=tun.tun_log_stats,
        error_endpoints=tun.error_endpoints,
        app_log=app_log,
        tun_log=tun_log,
        tasklist=tasklist,
        allow_evaluation=evaluate,
    )
    return {
        "report": report_path.name,
        "variant": variant,
        "guard": guard.to_dict(),
        "tun_summary": {
            "profile_name": profile_name,
            "mode": {
                "tun": tun.mode.get("tun"),
                "use_routing": tun.mode.get("use_routing"),
                "routing_profile": tun.mode.get("routing_profile"),
            },
            "tun_startup_healthy": guard.checks.get("tun_startup_healthy"),
            "dns_set_ok": guard.checks.get("dns_set_ok"),
            "error_like_lines": tun.tun_log_stats.get("error_like_lines"),
            "top_error_endpoint_category": tun.error_endpoints.get("top_error_endpoint_category"),
            "top_error_endpoint_share": tun.error_endpoints.get("top_error_endpoint_share"),
            "relay2_proxy_count": tun.profile.get("relay2_proxy_count"),
            "balancer_names": tun.profile.get("balancer_names"),
        },
        "notes": tun.notes[:8],
    }


def print_human(result: dict) -> None:
    g = result["guard"]
    print(f"report={result['report']} variant={result['variant']}")
    print(f"ACCEPTABLE_SMOKE_INPUT={g['ACCEPTABLE_SMOKE_INPUT']}")
    print(f"verdict={g['verdict']}")
    if g["invalid_reasons"]:
        print("invalid_reasons:")
        for r in g["invalid_reasons"]:
            print(f"  - {r}")
    print("checks:")
    for k, v in g["checks"].items():
        print(f"  {k}: {v}")
    for note in g.get("notes") or []:
        print(f"note: {note}")
    ts = result.get("tun_summary") or {}
    print(
        f"tun: errors={ts.get('error_like_lines')} "
        f"dns_ok={ts.get('dns_set_ok')} "
        f"top_err_cat={ts.get('top_error_endpoint_category')}"
    )


def main(argv: list[str] | None = None) -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="NL canary smoke guard analyzer")
    parser.add_argument("--report", type=Path, required=True, help="Happ report.zip path")
    parser.add_argument(
        "--variant",
        choices=("direct_basic", "split_stealth"),
        default="direct_basic",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="when smoke input is valid, derive PASS/PARTIAL/FAIL from session metrics",
    )
    args = parser.parse_args(argv)

    if not args.report.is_file():
        print(f"error: report not found: {args.report}", file=sys.stderr)
        return 2

    result = analyze_nl_canary_smoke_report(
        args.report,
        variant=args.variant,
        evaluate=args.evaluate,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_human(result)

    guard = result["guard"]
    if not guard["ACCEPTABLE_SMOKE_INPUT"]:
        return 3
    if guard["verdict"] == VERDICT_NOT_TESTED:
        return 0
    if guard["verdict"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
