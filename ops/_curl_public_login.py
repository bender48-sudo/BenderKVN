#!/usr/bin/env python3
import json
import shlex
import subprocess

body = json.dumps({"username": "Vinni", "password": "wrong"})
cmd = (
    "curl -sk -w '\\nHTTP:%{http_code}\\n' "
    "-X POST https://k9x2m1.conntest.xyz:2053/api/auth/login "
    f"-H {shlex.quote('Content-Type: application/json')} "
    f"--data-binary {shlex.quote(body)} "
    f"-H {shlex.quote('Origin: https://k9x2m1.conntest.xyz:2053')} "
    f"-H {shlex.quote('Referer: https://k9x2m1.conntest.xyz:2053/auth/login')} "
    f"-H {shlex.quote('X-Remnawave-Client-Type: browser')}"
)
subprocess.run(["ssh", "-o", "BatchMode=yes", "bvpn-ams", cmd], check=False)
