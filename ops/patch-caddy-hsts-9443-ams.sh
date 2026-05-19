#!/bin/bash
# P2-RED-EDGE-HEADERS-02: HSTS on conntest.xyz:9443 (AMS selfsteal apex).
set -euo pipefail
CADDYFILE="${1:-/etc/caddy/Caddyfile}"
if grep -A6 'conntest.xyz:9443' "$CADDYFILE" | grep -q 'Strict-Transport-Security'; then
  echo "conntest.xyz:9443 already has HSTS"
else
  cp -a "$CADDYFILE" "${CADDYFILE}.bak-pre-hsts-9443-ams"
  awk '
    /^conntest\.xyz:9443 \{/ && !done {
      print
      print "    header {"
      print "        Strict-Transport-Security \"max-age=31536000; includeSubDomains\""
      print "        X-Content-Type-Options \"nosniff\""
      print "    }"
      done=1
      next
    }
    { print }
  ' "$CADDYFILE" > "${CADDYFILE}.tmp" && mv "${CADDYFILE}.tmp" "$CADDYFILE"
  echo "patched HSTS into conntest.xyz:9443 in $CADDYFILE"
fi
caddy validate --config "$CADDYFILE"
systemctl restart caddy
echo "EDGE_HEADERS_9443_AMS_OK"
