#!/usr/bin/env python3
import subprocess

subprocess.run(
    [
        "ssh",
        "-o",
        "BatchMode=yes",
        "bvpn-ams",
        "sudo docker exec remnawave grep -rn \"LOGIN:\" /opt/app/dist/libs/contract/api --include='*.js' | head -25",
    ],
    check=False,
)
