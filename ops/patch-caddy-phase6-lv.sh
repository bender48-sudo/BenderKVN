#!/usr/bin/env bash
# Q087/Q088: sunset :2053 → :8443 redirect; remove public :2054 (brace-safe).
# On LV with admin off use: systemctl restart caddy (not reload).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${DIR}/patch-caddy-phase6-lv-safe.sh"
