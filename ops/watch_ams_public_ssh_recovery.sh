#!/usr/bin/env bash
# LV watch: when AMS ops SSH (private 168.100.11.52:22) is up, run recovery:
#   1) pull-latest-dump-ams-to-lv.sh  (priority — backup stale since 2026-06-20)
#   2) push_sub_config_generation_ams.py --generation 21
# Read-only probe between actions; idempotent state in /var/lib/bvpn/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/ams_ops_env.sh"

OPS_DIR="${OPS_DIR:-/opt/scripts}"
LOG="${LOG:-/var/log/bvpn-ams-public-ssh-watch.log}"
STATE_DIR="${STATE_DIR:-/var/lib/bvpn}"
STATE_FILE="${STATE_DIR}/ams-public-ssh-watch.state"
INCIDENT_ID="${INCIDENT_ID:-ams_private_ops_20260626}"
TARGET_GEN="${TARGET_GEN:-21}"
PUSH_REASON="${PUSH_REASON:-canary_b_relay2_stable_direct_broadcast}"
STILL_DOWN_EVERY_SEC="${STILL_DOWN_EVERY_SEC:-1800}"

mkdir -p "${STATE_DIR}"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "${LOG}"
}

_notify_admin() {
  local msg="$1"
  for f in /etc/bvpn/balancer.env /opt/remna-shop/.env; do
    if [[ -f "$f" ]]; then
      # shellcheck disable=SC1091
      source "$f"
      break
    fi
  done
  local token="${BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
  local chat="${ADMIN_CHAT_ID:-${ADMIN_TELEGRAM_ID:-}}"
  [[ -n "${token}" && -n "${chat}" ]] || return 0
  curl -s -X POST "https://api.telegram.org/bot${token}/sendMessage" \
    -d "chat_id=${chat}" \
    --data-urlencode "text=${msg}" >/dev/null 2>&1 || true
}

probe_ssh() {
  local key args
  key="$(ams_ops_ssh_key)" || return 1
  mapfile -t args < <(ams_ops_ssh_base)
  ssh "${args[@]}" \
    -o BatchMode=yes \
    -o ConnectTimeout=12 \
    'echo ok' 2>/dev/null | grep -qx ok
}

load_state() {
  incident_id="${INCIDENT_ID}"
  last_probe="unknown"
  pull_ok="0"
  push_ok="0"
  completed="0"
  last_still_down_log="0"
  last_pull_file=""
  if [[ -f "${STATE_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${STATE_FILE}"
  fi
}

save_state() {
  cat >"${STATE_FILE}.tmp" <<EOF
incident_id=${incident_id}
last_probe=${last_probe}
pull_ok=${pull_ok}
push_ok=${push_ok}
completed=${completed}
last_still_down_log=${last_still_down_log}
last_pull_file=${last_pull_file}
updated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
  mv -f "${STATE_FILE}.tmp" "${STATE_FILE}"
}

run_pull() {
  local pull="${OPS_DIR}/pull-latest-dump-ams-to-lv.sh"
  if [[ ! -x "$pull" ]]; then
    log "ERROR pull script missing: $pull"
    return 1
  fi
  log "ACTION pull-latest-dump-ams-to-lv.sh (priority)"
  if bash "$pull" >>"${LOG}" 2>&1; then
    last_pull_file="$(ls -1t /opt/backups/remnawave-*.sql.gz 2>/dev/null | head -1 || true)"
    pull_ok="1"
    save_state
    log "OK pull verified newest=${last_pull_file:-unknown}"
    return 0
  fi
  log "FAIL pull — will retry next cron tick"
  return 1
}

run_push_gen() {
  local push_py="${OPS_DIR}/push_sub_config_generation_ams.py"
  if [[ ! -f "$push_py" ]]; then
    log "ERROR push script missing: $push_py"
    return 1
  fi
  log "ACTION push_sub_config_generation_ams.py --generation ${TARGET_GEN}"
  if AMS_OPS_HOST="${AMS_OPS_IP}" AMS_OPS_SSH_PORT="${AMS_OPS_PORT}" \
    python3 "$push_py" --generation "${TARGET_GEN}" --reason "${PUSH_REASON}" >>"${LOG}" 2>&1; then
    push_ok="1"
    save_state
    log "OK push sub_config_generation=${TARGET_GEN}"
    return 0
  fi
  log "FAIL push gen${TARGET_GEN} — will retry next cron tick"
  return 1
}

main() {
  load_state

  if probe_ssh; then
    if [[ "${last_probe}" != "up" ]]; then
      log "AMS ops SSH UP ${AMS_OPS_IP}:${AMS_OPS_PORT} incident=${INCIDENT_ID}"
      _notify_admin "✅ AMS ops SSH up (${AMS_OPS_IP}:${AMS_OPS_PORT}). Starting recovery: backup pull → gen${TARGET_GEN} push."
      last_probe="up"
      save_state
    fi

    if [[ "${completed}" == "1" ]]; then
      exit 0
    fi

    if [[ "${pull_ok}" != "1" ]]; then
      run_pull || exit 0
    fi

    if [[ "${pull_ok}" == "1" && "${push_ok}" != "1" ]]; then
      run_push_gen || exit 0
    fi

    if [[ "${pull_ok}" == "1" && "${push_ok}" == "1" && "${completed}" != "1" ]]; then
      completed="1"
      save_state
      log "RECOVERY COMPLETE incident=${INCIDENT_ID} pull=${last_pull_file:-ok} push=gen${TARGET_GEN}"
      _notify_admin "✅ AMS recovery done: fresh backup pulled + gen${TARGET_GEN} pushed. Watch idle."
    fi
    exit 0
  fi

  now_epoch="$(date +%s)"
  if [[ "${last_probe}" == "up" ]]; then
    log "AMS ops SSH LOST ${AMS_OPS_IP}:${AMS_OPS_PORT} — reset recovery flags"
    last_probe="down"
    pull_ok="0"
    push_ok="0"
    completed="0"
    last_still_down_log="${now_epoch}"
    save_state
    exit 0
  fi

  last_probe="down"
  if (( now_epoch - last_still_down_log >= STILL_DOWN_EVERY_SEC )); then
    log "still down ${AMS_OPS_IP}:${AMS_OPS_PORT} (check key in AMS authorized_keys)"
    last_still_down_log="${now_epoch}"
    save_state
  fi
}

main "$@"
