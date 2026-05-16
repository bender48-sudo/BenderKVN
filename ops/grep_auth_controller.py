#!/usr/bin/env python3
import subprocess

remote = "sudo docker exec remnawave grep -n Controller\\|Post\\|Get /opt/app/dist/src/modules/auth/auth.controller.js | head -60"
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", remote], check=False)
