#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_urls  # noqa: E402


def tok():
    for line in open("/etc/bvpn/balancer.env"):
        if line.startswith("PANEL_TOKEN="):
            return line.split("=",1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")

t = tok()
u = site_urls.PANEL_URL + "/api/nodes"
p = subprocess.run(["curl","-sk","-H",f"Authorization: Bearer {t}",u],capture_output=True)
d = json.loads(p.stdout)
r = d.get("response", d)
for x in r:
    print(x.get("name"), x.get("address"), "connected=", x.get("isConnected"))
