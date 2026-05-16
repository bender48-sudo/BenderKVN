#!/usr/bin/env python3
import json, subprocess

def tok():
    for line in open("/etc/bvpn/balancer.env"):
        if line.startswith("PANEL_TOKEN="):
            return line.split("=",1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")

t = tok()
uuid = "9ebbce97-ae45-4f39-a7e6-d7e675a94a73"
base = "https://k9x2m1.conntest.xyz:2053"
body = json.dumps({"uuid": uuid, "noop": True})

def try_method(method: str, path: str) -> None:
    url = base + path
    p = subprocess.run(
        ["curl", "-sk", "-o", "/tmp/r.txt", "-w", "%{http_code}", "-X", method,
         "-H", f"Authorization: Bearer {t}", "-H", "Content-Type: application/json",
         "--data-binary", body, url],
        capture_output=True,
    )
    code = p.stdout.decode().strip()
    with open("/tmp/r.txt") as f:
        head = f.read(200)
    print(method, path, "->", code, head[:120].replace("\n", " "))

for method in ("PATCH", "PUT", "POST"):
    try_method(method, f"/api/subscription-templates/{uuid}")
    try_method(method, f"/api/subscription-templates")
