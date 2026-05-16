#!/bin/bash
# Run ON Latvia as root (panel stack moved; patches dir may still live here).
# Syncs /opt/remnawave/patches -> AMS /opt/remnawave/patches.
# Requires SSH from this host to AMS (e.g. /root/.ssh/id_ed25519).
# Usage: AMS_IP=168.100.11.140 AMS_SSH_PORT=3344 bash lv-rsync-patches-to-ams.sh
set -euo pipefail
AMS_IP="${AMS_IP:-168.100.11.140}"
AMS_SSH_PORT="${AMS_SSH_PORT:-3344}"
SRC="${SRC:-/opt/remnawave/patches}"
SSH_BASE=(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p "${AMS_SSH_PORT}" "root@${AMS_IP}")
if [[ ! -d "$SRC" ]]; then
  echo "ERROR: missing $SRC" >&2
  exit 1
fi
"${SSH_BASE[@]}" "mkdir -p /opt/remnawave/patches"
if command -v rsync >/dev/null 2>&1; then
  echo "Using rsync..."
  rsync -az --delete -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p ${AMS_SSH_PORT}" \
    "${SRC}/" "root@${AMS_IP}:/opt/remnawave/patches/"
else
  echo "rsync not found; using tar over ssh..."
  tar -C "$(dirname "$SRC")" -czf - "$(basename "$SRC")" | "${SSH_BASE[@]}" "tar -xzf - -C /opt/remnawave"
fi
echo "--- AMS listing ---"
"${SSH_BASE[@]}" "ls -la /opt/remnawave/patches"
