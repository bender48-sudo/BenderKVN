#!/usr/bin/env bash
# P3-FLOW-11-LIVE-01: add portal/start/status/setup to p4n7q.conntest.xyz:8443 (backup apex).
set -euo pipefail
CF=/etc/caddy/Caddyfile
BK="/etc/caddy/Caddyfile.bak-pre-p4n7q-portal-$(date +%Y%m%d-%H%M%S)"
cp -a "$CF" "$BK"

python3 <<'PY'
import re
import sys
from pathlib import Path

path = Path("/etc/caddy/Caddyfile")
text = path.read_text(encoding="utf-8")
marker = "p4n7q.conntest.xyz:8443 {"
if marker not in text:
    sys.exit("ERROR: p4n7q.conntest.xyz:8443 block not found")

if "handle_path /portal/*" in text.split(marker, 1)[1].split("k9x2m1.conntest.xyz:8443", 1)[0]:
    print("OK: p4n7q portal routes already present")
    raise SystemExit(0)

portal_block = """
    # P3-FLOW-11-LIVE-01 — backup apex: portal + bootstrap (not only /api/sub)
    handle /status {
        root * /var/www/bvpn-status
        rewrite * /index.html
        file_server
    }
    handle_path /start/* {
        root * /var/www/bvpn-portal
        try_files {path} /index.html
        file_server
    }
    handle /start {
        redir /start/ 308
    }
    handle_path /portal/* {
        root * /var/www/bvpn-portal
        try_files {path} /index.html
        file_server
    }
    handle /portal {
        redir /portal/ 308
    }
    handle /setup/api/* {
        rate_limit {
            zone setup_api_per_ip_p4 {
                key {remote_host}
                events 30
                window 1m
            }
        }
        uri strip_prefix /setup/api
        reverse_proxy 127.0.0.1:8871 {
            header_up Host {host}
        }
    }
    @setup_pages_p4 path /setup /setup/*
    handle @setup_pages_p4 {
        root * /var/www/bvpn-portal
        @not_api not path /setup/api/*
        handle @not_api {
            rewrite * /setup.html
            file_server
        }
    }
"""

# Insert before @blocked inside p4n7q:8443
seg_start = text.index(marker)
seg_end = text.index("k9x2m1.conntest.xyz:8443", seg_start)
segment = text[seg_start:seg_end]
blocked = segment.find("    @blocked {")
if blocked < 0:
    sys.exit("ERROR: @blocked not found in p4n7q:8443")
new_segment = segment[:blocked] + portal_block + segment[blocked:]
# widen @blocked exceptions
new_segment = new_segment.replace(
    """    @blocked {
        not path /api/sub/*
        not path /assets/*
        not path /locales/*
    }""",
    """    @blocked {
        not path /api/sub/*
        not path /assets/*
        not path /locales/*
        not path /status
        not path /status/*
        not path /start
        not path /start/*
        not path /portal
        not path /portal/*
        not path /setup
        not path /setup/*
    }""",
    1,
)
text = text[:seg_start] + new_segment + text[seg_end:]
path.write_text(text, encoding="utf-8")
print("PATCH_P4N7Q_PORTAL_OK")
PY

caddy validate --config "$CF"
systemctl restart caddy
sleep 2
systemctl is-active caddy
echo "CADDY_RESTART_OK"
