#!/usr/bin/env python3
import subprocess


def run(label: str, cmd: str) -> None:
    print(f"\n### {label} ###\n")
    subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", cmd], check=False)


run("auth/login paths", "sudo docker exec remnawave grep -rn auth/login /opt/app/dist/src 2>/dev/null | head -40")
run(
    "FORBIDDEN in auth module",
    "sudo docker exec remnawave grep -rn FORBIDDEN /opt/app/dist/src/modules/auth 2>/dev/null | head -40",
)
run(
    "csrf case-insensitive dist",
    "sudo docker exec remnawave grep -rni csrf /opt/app/dist/src 2>/dev/null | head -40",
)
run(
    "Throttler / rate",
    "sudo docker exec remnawave grep -rni throttl /opt/app/dist/src 2>/dev/null | head -30",
)
