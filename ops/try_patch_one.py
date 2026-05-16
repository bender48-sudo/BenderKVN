#!/usr/bin/env python3
import json, subprocess

def tok():
    for line in open("/etc/bvpn/balancer.env"):
        if line.startswith("PANEL_TOKEN="):
            return line.split("=",1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")

t = tok()
u = "https://k9x2m1.conntest.xyz:2053/api/subscription-templates/9ebbce97-ae45-4f39-a7e6-d7e675a94a73"
p0 = subprocess.run(["curl","-sk","-H",f"Authorization: Bearer {t}",u],capture_output=True)
tpl = json.loads(p0.stdout)["response"]
doc = tpl["templateJson"]
vals = doc["remnawave"]["injectHosts"][0]["selector"]["values"]
# drop first AMS uuid only as test
doc["remnawave"]["injectHosts"][0]["selector"]["values"] = [x for x in vals if x != "9f12152d-3285-4f20-adff-6d01a33e043c"]
body = {"uuid": tpl["uuid"], "templateJson": doc}
raw = json.dumps(body, ensure_ascii=False)
open("/tmp/patch_body.json","w",encoding="utf-8").write(raw)
p1 = subprocess.run(["curl","-skw","\nHTTP:%{http_code}\n","-X","PATCH","-H",f"Authorization: Bearer {t}","-H","Content-Type: application/json; charset=utf-8","--data-binary","@/tmp/patch_body.json",u],capture_output=True)
print(p1.stdout.decode()[-2000:])
