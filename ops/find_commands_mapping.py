#!/usr/bin/env python3
import subprocess

subprocess.run(
    [
        "ssh",
        "-o",
        "BatchMode=yes",
        "bvpn-ams",
        "sudo docker exec remnawave find /opt/app/dist/libs/contract -name '*commands*.js'",
    ],
    check=False,
)
