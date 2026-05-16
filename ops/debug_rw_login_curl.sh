#!/usr/bin/env bash
set -euo pipefail
BODY='{"username":"Vinni","password":"wrong"}'
HDR_CT='Content-Type: application/json'

run() {
  local label="$1"
  shift
  echo "=== $label ==="
  curl -sS -w "\nHTTP:%{http_code}\n" "$@" || true
  echo
}

run "bare POST" -X POST http://127.0.0.1:3000/api/auth/login -H "$HDR_CT" --data-binary "$BODY"

run "+ XFP https Host bare (no port)" -X POST http://127.0.0.1:3000/api/auth/login \
  -H "$HDR_CT" -H "X-Forwarded-Proto: https" -H "Host: k9x2m1.conntest.xyz" \
  --data-binary "$BODY"

run "+ XFP Host :2053" -X POST http://127.0.0.1:3000/api/auth/login \
  -H "$HDR_CT" -H "X-Forwarded-Proto: https" -H "Host: k9x2m1.conntest.xyz:2053" \
  --data-binary "$BODY"

run "+ Origin Referer client-type" -X POST http://127.0.0.1:3000/api/auth/login \
  -H "$HDR_CT" -H "X-Forwarded-Proto: https" -H "Host: k9x2m1.conntest.xyz:2053" \
  -H "Origin: https://k9x2m1.conntest.xyz:2053" \
  -H "Referer: https://k9x2m1.conntest.xyz:2053/auth/login" \
  -H "X-Remnawave-Client-Type: browser" \
  --data-binary "$BODY"
