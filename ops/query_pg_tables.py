#!/usr/bin/env python3
import subprocess

cmd = (
    'sudo docker exec remnawave-db '
    'psql -U postgres -d postgres -tAc '
    '"SELECT tablename FROM pg_tables WHERE schemaname = '
    "'public' ORDER BY tablename LIMIT 30;\""
)
r = subprocess.run(
    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "bvpn-ams", cmd],
    capture_output=True,
    text=True,
    timeout=120,
    check=False,
)
print("stdout:", r.stdout[:4000])
print("stderr:", r.stderr[:2000])
print("code", r.returncode)
