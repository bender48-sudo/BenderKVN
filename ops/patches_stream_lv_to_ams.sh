#!/bin/bash
# Run from a machine with SSH to both hosts (e.g. laptop with ~/.ssh/config).
# Usage: bash patches_stream_lv_to_ams.sh [lv_host] [ams_host]
# Defaults: bvpn-lv bvpn-ams
set -euo pipefail
LV="${1:-bvpn-lv}"
AMS="${2:-bvpn-ams}"
echo "Streaming /opt/remnawave/patches from ${LV} -> ${AMS} ..."
ssh -o BatchMode=yes -o ConnectTimeout=20 "${LV}" 'tar czf - -C /opt/remnawave patches' \
  | ssh -o BatchMode=yes -o ConnectTimeout=20 "${AMS}" 'mkdir -p /opt/remnawave && tar xzf - -C /opt/remnawave && ls -la /opt/remnawave/patches'
echo "OK"
