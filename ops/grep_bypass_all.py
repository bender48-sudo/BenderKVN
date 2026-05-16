#!/usr/bin/env python3
import subprocess

cmd = "sudo docker exec remnawave grep -rn 'BYPASS_HTTPS' /opt/app/dist | head -30"
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", cmd], check=False)
