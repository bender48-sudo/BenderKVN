#!/usr/bin/env python3
"""GET /api/auth/status via public LV URL (same path browser uses)."""
import subprocess

cmd = (
    "curl -sk "
    "'https://k9x2m1.conntest.xyz:2053/api/auth/status' "
    "-H 'X-Remnawave-Client-Type: browser'"
)
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", cmd], check=False)
