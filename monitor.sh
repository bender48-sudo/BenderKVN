#!/bin/bash
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# OPSEC Stage 4: secrets sourced from balancer.env (was hardcoded before)
source /etc/bvpn/balancer.env

# Telegram HTML symbols (bash $'…' — avoids ??? when script encoding/locale breaks UTF-8 literals)
ICON_OK=$'\u2705'
ICON_ALERT=$'\U0001F6A8'
ICON_WARN=$'\u26A0\uFE0F'
ICON_GREEN=$'\U0001F7E2'
ICON_RED=$'\u274C'
FLAG_LV=$'\U0001F1FB\U0001F1F7'
FLAG_NL=$'\U0001F1F3\U0001F1F1'
FLAG_RU=$'\U0001F1F7\U0001F1FA'
FLAG_AMS=$'\U0001F1F3\U0001F1F1'

# Public subscription smoke URL (aligned with daily-report.sh; overrides via balancer.env OK)
SUB_PUBLIC_ORIGIN="${SUB_PUBLIC_ORIGIN:-https://p4n7q.conntest.xyz:8443}"
export SUB_PUBLIC_ORIGIN
SUB_MONITOR_PROBE_URL="${SUB_MONITOR_PROBE_URL:-${SUB_PUBLIC_ORIGIN}/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"
SUB_ALT_PUBLIC_ORIGIN="${SUB_ALT_PUBLIC_ORIGIN:-https://k9x2m1.conntest.xyz:8443}"
SUB_ALT_MONITOR_PROBE_URL="${SUB_ALT_MONITOR_PROBE_URL:-${SUB_ALT_PUBLIC_ORIGIN}/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"

# After P0 migrations panel lives on AMS; balancer.env MUST set this (fallback matches tmpl)
PANEL_URL="${PANEL_URL:-https://k9x2m1.conntest.xyz:8443}"

# Anti-correlation jitter: random delay 0-60s
sleep $((RANDOM % 60))

# ==========================================
# BenderVPN Monitoring Script
# Runs every 5 min via cron
# ==========================================

ADMIN_CHAT_ID="924498094"
# Persistent state dir — survives reboot (was /tmp/bvpn_states; after reboot
# the alert markers vanished and `recover` never fired the RECOVERED message,
# which felt like "монитор не отписал что починилось". 2026-05-14.
STATE_DIR="/var/lib/bvpn-monitor"
# P2-MON-02: не путать с ru-monitor — state.json у него в /var/lib/bvpn-ru-monitor/,
# антиспам-маркеры selfsteal/ru и alert_* этого скрипта — в /var/lib/bvpn-monitor/.
# Таблица путей: docs/DEPLOY.md §6.
LEGACY_STATE_DIR="/tmp/bvpn_states"
LOG_FILE="/var/log/bvpn-monitor.log"
AMS_IP="168.100.11.140"
AMS_SSH_PORT="3344"
AMS_SSH_KEY="/root/.ssh/id_ed25519"

mkdir -p "$STATE_DIR"

# One-time migration: rescue any in-flight alert markers from old /tmp dir so
# active ALERTs don't double-fire and RECOVERED can still close them out.
if [ -d "$LEGACY_STATE_DIR" ]; then
    for f in "$LEGACY_STATE_DIR"/alert_* "$LEGACY_STATE_DIR"/cpu_* "$LEGACY_STATE_DIR"/ru_monitor_*; do
        [ -e "$f" ] || continue
        b=$(basename "$f")
        [ -e "$STATE_DIR/$b" ] || cp -p "$f" "$STATE_DIR/$b"
    done
fi

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

_tg_send() {
    local body="$1"
    local tmp
    tmp=$(mktemp)
    printf '%s' "$body" >"$tmp"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ADMIN_CHAT_ID}" \
        -d "parse_mode=HTML" \
        --data-urlencode "text@${tmp}" > /dev/null 2>&1
    rm -f "$tmp"
}

alert() {
    local check_name="$1"
    local message="$2"
    local state_file="$STATE_DIR/alert_${check_name}"

    if [ ! -f "$state_file" ]; then
        _tg_send "$message"
        touch "$state_file"
        log "ALERT sent: $check_name"
    fi
}

recover() {
    local check_name="$1"
    local message="$2"
    local state_file="$STATE_DIR/alert_${check_name}"

    if [ -f "$state_file" ]; then
        local notify=1
        local rn="$STATE_DIR/recover_notify_${check_name}"
        if [ -f "$rn" ]; then
            local now last
            now=$(date +%s)
            last=$(cat "$rn" 2>/dev/null || echo 0)
            if [ "$((now - last))" -lt "$RECOVER_NOTIFY_MIN_SEC" ]; then
                notify=0
            fi
        fi
        if [ "$notify" -eq 1 ]; then
            _tg_send "$message"
            date +%s >"$rn"
        fi
        rm -f "$state_file"
        date +%s >"$STATE_DIR/cooldown_${check_name}"
        rm -f "$STATE_DIR/fail_streak_${check_name}" "$STATE_DIR/ok_streak_${check_name}"
        log "RECOVERED: $check_name (tg_notify=${notify})"
    fi
}

# Anti-flap: N failures → one ALERT; M successes while alerting → one RECOVERED.
# After RECOVERED, cooldown suppresses new ALERT (short blips at night).
FAIL_STREAK_THRESHOLD="${FAIL_STREAK_THRESHOLD:-3}"
OK_STREAK_THRESHOLD="${OK_STREAK_THRESHOLD:-2}"
RE_ALERT_COOLDOWN_SEC="${RE_ALERT_COOLDOWN_SEC:-900}"
# Не слать RECOVERED в TG чаще раза в час на один check (флап панели :2053→:8443)
RECOVER_NOTIFY_MIN_SEC="${RECOVER_NOTIFY_MIN_SEC:-3600}"

_streak_bump() {
    local f="$1"
    local n=1
    if [ -f "$f" ]; then
        n=$(($(cat "$f" 2>/dev/null || echo 0) + 1))
    fi
    echo "$n" >"$f"
    echo "$n"
}

monitor_check_ok() {
    local name="$1"
    local recover_msg="$2"
    local ok_need="${3:-$OK_STREAK_THRESHOLD}"

    rm -f "$STATE_DIR/fail_streak_${name}"

    if [ ! -f "$STATE_DIR/alert_${name}" ]; then
        rm -f "$STATE_DIR/ok_streak_${name}"
        return 0
    fi

    local n
    n=$(_streak_bump "$STATE_DIR/ok_streak_${name}")
    if [ "$n" -ge "$ok_need" ]; then
        recover "$name" "$recover_msg"
    fi
}

monitor_check_fail() {
    local name="$1"
    local alert_msg="$2"
    local fail_need="${3:-$FAIL_STREAK_THRESHOLD}"

    rm -f "$STATE_DIR/ok_streak_${name}"

    if [ -f "$STATE_DIR/alert_${name}" ]; then
        return 0
    fi

    local cd="$STATE_DIR/cooldown_${name}"
    if [ -f "$cd" ]; then
        local now last
        now=$(date +%s)
        last=$(cat "$cd" 2>/dev/null || echo 0)
        if [ "$((now - last))" -lt "$RE_ALERT_COOLDOWN_SEC" ]; then
            return 0
        fi
    fi

    local n
    n=$(_streak_bump "$STATE_DIR/fail_streak_${name}")
    if [ "$n" -ge "$fail_need" ]; then
        alert "$name" "$alert_msg"
        rm -f "$STATE_DIR/fail_streak_${name}"
    fi
}

_curl_http() {
    curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$@" 2>/dev/null
}

_http_probe_retries() {
    local tries="${1:-3}"
    shift
    local code attempt=0
    while [ "$attempt" -lt "$tries" ]; do
        attempt=$((attempt + 1))
        code=$(_curl_http "$@")
        if [ "$code" = "200" ] || [ "$code" = "304" ]; then
            echo "$code"
            return 0
        fi
        [ "$attempt" -lt "$tries" ] && sleep 2
    done
    echo "${code:-0}"
}

NOW=$(date '+%Y-%m-%d %H:%M UTC')

# P2-MON-01: «порт слушает» ≠ «Xray жив». Контейнер up, но процесс упал — ловим здесь.
remnanode_is_running() {
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'remnanode'
}

xray_core_ok() {
    # Должен выполниться бинарник из образа (remnanode); быстрее и надёжнее поиска PID.
    timeout 10 docker exec remnanode xray version >/dev/null 2>&1
}

# ==========================================
# CHECK 1–2: XRay Latvia — remnanode, xray core, :443 / :8443
# ==========================================
if remnanode_is_running && xray_core_ok; then
    monitor_check_ok "xray_lv_remnanode" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s remnanode + Xray — OK\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_LV" "$NOW")"
    monitor_check_ok "xray_lv_core" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s Xray core — OK\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_LV" "$NOW")"
    if ss -tlnp | grep -q ":443 "; then
        monitor_check_ok "xray_lv_443" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s XRay :443 — back up\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_LV" "$NOW")"
    else
        monitor_check_fail "xray_lv_443" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s XRay :443 — port closed\n🕐 %s\n🖥 176.126.162.158' "$ICON_ALERT" "$ICON_RED" "$FLAG_LV" "$NOW")"
    fi
    if ss -tlnp | grep -q ":8443 "; then
        monitor_check_ok "xray_lv_8443" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s XRay :8443 — back up\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_LV" "$NOW")"
    else
        monitor_check_fail "xray_lv_8443" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s XRay :8443 — port closed\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_LV" "$NOW")"
    fi
elif ! remnanode_is_running; then
    monitor_check_fail "xray_lv_remnanode" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s remnanode — not running\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_LV" "$NOW")"
elif ! xray_core_ok; then
    monitor_check_fail "xray_lv_core" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s Xray core — dead in container\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_LV" "$NOW")"
fi

# ==========================================
# CHECK 3-4: XRay Amsterdam :443 / :8443
# DISABLED 2026-05-14 — P1-ARCH-AMS-DECOM drain phase.
# AMS xray no longer receives traffic (injectHosts trimmed, all hosts hidden,
# probe_users_subs shows AMS=0 for sampled users, ss/docker stats show 0 load).
# Re-enable only if the AMS xray node is re-introduced into the topology.
# ==========================================
# AMS_443=$(ssh -i "$AMS_SSH_KEY" -p "$AMS_SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
#     root@"$AMS_IP" 'ss -tlnp | grep -c ":443 "' 2>/dev/null || echo 0)
# if [ "$AMS_443" -gt 0 ] 2>/dev/null; then
#     recover "xray_ams_443" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 XRay Amsterdam :443 — back up\n🕐 %s' "$NOW")"
# else
#     alert "xray_ams_443" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ XRay Amsterdam :443 — DOWN\n🕐 %s\n🖥 168.100.11.140\n\n🔧 <code>ssh -p 3344 root@168.100.11.140 '\''docker logs remnanode --tail 20'\''</code>' "$NOW")"
# fi
#
# AMS_8443=$(ssh -i "$AMS_SSH_KEY" -p "$AMS_SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
#     root@"$AMS_IP" 'ss -tlnp | grep -c ":8443 "' 2>/dev/null || echo 0)
# if [ "$AMS_8443" -gt 0 ] 2>/dev/null; then
#     recover "xray_ams_8443" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 XRay Amsterdam :8443 — back up\n🕐 %s' "$NOW")"
# else
#     alert "xray_ams_8443" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ XRay Amsterdam :8443 — DOWN\n🕐 %s\n🖥 168.100.11.140' "$NOW")"
# fi

# ==========================================
# CHECK 5: Subscription endpoint
# ==========================================
SUB_STATUS=$(_http_probe_retries 3 "$SUB_MONITOR_PROBE_URL")
if [ "$SUB_STATUS" = "200" ]; then
    monitor_check_ok "subscription" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s Subscription — back up (HTTP 200)\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$NOW")"
else
    monitor_check_fail "subscription" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s Subscription — DOWN (HTTP %s)\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "${SUB_STATUS:-timeout}" "$NOW")"
fi

# CHECK 5b: Alternate subscription origin (P2-RED-SUB-01)
SUB_ALT_STATUS=$(_http_probe_retries 3 "$SUB_ALT_MONITOR_PROBE_URL")
if [ "$SUB_ALT_STATUS" = "200" ]; then
    monitor_check_ok "subscription_alt" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s alt subscription — back up\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_NL" "$NOW")"
else
    monitor_check_fail "subscription_alt" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s alt subscription — DOWN (HTTP %s)\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_NL" "${SUB_ALT_STATUS:-timeout}" "$NOW")"
fi

# ==========================================
# CHECK 6: Selfsteal Latvia
# ==========================================
SELFSTEAL=$(curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 5 \
    --resolve "id.x5.ru:9443:127.0.0.1" https://id.x5.ru:9443 2>/dev/null)
if [ "$SELFSTEAL" = "200" ]; then
    monitor_check_ok "selfsteal_lv" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s Selfsteal — back up\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_LV" "$NOW")"
else
    monitor_check_fail "selfsteal_lv" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s Selfsteal — DOWN (HTTP %s)\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_LV" "${SELFSTEAL:-timeout}" "$NOW")"
fi

# ==========================================
# CHECK 7: Relay tunnel
# ==========================================
if nc -zw5 72.56.0.145 443 2>/dev/null; then
    monitor_check_ok "relay_443" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s Relay :443 — back up\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_RU" "$NOW")"
else
    monitor_check_fail "relay_443" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s Relay :443 — unreachable\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_RU" "$NOW")"
fi

# ==========================================
# CHECK 8: Remnawave panel API
# ==========================================
PANEL_STATUS=$(_http_probe_retries 3 \
    -H "Authorization: Bearer ${PANEL_TOKEN}" \
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \
    "${PANEL_URL}/api/nodes")
if [ "$PANEL_STATUS" = "200" ]; then
    monitor_check_ok "panel" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s Remnawave panel — back up\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_AMS" "$NOW")"
else
    monitor_check_fail "panel" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s Remnawave panel — DOWN (HTTP %s)\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_AMS" "${PANEL_STATUS:-timeout}" "$NOW")"
fi

# ==========================================
# CHECK 9: Disk space Latvia (>90%)
# ==========================================
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 90 ] 2>/dev/null; then
    monitor_check_ok "disk_lv" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s Disk — %s%%\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_LV" "$DISK_USAGE" "$NOW")"
else
    monitor_check_fail "disk_lv" "$(printf '%s <b>BenderVPN WARNING</b>\n\n%s %s Disk — %s%%\n🕐 %s' "$ICON_WARN" "$FLAG_LV" "$DISK_USAGE" "$NOW")"
fi

# ==========================================
# CHECK 10: Bot on Amsterdam
# ==========================================
BOT_RUNNING=$(ssh -i "$AMS_SSH_KEY" -p "$AMS_SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    root@"$AMS_IP" 'docker ps --format "{{.Names}}" | grep -c remna-shop-bot' 2>/dev/null || echo 0)
if [ "$BOT_RUNNING" -gt 0 ] 2>/dev/null; then
    monitor_check_ok "bot" "$(printf '%s <b>BenderVPN RECOVERED</b>\n\n%s %s Telegram bot — back up\n🕐 %s' "$ICON_OK" "$ICON_GREEN" "$FLAG_AMS" "$NOW")"
else
    monitor_check_fail "bot" "$(printf '%s <b>BenderVPN ALERT</b>\n\n%s %s Telegram bot — DOWN\n🕐 %s' "$ICON_ALERT" "$ICON_RED" "$FLAG_AMS" "$NOW")"
fi

log "Monitor check completed"
