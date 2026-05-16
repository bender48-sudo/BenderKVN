#!/usr/bin/env python3
"""PATCH full subscription template object (as GET /response) — Remnawave rejects minimal body."""
from __future__ import annotations

import copy
import json
import subprocess
import sys

try:
    from site_urls import PANEL_URL as DEFAULT_BASE, REMNA_TEMPLATE_UUID as TEMPLATE_UUID  # noqa: E402
except ImportError:  # single-file deploy on prod without ops/site_urls.py
    DEFAULT_BASE = "https://k9x2m1.conntest.xyz:2053"
    TEMPLATE_UUID = "9ebbce97-ae45-4f39-a7e6-d7e675a94a73"


def token() -> str:
    for line in open("/etc/bvpn/balancer.env"):
        if line.startswith("PANEL_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PANEL_TOKEN not found")


def curl_raw(method: str, url: str, body: str | None = None) -> tuple[int, str]:
    tok = token()
    cmd = [
        "curl", "-sk", "-w", "\n%{http_code}", "-X", method,
        "-H", f"Authorization: Bearer {tok}",
        "-H", "Content-Type: application/json; charset=utf-8",
    ]
    if body is not None:
        cmd.extend(["--data-binary", body])
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout.decode("utf-8", errors="replace")
    if "\n" not in out:
        return p.returncode, out
    *rest, code = out.rsplit("\n", 1)
    text = "\n".join(rest)
    try:
        http = int(code.strip())
    except ValueError:
        return p.returncode, out
    return http, text


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    hosts_url = f"{base.rstrip('/')}/api/hosts"
    tpl_get_url = f"{base.rstrip('/')}/api/subscription-templates/{TEMPLATE_UUID}"
    tpl_patch_url = f"{base.rstrip('/')}/api/subscription-templates"

    http, htext = curl_raw("GET", hosts_url)
    if http != 200:
        raise SystemExit(f"GET hosts HTTP {http}: {htext[:500]}")
    hosts = json.loads(htext).get("response", [])
    drop: set[str] = set()
    for h in hosts:
        u = str(h.get("uuid") or "")
        if not u:
            continue
        addr = str(h.get("address") or "")
        rem = str(h.get("remark") or "")
        if "168.100.11.140" in addr or "Relay AMS" in rem:
            drop.add(u)

    print(f"drop {len(drop)} host UUIDs")

    http, ttext = curl_raw("GET", tpl_get_url)
    if http != 200:
        raise SystemExit(f"GET template HTTP {http}: {ttext[:500]}")
    data = json.loads(ttext)
    tpl = copy.deepcopy(data.get("response"))
    if not isinstance(tpl, dict):
        raise SystemExit("no response in GET template")

    doc = tpl.get("templateJson")
    if not isinstance(doc, dict):
        raise SystemExit("no templateJson")

    ih = doc["remnawave"]["injectHosts"]
    sel = ih[0]["selector"]
    vals = sel.get("values") or []
    before = [str(x) for x in vals]
    after = [x for x in before if x not in drop]
    print(f"injectHosts: {len(before)} -> {len(after)}")
    if len(after) == len(before):
        print("nothing to do")
        return

    sel["values"] = after
    tpl["templateJson"] = doc
    if "encodedTemplateYaml" in tpl:
        del tpl["encodedTemplateYaml"]

    minimal = {
        "uuid": tpl.get("uuid") or TEMPLATE_UUID,
        "templateJson": doc,
        "viewPosition": tpl.get("viewPosition"),
        "templateType": tpl.get("templateType"),
    }
    body = json.dumps(minimal, ensure_ascii=False)
    open("/tmp/tpl_patch_full.json", "w", encoding="utf-8").write(body)

    http2, rtext = curl_raw("PATCH", tpl_patch_url, body)
    print(f"PATCH HTTP {http2}")
    if http2 not in (200, 201):
        try:
            rj = json.loads(rtext)
            print(json.dumps(rj, ensure_ascii=False, indent=2)[:1500])
        except json.JSONDecodeError:
            print(rtext[:1500])
        raise SystemExit(1)
    print("OK: template updated")


if __name__ == "__main__":
    main()
