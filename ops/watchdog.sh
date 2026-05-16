#!/bin/bash
# bvpn-watchdog: runs on NL, every 15 min, probes LV monitor health.
# If monitor.sh or ru-monitor.py logs are stale > THRESHOLD, fires one ALERT
# to Telegram and creates a per-monitor antispam marker (cleared on recovery).
set -uo pipefail

ADMIN_CHAT_ID="924498094"
BOT_TOKEN_FILE="/etc/bvpn/bot-token"
STATE_DIR="/var/lib/bvpn-watchdog"
THRESHOLD=1800  # 30 minutes
KEY="/root/.ssh/lv_watchdog"
LV="root@176.126.162.158"
LV_PORT=3333
LOG="/var/log/bvpn-watchdog.log"

mkdir -p "$STATE_DIR"
ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*" >> "$LOG"; }

if [ ! -s "$BOT_TOKEN_FILE" ]; then
    log "FATAL: $BOT_TOKEN_FILE missing"
    exit 0
fi
BOT_TOKEN=$(tr -d ' \n' < "$BOT_TOKEN_FILE")

tg() {
    local text="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ADMIN_CHAT_ID}" \
        -d "parse_mode=HTML" \
        --data-urlencode "text=${text}" > /dev/null 2>&1
}

fire_alert() {
    local key="$1" text="$2"
    local f="$STATE_DIR/alert_${key}"
    if [ ! -f "$f" ]; then
        tg "$text"
        touch "$f"
        log "ALERT $key sent"
    fi
}

fire_recover() {
    local key="$1" text="$2"
    local f="$STATE_DIR/alert_${key}"
    if [ -f "$f" ]; then
        tg "$text"
        rm -f "$f"
        log "RECOVER $key sent"
    fi
}

# Probe LV.
probe=$(ssh -i "$KEY" -p "$LV_PORT" \
        -o BatchMode=yes \
        -o StrictHostKeyChecking=accept-new \
        -o ConnectTimeout=10 \
        "$LV" 2>/dev/null) || probe=""

if [ -z "$probe" ]; then
    fire_alert "lv_ssh_dead" "$(printf '🚨 <b>BenderVPN WATCHDOG</b>\n\n❌ NL→LV SSH probe failed\n🕐 %s\n🖥 176.126.162.158\n\nLV likely unreachable from NL (network/host issue).' "$(ts)")"
    log "probe empty; LV unreachable"
    exit 0
fi
fire_recover "lv_ssh_dead" "$(printf '✅ <b>BenderVPN WATCHDOG</b>\n\n🟢 NL→LV SSH probe restored\n🕐 %s' "$(ts)")"

monitor_sh=$(echo "$probe" | awk -F= '/^monitor_sh=/{print $2}')
ru_monitor=$(echo "$probe" | awk -F= '/^ru_monitor=/{print $2}')
now=$(echo "$probe"      | awk -F= '/^now=/{print $2}')

[ -z "${monitor_sh:-}" ] && monitor_sh=0
[ -z "${ru_monitor:-}" ] && ru_monitor=0
[ -z "${now:-}" ] && now=$(date +%s)

age_m=$(( now - monitor_sh ))
age_r=$(( now - ru_monitor ))

log "probe ok: monitor.sh age=${age_m}s ru-monitor.py age=${age_r}s"

check() {
    local name="$1" age="$2" key="$3" alert_label="$4"
    if [ "$age" -gt "$THRESHOLD" ]; then
        fire_alert "$key" "$(printf '🚨 <b>BenderVPN WATCHDOG</b>\n\n❌ %s — stale\n🕐 last tick %ds ago (threshold %ds)\n🖥 LV monitor host\n\nCheck cron / systemd-cron / disk on LV.' "$alert_label" "$age" "$THRESHOLD")"
    else
        fire_recover "$key" "$(printf '✅ <b>BenderVPN WATCHDOG</b>\n\n🟢 %s — back online\n🕐 last tick %ds ago' "$alert_label" "$age")"
    fi
}

check "monitor.sh"    "$age_m" "monitor_sh_stale" "monitor.sh"
check "ru-monitor.py" "$age_r" "ru_monitor_stale" "ru-monitor.py"
