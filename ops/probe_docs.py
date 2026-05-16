#!/usr/bin/env python3
import subprocess
t=open("/etc/bvpn/balancer.env").read()
tok=[l.split("=",1)[1].strip().strip('"').strip("'") for l in t.splitlines() if l.startswith("PANEL_TOKEN=")][0]
for path in ["/api/docs-json","/docs-json","/api-json","/swagger/json"]:
    u="https://k9x2m1.conntest.xyz:2053"+path
    p=subprocess.run(["curl","-sk","-o","/tmp/o.json","-w","%{http_code}","-H",f"Authorization: Bearer {tok}",u],capture_output=True)
    c=p.stdout.decode().strip()
    import os
    sz=os.path.getsize("/tmp/o.json")
    print(path, "http", c, "bytes", sz)
