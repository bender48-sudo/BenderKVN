#!/bin/bash
# Expose bot payment webhooks on k9x2m1:8443 -> AMS remna-shop :1488
set -euo pipefail

CADDYFILE="${1:-/etc/caddy/Caddyfile}"
MARKER='handle /yookassa-webhook'

if grep -q "$MARKER" "$CADDYFILE" 2>/dev/null; then
  echo "OK: yookassa webhook route already present"
  exit 0
fi

python3 - "$CADDYFILE" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
needle = "    @sub_path_alt path /api/sub/*\n"
block = """    handle /yookassa-webhook {
        reverse_proxy http://168.100.11.140:1488 {
            header_up Host {host}
            header_up X-Forwarded-For {remote_host}
        }
    }
    handle /crypto-webhook {
        reverse_proxy http://168.100.11.140:1488 {
            header_up Host {host}
            header_up X-Forwarded-For {remote_host}
        }
    }
    handle /cryptobot-webhook {
        reverse_proxy http://168.100.11.140:1488 {
            header_up Host {host}
            header_up X-Forwarded-For {remote_host}
        }
    }

    @sub_path_alt path /api/sub/*
"""
if needle not in text:
    print("ERROR: anchor @sub_path_alt not found in k9 :8443 block", file=sys.stderr)
    sys.exit(1)
open(path + ".bak-pre-yookassa-webhook", "w", encoding="utf-8").write(text)
open(path, "w", encoding="utf-8").write(text.replace(needle, block, 1))
print("OK: inserted payment webhook routes")
PY

caddy validate --config "$CADDYFILE"
systemctl reload caddy || systemctl restart caddy
echo "CADDY_YOOKASSA_WEBHOOK_OK"
