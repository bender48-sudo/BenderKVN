#!/usr/bin/env python3
"""AMS safe-deploy gate smoke (P2-OPS-AMS-SAFE-DEPLOY-01).

Read-only checks on prod AMS + public panel/sub edges. Run **before** and **after**
any render/nakат of ``/opt/remnawave/*``, ``/opt/remnawave/sub/*``, ``/opt/remna-shop/.env``.

Example::

  python ops/smoke_ams_safe_deploy.py
  python ops/smoke_ams_safe_deploy.py --json
  python ops/smoke_ams_safe_deploy.py --skip-sub-probe

Exit 0 prints ``AMS_SAFE_DEPLOY_OK``.
"""
from __future__ import annotations

import argparse
import json
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

import site_urls  # noqa: E402
from panel_client import PanelClient  # noqa: E402

AMS = "root@168.100.11.140"
SSH_PORT = "3344"
SSH_KEY = Path.home() / ".ssh" / "bvpn_ams_ed25519"
def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _ssh(cmd: str, timeout: int = 90) -> tuple[int, str]:
    full = [
        "ssh",
        "-i",
        str(SSH_KEY),
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={min(timeout, 40)}",
        "-p",
        SSH_PORT,
        AMS,
        cmd,
    ]
    proc = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _https_code(url: str, timeout: float = 12.0) -> int:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Happ/1.9.4 (iOS)"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def _ssh_run_local_script(local_name: str) -> tuple[int, str]:
    """SCP ops/*.sh to AMS /tmp and execute (LF temp file — Windows CRLF safe)."""
    import tempfile

    path = ROOT / "ops" / local_name
    if not path.is_file():
        return 127, f"missing {path}"
    remote = f"/tmp/bvpn-{local_name}"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".sh", delete=False, newline="\n"
    ) as tmp:
        tmp.write(_lf(path.read_text(encoding="utf-8")))
        local_tmp = tmp.name
    try:
        scp = subprocess.run(
            [
                "scp",
                "-i",
                str(SSH_KEY),
                "-o",
                "BatchMode=yes",
                "-P",
                SSH_PORT,
                local_tmp,
                f"{AMS}:{remote}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if scp.returncode != 0:
            return scp.returncode, (scp.stderr or scp.stdout or "scp failed")[:300]
        proc = subprocess.run(
            [
                "ssh",
                "-i",
                str(SSH_KEY),
                "-o",
                "BatchMode=yes",
                "-p",
                SSH_PORT,
                AMS,
                f"bash {remote}",
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    finally:
        Path(local_tmp).unlink(missing_ok=True)


def _ssh_ams_bundle() -> tuple[int, dict[str, str], str]:
    code, out = _ssh_run_local_script("ams_safe_deploy_bundle.sh")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    flags = {ln: "1" for ln in lines}
    return code, flags, out


def check_ams_bundle() -> tuple[bool, str]:
    code, flags, raw = _ssh_ams_bundle()
    if code != 0:
        return False, f"AMS bundle ssh exit {code}: {raw[-200:]}"
    problems = [k for k in flags if k != "BUNDLE_DONE"]
    if problems:
        return False, ", ".join(problems)
    return True, "AMS containers + panel .env bundle OK"


def check_panel_api() -> tuple[bool, str]:
    try:
        client = PanelClient()
    except Exception as e:
        return False, f"PanelClient: {e}"
    code, data = client.get(
        "/api/nodes",
        extra_headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "127.0.0.1"},
    )
    if code != 200:
        return False, f"GET /api/nodes HTTP {code}"
    nodes = (data or {}).get("response") if isinstance(data, dict) else None
    if not isinstance(nodes, list):
        return False, "unexpected /api/nodes payload"
    return True, f"panel API OK ({len(nodes)} nodes)"


def check_sub_edges() -> tuple[bool, str]:
    bad: list[str] = []
    for url in site_urls.sub_all_probe_urls():
        code = 0
        for attempt in range(3):
            code = _https_code(url)
            if code in (200, 304):
                break
            if attempt < 2:
                import time

                time.sleep(2)
        if code not in (200, 304):
            bad.append(f"{url} -> {code}")
    if bad:
        return False, "; ".join(bad)
    return True, f"sub edges OK ({len(site_urls.sub_all_probe_urls())} origins)"


def check_postgres_luks() -> tuple[bool, str]:
    code, out = _ssh("python3 /opt/scripts/ams_postgres_crypt_probe.py 2>&1", timeout=30)
    if code == 0 and "POSTGRES_CRYPT_OK" in out:
        return True, "POSTGRES_CRYPT_OK"
    return False, out[-400:]


def check_sub_load_probe() -> tuple[bool, str]:
    probe = ROOT / "ops" / "subscription_load_probe.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(probe),
            "--total",
            "12",
            "--concurrency",
            "6",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(ROOT),
    )
    tail = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return False, tail[-400:]
    return True, "subscription_load_probe 12×6 exit 0"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip-sub-probe", action="store_true", help="skip 12-request load probe")
    args = ap.parse_args()

    checks: list[tuple[str, bool, str]] = []
    for name, fn in [
        ("ams_bundle", check_ams_bundle),
        ("panel_api", check_panel_api),
        ("sub_edges", check_sub_edges),
        ("postgres_luks", check_postgres_luks),
    ]:
        ok, detail = fn()
        checks.append((name, ok, detail))

    if not args.skip_sub_probe:
        ok, detail = check_sub_load_probe()
        checks.append(("sub_load_probe", ok, detail))

    report = {
        "probe": "ams_safe_deploy",
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
        "all_ok": all(ok for _, ok, _ in checks),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for n, ok, d in checks:
            mark = "OK" if ok else "FAIL"
            safe = d.encode("ascii", errors="replace").decode("ascii")
            print(f"[{mark}] {n}: {safe}")

    if not report["all_ok"]:
        print("AMS_SAFE_DEPLOY_FAIL", file=sys.stderr)
        return 1
    print("AMS_SAFE_DEPLOY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
