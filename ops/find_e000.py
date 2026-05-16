#!/usr/bin/env python3
import subprocess

remote = (
    "sudo docker exec remnawave sh -lc "
    "'grep -r E000 /opt/app/dist --include=\"*.js\" 2>/dev/null | head -40'"
)
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", remote], check=False)
