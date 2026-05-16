#!/usr/bin/env python3
"""P2-RED-SUB-01: probe all subscription public origins; detect HTTP/body drift.

Exit 0 when every origin returns 200/304 and subscription body hashes match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from typing import Any

from site_urls import sub_all_probe_urls

_HAPP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _fetch_curl(url: str, timeout: float) -> tuple[int | None, str | None, str | None]:
    import os
    import tempfile
    import shutil

    if not shutil.which("curl"):
        return None, None, "curl not found"
    fd, path = tempfile.mkstemp(prefix="sub_probe_")
    os.close(fd)
    try:
        code_s = subprocess.check_output(
            [
                "curl",
                "-sS",
                "-m",
                str(int(max(timeout, 5))),
                "-A",
                _HAPP_UA,
                "-o",
                path,
                "-w",
                "%{http_code}",
                url,
            ],
            stderr=subprocess.STDOUT,
        )
        code = int(code_s.decode().strip())
        with open(path, "rb") as f:
            payload = f.read()
        digest = hashlib.sha256(payload).hexdigest() if payload else None
        return code, digest, None
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _fetch_urllib(url: str, timeout: float) -> tuple[int | None, str | None, str | None]:
    import ssl
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": _HAPP_UA})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            return resp.getcode(), hashlib.sha256(body).hexdigest(), None
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, hashlib.sha256(body).hexdigest() if body else None, None
    except Exception as e:
        return None, None, str(e)


def _fetch(url: str, timeout: float) -> tuple[int | None, str | None, str | None]:
    try:
        return _fetch_curl(url, timeout)
    except Exception as curl_err:
        code, digest, err = _fetch_urllib(url, timeout)
        if code is not None:
            return code, digest, err
        return None, None, f"curl: {curl_err}; urllib: {err}"


def main() -> int:
    p = argparse.ArgumentParser(description="Subscription multi-origin drift probe")
    p.add_argument("--timeout", type=float, default=25.0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    urls = sub_all_probe_urls()
    if len(urls) < 2:
        print("FAIL: need >=2 origins (SUB_PUBLIC + SUB_ALT_PUBLIC_ORIGINS)", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    ok_codes = {200, 304}
    ref_hash: str | None = None

    for url in urls:
        code, digest, err = _fetch(url, args.timeout)
        row: dict[str, Any] = {"url": url, "http_code": code, "sha256": digest, "error": err}
        results.append(row)
        if code not in ok_codes or not digest:
            continue
        if ref_hash is None:
            ref_hash = digest
        elif digest != ref_hash:
            row["drift"] = True

    hashes = {r["sha256"] for r in results if r.get("sha256")}
    drift = len(hashes) > 1
    all_ok = all(r.get("http_code") in ok_codes and r.get("sha256") for r in results)

    report = {
        "origins": len(urls),
        "all_ok": all_ok,
        "body_drift": drift,
        "reference_sha256": ref_hash,
        "results": results,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for r in results:
            flag = " DRIFT" if r.get("drift") else ""
            print(f"{r['url']}: HTTP {r['http_code']} sha256={r.get('sha256', '—')}{flag}")
        print(f"all_ok={all_ok} body_drift={drift}")

    if not all_ok or drift:
        return 1
    print("SUB_MULTI_ORIGIN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
