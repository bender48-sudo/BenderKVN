#!/usr/bin/env python3
import json, subprocess, re

def tok():
    for line in open("/etc/bvpn/balancer.env"):
        if line.startswith("PANEL_TOKEN="):
            return line.split("=",1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")

t = tok()
p = subprocess.run(["curl","-sk","-H",f"Authorization: Bearer {t}","https://k9x2m1.conntest.xyz:2053/api-json"],capture_output=True)
d = json.loads(p.stdout)
paths = d.get("paths") or {}
for path, methods in sorted(paths.items()):
    if "subscription" in path.lower() and "template" in path.lower():
        print(path, sorted(methods.keys()))
