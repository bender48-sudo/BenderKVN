#!/bin/bash
# Build Caddy v2.11.2 with github.com/mholt/caddy-ratelimit and install on bvpn-lv.
# Requires: /usr/local/go/bin (>=1.22), xcaddy in PATH.
set -euo pipefail

GO_BIN="${GO_BIN:-/usr/local/go/bin}"
export PATH="${GO_BIN}:$PATH"

if ! command -v xcaddy >/dev/null; then
  echo "ERROR: xcaddy not found" >&2
  exit 1
fi

BUILD_DIR="${BUILD_DIR:-/tmp/caddy-rl-build}"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "==> xcaddy build v2.11.2 + caddy-ratelimit in $BUILD_DIR"
xcaddy build v2.11.2 --with github.com/mholt/caddy-ratelimit

if ! ./caddy list-modules 2>/dev/null | grep -q 'http.handlers.rate_limit'; then
  echo "ERROR: built binary missing http.handlers.rate_limit" >&2
  exit 1
fi

CADDY_BIN="${CADDY_BIN:-/usr/bin/caddy}"
BK="${CADDY_BIN}.bak-pre-ratelimit-$(date +%Y%m%d-%H%M%S)"
cp -a "$CADDY_BIN" "$BK"
install -m 755 ./caddy "$CADDY_BIN"

echo "==> validate installed binary"
"$CADDY_BIN" version
"$CADDY_BIN" list-modules 2>/dev/null | grep -E 'rate_limit|caddy$' || true
echo "OK: installed (backup $BK)"
