#!/bin/bash
# BenderVPN Capacity Monitor
# Runs hourly via cron. Alerts when user count approaches node capacity.
# Client-side leastLoad balancer handles traffic distribution.

set -euo pipefail

if [ ! -f /etc/bvpn/balancer.env ]; then
    echo "FATAL: /etc/bvpn/balancer.env not found" >&2
    exit 1
fi
source /etc/bvpn/balancer.env

# Anti-correlation jitter: random delay 0-600s
sleep $((RANDOM % 600))

ADMIN_CHAT_ID="924498094"
# After panel migration off LV, set PANEL_URL in /etc/bvpn/balancer.env (HTTPS, no trailing slash).
PANEL_URL="${PANEL_URL:-http://localhost:3000}"
STATE_DIR="/tmp/bvpn_states"
LOG_FILE="/var/log/bvpn-balancer.log"
USERS_PER_NODE=50

mkdir -p "$STATE_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

notify() {
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ADMIN_CHAT_ID}" \
        -d "parse_mode=HTML" \
        --data-urlencode "text=$1" > /dev/null 2>&1
}

sent_today() {
    [ -f "${STATE_DIR}/${1}_$(date +%Y-%m-%d)" ]
}

mark_sent() {
    touch "${STATE_DIR}/${1}_$(date +%Y-%m-%d)"
}

api() {
    curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \
        -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \
        "${PANEL_URL}${1}" 2>/dev/null
}

get_users_count() {
    api "/api/users" | python3 -c "
import json,sys
d=json.load(sys.stdin)
users=d.get('response',{}).get('users',[])
active=[u for u in users if u.get('status')=='ACTIVE']
print(len(active))
" 2>/dev/null || echo "0"
}

get_nodes_count() {
    api "/api/nodes" | python3 -c "
import json,sys
d=json.load(sys.stdin)
nodes=d.get('response',d)
if isinstance(nodes,list): items=nodes
else: items=nodes.get('nodes',nodes.get('items',[]))
active=[n for n in items if not n.get('isDisabled',False)]
print(len(active))
" 2>/dev/null || echo "0"
}

get_latvia_cpu() {
    awk '{printf "%.2f", $1}' /proc/loadavg
}

get_amsterdam_cpu() {
    ssh -i /root/.ssh/id_ed25519 -p 3344 -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
        root@168.100.11.140 'awk "{printf \"%.2f\", \$1}" /proc/loadavg' 2>/dev/null || echo "N/A"
}

# Cleanup state files older than 7 days
find "$STATE_DIR" -type f -mtime +7 -delete 2>/dev/null || true

# Gather metrics
USERS=$(get_users_count)
NODES=$(get_nodes_count)
CAPACITY=$((NODES * USERS_PER_NODE))
if [ "$CAPACITY" -gt 0 ]; then
    LOAD_PCT=$((USERS * 100 / CAPACITY))
else
    LOAD_PCT=0
fi
PER_NODE=$((NODES > 0 ? USERS / NODES : USERS))

LV_CPU=$(get_latvia_cpu)
AMS_CPU=$(get_amsterdam_cpu)

LV_CPU_INT=$(echo "$LV_CPU" | awk '{printf "%d", $1 * 100}')
AMS_CPU_INT=$(echo "$AMS_CPU" | awk '{printf "%d", $1 * 100}' 2>/dev/null || echo "0")

NOW=$(date '+%Y-%m-%d %H:%M UTC')

log "USERS=$USERS NODES=$NODES CAP=${LOAD_PCT}% LV_CPU=$LV_CPU AMS_CPU=$AMS_CPU"

# === Capacity alerts ===
if [ "$LOAD_PCT" -ge 100 ]; then
    if ! sent_today capacity_critical; then
        MSG=$(printf '🔴 <b>BenderVPN CRITICAL</b>\n\n📊 Нагрузка: <b>%s/%s пользователей (%s%%)</b>\n🖥 Нод: %s\n📈 На ноду: ~%s пользователей\n\n🔴 <b>CRITICAL</b>: Capacity 100%%+ — система на пределе!\nДобавлять ноду СЕЙЧАС.\n\n🔧 Действия:\n- Провайдер: doubleservers.com\n- Скрипт: /opt/scripts/deploy-node.sh\n\n🕐 %s' "$USERS" "$CAPACITY" "$LOAD_PCT" "$NODES" "$PER_NODE" "$NOW")
        notify "$MSG"
        mark_sent capacity_critical
        log "ALERT: capacity CRITICAL ${LOAD_PCT}%"
    fi
elif [ "$LOAD_PCT" -ge 95 ]; then
    if ! sent_today capacity_alert; then
        MSG=$(printf '🟠 <b>BenderVPN ALERT</b>\n\n📊 Нагрузка: <b>%s/%s пользователей (%s%%)</b>\n🖥 Нод: %s\n📈 На ноду: ~%s пользователей\n\n🟠 <b>ALERT</b>: Capacity 95%%+ достигнут.\nЗакупай ноду срочно.\n\n🔧 Действия:\n- Провайдер: doubleservers.com\n- Скрипт: /opt/scripts/deploy-node.sh\n\n🕐 %s' "$USERS" "$CAPACITY" "$LOAD_PCT" "$NODES" "$PER_NODE" "$NOW")
        notify "$MSG"
        mark_sent capacity_alert
        log "ALERT: capacity ALERT ${LOAD_PCT}%"
    fi
elif [ "$LOAD_PCT" -ge 80 ]; then
    if ! sent_today capacity_warn; then
        MSG=$(printf '⚠️ <b>BenderVPN Capacity</b>\n\n📊 Нагрузка: <b>%s/%s пользователей (%s%%)</b>\n🖥 Нод: %s\n📈 На ноду: ~%s пользователей\n\n🟡 <b>WARN</b>: Capacity 80%%+ достигнут.\nРекомендуется начать разворачивание %s-й ноды.\n\n🔧 Действия:\n- Провайдер: doubleservers.com\n- Скрипт: /opt/scripts/deploy-node.sh\n- После деплоя capacity пересчитается автоматически\n\n🕐 %s' "$USERS" "$CAPACITY" "$LOAD_PCT" "$NODES" "$PER_NODE" "$((NODES + 1))" "$NOW")
        notify "$MSG"
        mark_sent capacity_warn
        log "ALERT: capacity WARN ${LOAD_PCT}%"
    fi
fi

# === CPU alerts ===
CPU_MAX=$LV_CPU_INT
[ "$AMS_CPU_INT" -gt "$CPU_MAX" ] 2>/dev/null && CPU_MAX=$AMS_CPU_INT

if [ "$CPU_MAX" -ge 200 ]; then
    if ! sent_today cpu_critical; then
        MSG=$(printf '🔴 <b>BenderVPN CPU CRITICAL</b>\n\n🇱🇻 Latvia: <b>%s</b>\n🇳🇱 Amsterdam: <b>%s</b>\n\nCPU load >2.0 — возможна деградация.\n\n🕐 %s' "$LV_CPU" "$AMS_CPU" "$NOW")
        notify "$MSG"
        mark_sent cpu_critical
        log "ALERT: CPU CRITICAL max=$CPU_MAX"
    fi
elif [ "$CPU_MAX" -ge 150 ]; then
    if ! sent_today cpu_warn; then
        MSG=$(printf '⚠️ <b>BenderVPN CPU Warning</b>\n\n🇱🇻 Latvia: <b>%s</b>\n🇳🇱 Amsterdam: <b>%s</b>\n\nCPU load >1.5 — наблюдаем.\n\n🕐 %s' "$LV_CPU" "$AMS_CPU" "$NOW")
        notify "$MSG"
        mark_sent cpu_warn
        log "ALERT: CPU WARN max=$CPU_MAX"
    fi
fi

# === Daily summary at 09:XX UTC ===
HOUR=$(date +%H)
if [ "$HOUR" = "09" ] && ! sent_today summary; then
    if [ "$LOAD_PCT" -ge 80 ]; then
        STATUS="🟡 Внимание — capacity ${LOAD_PCT}%"
    else
        STATUS="✅ Всё в норме"
    fi

    MSG=$(printf '📊 <b>BenderVPN Daily Summary</b>\n\n👥 Пользователи: <b>%s/%s</b> (%s%%)\n🖥 Нод: %s\n- 🇱🇻 Latvia: CPU load %s\n- 🇳🇱 Amsterdam: CPU load %s\n\n%s\n\n🕐 %s' "$USERS" "$CAPACITY" "$LOAD_PCT" "$NODES" "$LV_CPU" "$AMS_CPU" "$STATUS" "$NOW")
    notify "$MSG"
    mark_sent summary
    log "Daily summary sent"
fi
