#!/usr/bin/env bash
# AMS ops SSH via private VPC (168.100.11.52:22). Public .140:3344 is legacy fallback only.
# Source from LV cron/scripts: . /opt/scripts/ams_ops_env.sh
AMS_OPS_IP="${AMS_OPS_IP:-${AMS_IP:-168.100.11.52}}"
AMS_OPS_PORT="${AMS_OPS_PORT:-${AMS_PORT:-22}}"

ams_ops_ssh_key() {
  local k
  for k in "${AMS_OPS_SSH_KEY:-}" /root/.ssh/bvpn_ams_ed25519 /root/.ssh/id_ed25519; do
    if [[ -n "${k}" && -f "${k}" ]]; then
      echo "${k}"
      return 0
    fi
  done
  return 1
}

# Connection flags only (for scp — no trailing user@host).
ams_ops_scp_base() {
  local key
  key="$(ams_ops_ssh_key)" || return 1
  printf '%s\n' \
    -i "${key}" \
    -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=accept-new \
    -o ConnectTimeout=20 \
    -P "${AMS_OPS_PORT}"
}

# Full ssh argv suffix: flags + root@host (for ssh remote commands).
ams_ops_ssh_base() {
  local key
  key="$(ams_ops_ssh_key)" || return 1
  printf '%s\n' \
    -i "${key}" \
    -o IdentitiesOnly=yes \
    -o StrictHostKeyChecking=accept-new \
    -o ConnectTimeout=20 \
    -p "${AMS_OPS_PORT}" \
    "root@${AMS_OPS_IP}"
}
