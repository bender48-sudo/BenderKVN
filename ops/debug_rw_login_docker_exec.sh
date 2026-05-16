#!/usr/bin/env bash
set -euo pipefail

dc() { sudo docker exec remnawave sh -lc "$1"; }

echo "=== inside: bare POST (no proxy headers) ==="
dc 'curl -sS -w "\nHTTP:%{http_code}\n" -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  --data-binary "{\"username\":\"Vinni\",\"password\":\"wrong\"}"' || true
echo

echo "=== inside: XFP + Host (no port), matches Caddy header_up Host ==="
dc 'curl -sS -w "\nHTTP:%{http_code}\n" -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -H "Host: k9x2m1.conntest.xyz" \
  --data-binary "{\"username\":\"Vinni\",\"password\":\"wrong\"}"' || true
echo

echo "=== inside: XFP + Host :2053 ==="
dc 'curl -sS -w "\nHTTP:%{http_code}\n" -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -H "Host: k9x2m1.conntest.xyz:2053" \
  --data-binary "{\"username\":\"Vinni\",\"password\":\"wrong\"}"' || true
echo

echo "=== inside: match Caddy + Origin :2053 + client-type browser ==="
dc 'curl -sS -w "\nHTTP:%{http_code}\n" -X POST http://127.0.0.1:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -H "Host: k9x2m1.conntest.xyz" \
  -H "Origin: https://k9x2m1.conntest.xyz:2053" \
  -H "Referer: https://k9x2m1.conntest.xyz:2053/auth/login" \
  -H "X-Remnawave-Client-Type: browser" \
  --data-binary "{\"username\":\"Vinni\",\"password\":\"wrong\"}"' || true
echo
