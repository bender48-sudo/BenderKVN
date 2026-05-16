#!/usr/bin/env python3
import subprocess

cmd = (
    "sudo docker exec remnawave grep -rn REMNAWAVE_BYPASS "
    "/opt/app/dist/src --include='*.js' | head -40"
)
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", cmd], check=False)
