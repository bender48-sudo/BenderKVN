#!/usr/bin/env python3
import subprocess

remote = "sudo docker exec remnawave cat /opt/app/dist/src/common/decorators/get-ip/get-ip.decorator.js"
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", remote], check=False)
