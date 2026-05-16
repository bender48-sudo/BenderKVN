#!/usr/bin/env python3
import subprocess

subprocess.run(
    [
        "ssh",
        "-o",
        "BatchMode=yes",
        "bvpn-ams",
        "sudo docker exec remnawave cat /opt/app/dist/libs/contract/commands/auth/login.command.js "
        "/opt/app/dist/libs/contract/commands/auth/get-status.command.js",
    ],
    check=False,
)
