#!/usr/bin/env python3
import subprocess

remote = "sudo docker exec remnawave grep -rn getStatus\\|auth/status\\|/status\\) /opt/app/dist/src/modules/auth/*.js 2>/dev/null | head -20"
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", remote], check=False)
