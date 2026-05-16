#!/usr/bin/env python3
import subprocess

remote = "sudo docker exec remnawave cat /opt/app/dist/src/common/exception/http-exception.filter.js"
r = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "bvpn-ams", remote],
    capture_output=True,
    text=True,
    check=False,
)
print(r.stdout[:12000])
