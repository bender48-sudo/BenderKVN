#!/usr/bin/env bash
set -euo pipefail
source /etc/bvpn/balancer.env
code=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${PANEL_TOKEN}" \
  -H "X-Forwarded-Proto: https" \
  -H "X-Forwarded-For: 127.0.0.1" \
  "${PANEL_URL}/api/users")
echo "HTTP ${code}"
