#!/usr/bin/env python3
import subprocess

subprocess.run(
    [
        "ssh",
        "-o",
        "BatchMode=yes",
        "bvpn-ams",
        "sudo docker exec remnawave sed -n '1,120p' /opt/app/dist/libs/contract/commands/auth/index.js",
    ],
    check=False,
)
