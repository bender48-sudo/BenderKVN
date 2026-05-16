#!/usr/bin/env python3
import subprocess

subprocess.run(
    [
        "ssh",
        "-o",
        "BatchMode=yes",
        "bvpn-ams",
        "sudo docker exec remnawave ls /opt/app/dist/libs/contract/commands",
    ],
    check=False,
)
