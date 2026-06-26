#!/bin/bash
# Run ON Latvia as root (panel stack moved; patches dir may still live here).
# Syncs /opt/remnawave/patches -> AMS /opt/remnawave/patches.
# Requires SSH from this host to AMS (e.g. /root/.ssh/id_ed25519).
# Usage: bash lv-rsync-patches-to-ams.sh  (defaults: 168.100.11.52:22)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/ams_ops_env.sh"
SRC="${SRC:-/opt/remnawave/patches}"
mapfile -t _SSH_BASE < <(ams_ops_ssh_base)
SSH_BASE=(ssh "${_SSH_BASE[@]}" -o ConnectTimeout=15)
if [[ ! -d "$SRC" ]]; then
  echo "ERROR: missing $SRC" >&2
  exit 1
fi
"${SSH_BASE[@]}" "mkdir -p /opt/remnawave/patches"
if command -v rsync >/dev/null 2>&1; then
  echo "Using rsync..."
  rsync -az --delete -e "ssh ${_SSH_BASE[*]} -o ConnectTimeout=15" \
    "${SRC}/" "root@${AMS_OPS_IP}:/opt/remnawave/patches/"
else
  echo "rsync not found; using tar over ssh..."
  tar -C "$(dirname "$SRC")" -czf - "$(basename "$SRC")" | "${SSH_BASE[@]}" "tar -xzf - -C /opt/remnawave"
fi
echo "--- AMS listing ---"
"${SSH_BASE[@]}" "ls -la /opt/remnawave/patches"
