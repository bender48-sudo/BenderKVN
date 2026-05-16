#!/usr/bin/env python3
import subprocess

remote = "sudo docker exec remnawave sed -n '1,220p' /opt/app/dist/src/modules/auth/auth.service.js"
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", remote], check=False)
