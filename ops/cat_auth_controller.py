#!/usr/bin/env python3
import subprocess

remote = "sudo docker exec remnawave sed -n '1,160p' /opt/app/dist/src/modules/auth/auth.controller.js"
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", remote], check=False)
