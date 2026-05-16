#!/usr/bin/env python3
import json, subprocess

def tok():
    for line in open("/etc/bvpn/balancer.env"):
        if line.startswith("PANEL_TOKEN="):
            return line.split("=",1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")

t = tok()
u = "https://k9x2m1.conntest.xyz:2053/api/subscription-templates/9ebbce97-ae45-4f39-a7e6-d7e675a94a73"
p = subprocess.run(["curl","-sk","-H",f"Authorization: Bearer {t}",u],capture_output=True)
d = json.loads(p.stdout)
tj = d["response"]["templateJson"]
print(type(tj), len(tj) if isinstance(tj,str) else tj)
