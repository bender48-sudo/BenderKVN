#!/usr/bin/env bash
# P2-RED-SUB-EDGE-JURISDICTION-01: NL Caddy (selfsteal container) → AMS :3010 for /api/sub/*
# Run on bvpn-nl as root. DNS A: n4l8q.conntest.xyz → NL public IP.
set -euo pipefail

FQDN="${SUB_BACKUP_FQDN:-n4l8q.conntest.xyz}"
# NL rw-core binds :8443 (VPN alt); backup HTTPS edge uses :4433 (see EDGE-PORT-RECOMMENDATION.md).
PORT="${EDGE_PUBLIC_PORT:-4433}"
AMS_SUB="${AMS_SUB_UPSTREAM:-168.100.11.140:3010}"
MARKER="SUB_JURISDICTION_BACKUP_NL"
CADDYFILE="/opt/caddy/Caddyfile"
CADDY_CONTAINER="${CADDY_CONTAINER:-caddy-selfsteal}"
LEGACY_CONTAINER="caddy-sub-backup-nl"

if ! docker ps --format '{{.Names}}' | grep -qx "$CADDY_CONTAINER"; then
  echo "FAIL: container ${CADDY_CONTAINER} not running" >&2
  exit 1
fi

# Standalone edge container cannot complete ACME (http-01 hits :443 rw-core). Use host-network Caddy.
if docker ps -a --format '{{.Names}}' | grep -qx "$LEGACY_CONTAINER"; then
  docker rm -f "$LEGACY_CONTAINER" >/dev/null 2>&1 || true
fi

if grep -q "$MARKER" "$CADDYFILE" 2>/dev/null; then
  echo "OK: ${MARKER} already in ${CADDYFILE}"
else
  cp -a "$CADDYFILE" "${CADDYFILE}.bak-pre-${MARKER}-$(date +%Y%m%d-%H%M%S)"
  cat >>"$CADDYFILE" <<EOF

# ${MARKER}
http://${FQDN} {
    redir https://${FQDN}:${PORT}{uri} permanent
}
${FQDN}:${PORT} {
    tls {
        protocols tls1.2 tls1.3
    }
    handle /api/sub/* {
        reverse_proxy http://${AMS_SUB} {
            header_up X-Forwarded-Proto https
            header_up X-Forwarded-For {remote_host}
            header_up Host ${FQDN}
        }
    }
    handle {
        respond "BenderVPN NL backup edge" 200
    }
}
EOF
  docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
  docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
  echo "OK: appended ${MARKER} to ${CADDYFILE}"
fi

if command -v ufw >/dev/null 2>&1; then
  ufw allow "${PORT}/tcp" comment "Backup sub edge ${FQDN}" 2>/dev/null || true
fi

PROBE="${SUB_MONITOR_PROBE_SUFFIX:-api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"
code="000"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  sleep 15
  code="$(curl -sS -m 25 -o /dev/null -w '%{http_code}' "https://${FQDN}:${PORT}/${PROBE}" || echo 000)"
  echo "probe HTTPS ${FQDN}:${PORT}/${PROBE} -> HTTP ${code}"
  if [[ "$code" == "200" || "$code" == "304" ]]; then
    echo "OK: NL backup sub edge (${MARKER})"
    exit 0
  fi
done

echo "WARN: backup edge not 200 yet (ACME/DNS/upstream?)" >&2
docker logs --tail 30 "$CADDY_CONTAINER" 2>&1 || true
exit 1
