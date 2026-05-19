#!/bin/bash
# P2-RED-EDGE-HEADERS-02: HSTS on lv.conntest.xyz:9443 (selfsteal apex).
set -euo pipefail
CADDYFILE="${1:-/etc/caddy/Caddyfile}"
MARKER='Strict-Transport-Security "max-age=31536000; includeSubDomains"'
if grep -A6 'lv.conntest.xyz:9443' "$CADDYFILE" | grep -q 'Strict-Transport-Security'; then
  echo "lv.conntest.xyz:9443 already has HSTS"
else
  cp -a "$CADDYFILE" "${CADDYFILE}.bak-pre-hsts-9443-lv"
  awk '
    /^lv\.conntest\.xyz:9443 \{/ && !done {
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
  echo "patched HSTS into lv.conntest.xyz:9443 in $CADDYFILE"
fi
caddy validate --config "$CADDYFILE"
systemctl restart caddy
echo "EDGE_HEADERS_9443_LV_OK"
