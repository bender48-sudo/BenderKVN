#!/bin/bash
# Hotfix: disable Souin cache on /api/sub/* — was serving 344B plain vless instead of full JSON.
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK=/etc/caddy/Caddyfile.bak-pre-sub-cache-off-$(date +%Y%m%d-%H%M%S)
cp -a "$CF" "$BK"

python3 <<'PY'
import re
from pathlib import Path

path = Path("/etc/caddy/Caddyfile")
text = path.read_text()

# Remove global cache order if present
text = re.sub(r"^\{\s*\n\s*order cache before reverse_proxy\s*\n\}\s*\n\n", "", text, count=1, flags=re.M)

# Remove cache { ttl ... } block inside sub_api handle
text = re.sub(
    r"\n\s*cache \{\s*\n\s*ttl [^\n]+\s*\n\s*\}\s*\n",
    "\n",
    text,
    count=1,
)

if "cache {" in text and "/api/sub" in text:
    raise SystemExit("ERROR: cache block still present near sub_api")

path.write_text(text)
print("OK: removed Souin cache from sub_api handle")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
PROBE="${SUB_MONITOR_PROBE_SUFFIX:-api/sub/H91mGJ1f2hQv5zaoQD8hKCvha}"
curl -s -m 20 -H 'User-Agent: Happ/1.9.4 (iOS)' -w 'trial ct:%{content_type} bytes:%{size_download}\n' \
  "https://p4n7q.conntest.xyz:8443/${PROBE}" -o /dev/null
echo "OK: cache disabled (backup $BK)"
