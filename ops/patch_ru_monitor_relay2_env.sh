#!/usr/bin/env bash
# Append RELAY2 vars to live LV /etc/bvpn/ru-monitor.env if missing.
set -euo pipefail
ENV=/etc/bvpn/ru-monitor.env
grep -q '^RELAY2_HOST=' "$ENV" 2>/dev/null && exit 0
cat >>"$ENV" <<'EOF'

# Q120 relay#2 Timeweb Cloud RU (2026-05-29)
RELAY2_HOST=46.173.28.252
RELAY2_SSH_PORT=22
RELAY2_SSH_USER=bvpncheck
RELAY2_SSH_KEY=/root/.ssh/id_ed25519_relay2
EOF
echo RELAY2_ENV_APPENDED
