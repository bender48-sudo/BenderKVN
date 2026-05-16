#!/usr/bin/env python3
import json, subprocess, re

def tok():
    for line in open("/etc/bvpn/balancer.env"):
        if line.startswith("PANEL_TOKEN="):
            return line.split("=",1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")

t = tok()
u = "https://k9x2m1.conntest.xyz:2053/api/docs-json"
p = subprocess.run(["curl","-sk","-H",f"Authorization: Bearer {t}",u],capture_output=True)
if p.returncode:
    print("curl fail", p.stderr)
    raise SystemExit(1)
s = p.stdout.decode("utf-8", errors="replace")
# paths containing subscription and template
for m in re.findall(r'"(/api/[^"]*subscription[^"]*template[^"]*)"', s, re.I):
    print(m)
for m in re.findall(r'"(/api/[^"]*template[^"]*)"', s, re.I):
    if "subscription" in m.lower():
        print("T", m)
