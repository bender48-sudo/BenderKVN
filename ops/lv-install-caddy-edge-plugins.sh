#!/bin/bash
# Build Caddy v2.11.2 with rate_limit + cache-handler for sub-page HA/cache (VPN-AUD-152/153).
# Requires: /usr/local/go/bin (>=1.22), xcaddy in PATH. Run on bvpn-lv as root.
set -euo pipefail

GO_BIN="${GO_BIN:-/usr/local/go/bin}"
export PATH="${GO_BIN}:$PATH"

if ! command -v xcaddy >/dev/null; then
  echo "ERROR: xcaddy not found" >&2
  exit 1
fi

BUILD_DIR="${BUILD_DIR:-/tmp/caddy-edge-build}"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "==> xcaddy build v2.11.2 + ratelimit + cache-handler in $BUILD_DIR"
xcaddy build v2.11.2 \
  --with github.com/mholt/caddy-ratelimit \
  --with github.com/caddyserver/cache-handler

for mod in http.handlers.rate_limit; do
  if ! ./caddy list-modules 2>/dev/null | grep -qF "$mod"; then
    echo "ERROR: built binary missing $mod" >&2
    exit 1
  fi
done
if ! ./caddy list-modules 2>/dev/null | grep -qF 'http.handlers.cache'; then
  echo "ERROR: built binary missing http.handlers.cache" >&2
  exit 1
fi

CADDY_BIN="${CADDY_BIN:-/usr/bin/caddy}"
BK="${CADDY_BIN}.bak-pre-edge-plugins-$(date +%Y%m%d-%H%M%S)"
cp -a "$CADDY_BIN" "$BK"
install -m 755 ./caddy "$CADDY_BIN"

echo "==> validate installed binary"
"$CADDY_BIN" version
"$CADDY_BIN" list-modules 2>/dev/null | grep -E 'rate_limit|cache' || true
echo "OK: installed (backup $BK)"
