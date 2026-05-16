#!/bin/bash

# OPSEC Stage 4: secrets sourced from balancer.env (was hardcoded before)
source /etc/bvpn/balancer.env

# Public subscription smoke URL (aligned with daily-report.sh; overrides via balancer.env OK)
SUB_PUBLIC_ORIGIN="${SUB_PUBLIC_ORIGIN:-https://p4n7q.conntest.xyz:2053}"
export SUB_PUBLIC_ORIGIN
SUB_MONITOR_PROBE_URL="${SUB_MONITOR_PROBE_URL:-${SUB_PUBLIC_ORIGIN}/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"
SUB_ALT_PUBLIC_ORIGIN="${SUB_ALT_PUBLIC_ORIGIN:-https://k9x2m1.conntest.xyz:2053}"
SUB_ALT_MONITOR_PROBE_URL="${SUB_ALT_MONITOR_PROBE_URL:-${SUB_ALT_PUBLIC_ORIGIN}/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"

# After P0 migrations panel lives on AMS; balancer.env MUST set this (fallback matches tmpl)
PANEL_URL="${PANEL_URL:-https://k9x2m1.conntest.xyz:2053}"

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

alert() {
    local check_name="$1"
    local message="$2"
    local state_file="$STATE_DIR/alert_${check_name}"

    if [ ! -f "$state_file" ]; then
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ADMIN_CHAT_ID}" \
            -d "parse_mode=HTML" \
            --data-urlencode "text=${message}" > /dev/null 2>&1
        touch "$state_file"
        log "ALERT sent: $check_name"
    fi
}

recover() {
    local check_name="$1"
    local message="$2"
    local state_file="$STATE_DIR/alert_${check_name}"

    if [ -f "$state_file" ]; then
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ADMIN_CHAT_ID}" \
            -d "parse_mode=HTML" \
            --data-urlencode "text=${message}" > /dev/null 2>&1
        rm -f "$state_file"
        log "RECOVERED: $check_name"
    fi
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
    recover "xray_lv_remnanode" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 remnanode container + Xray core — OK\n🕐 %s' "$NOW")"
    recover "xray_lv_core" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Xray process/binary — OK\n🕐 %s' "$NOW")"
    if ss -tlnp | grep -q ":443 "; then
        recover "xray_lv_443" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 XRay Latvia :443 — back up\n🕐 %s' "$NOW")"
    else
        alert "xray_lv_443" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ XRay Latvia :443 — port closed (core OK)\n🕐 %s\n🖥 176.126.162.158\n\n🔧 <code>docker logs remnanode --tail 50</code>' "$NOW")"
    fi
    if ss -tlnp | grep -q ":8443 "; then
        recover "xray_lv_8443" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 XRay Latvia :8443 — back up\n🕐 %s' "$NOW")"
    else
        alert "xray_lv_8443" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ XRay Latvia :8443 — port closed (core OK)\n🕐 %s\n🖥 176.126.162.158' "$NOW")"
    fi
elif ! remnanode_is_running; then
    alert "xray_lv_remnanode" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ remnanode — container not running\n🕐 %s\n🖥 176.126.162.158\n\n🔧 <code>cd /opt/remnanode && docker compose ps && docker compose up -d</code>' "$NOW")"
elif ! xray_core_ok; then
    alert "xray_lv_core" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ Xray core — dead inside remnanode (ports may still listen)\n🕐 %s\n🖥 176.126.162.158\n\n🔧 <code>docker logs remnanode --tail 50</code>' "$NOW")"
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
SUB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 \
    "$SUB_MONITOR_PROBE_URL" 2>/dev/null)
if [ "$SUB_STATUS" = "200" ]; then
    recover "subscription" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Subscription endpoint — back up (HTTP 200)\n🕐 %s' "$NOW")"
else
    alert "subscription" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ Subscription endpoint — DOWN (HTTP %s)\n🕐 %s\n🌐 %s\n🔗 <code>%s</code>\n\n🔧 <code>systemctl status caddy</code>' "${SUB_STATUS:-timeout}" "$NOW" "${SUB_PUBLIC_ORIGIN}" "${SUB_MONITOR_PROBE_URL}")"
fi

# CHECK 5b: Alternate subscription origin (P2-RED-SUB-01)
SUB_ALT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 \
    "$SUB_ALT_MONITOR_PROBE_URL" 2>/dev/null)
if [ "$SUB_ALT_STATUS" = "200" ]; then
    recover "subscription_alt" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Subscription alt origin — back up (HTTP 200)\n🕐 %s\n🌐 %s' "$NOW" "${SUB_ALT_PUBLIC_ORIGIN}")"
else
    alert "subscription_alt" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ Subscription alt origin — DOWN (HTTP %s)\n🕐 %s\n🌐 %s\n🔗 <code>%s</code>' "${SUB_ALT_STATUS:-timeout}" "$NOW" "${SUB_ALT_PUBLIC_ORIGIN}" "${SUB_ALT_MONITOR_PROBE_URL}")"
fi

# ==========================================
# CHECK 6: Selfsteal Latvia
# ==========================================
SELFSTEAL=$(curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 5 \
    --resolve "id.x5.ru:9443:127.0.0.1" https://id.x5.ru:9443 2>/dev/null)
if [ "$SELFSTEAL" = "200" ]; then
    recover "selfsteal_lv" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Selfsteal Latvia — back up\n🕐 %s' "$NOW")"
else
    alert "selfsteal_lv" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ Selfsteal Latvia — DOWN (HTTP %s)\n🕐 %s\n\n🔧 <code>systemctl status caddy</code>' "${SELFSTEAL:-timeout}" "$NOW")"
fi

# ==========================================
# CHECK 7: Relay tunnel
# ==========================================
if nc -zw5 72.56.0.145 443 2>/dev/null; then
    recover "relay_443" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Relay RU :443 — back up\n🕐 %s' "$NOW")"
else
    alert "relay_443" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ Relay RU :443 — unreachable\n🕐 %s\n🖥 72.56.0.145' "$NOW")"
fi

# ==========================================
# CHECK 8: Remnawave panel API
# ==========================================
PANEL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 \
    -H "Authorization: Bearer ${PANEL_TOKEN}" \
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \
    "${PANEL_URL}/api/nodes" 2>/dev/null)
if [ "$PANEL_STATUS" = "200" ]; then
    recover "panel" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Remnawave panel — back up\n🕐 %s' "$NOW")"
else
    alert "panel" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ Remnawave panel — DOWN (HTTP %s)\n🕐 %s\n\n🔧 <code>docker ps | grep remnawave</code>' "${PANEL_STATUS:-timeout}" "$NOW")"
fi

# ==========================================
# CHECK 9: Disk space Latvia (>90%)
# ==========================================
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 90 ] 2>/dev/null; then
    recover "disk_lv" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Disk Latvia — freed up (%s%%)\n🕐 %s' "$DISK_USAGE" "$NOW")"
else
    alert "disk_lv" "$(printf '⚠️ <b>BenderVPN WARNING</b>\n\n💾 Disk Latvia at %s%%\n🕐 %s\n\n🔧 <code>df -h && du -sh /opt/* | sort -rh | head</code>' "$DISK_USAGE" "$NOW")"
fi

# ==========================================
# CHECK 10: Bot on Amsterdam
# ==========================================
BOT_RUNNING=$(ssh -i "$AMS_SSH_KEY" -p "$AMS_SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    root@"$AMS_IP" 'docker ps --format "{{.Names}}" | grep -c remna-shop-bot' 2>/dev/null || echo 0)
if [ "$BOT_RUNNING" -gt 0 ] 2>/dev/null; then
    recover "bot" "$(printf '✅ <b>BenderVPN RECOVERED</b>\n\n🟢 Telegram bot — back up\n🕐 %s' "$NOW")"
else
    alert "bot" "$(printf '🚨 <b>BenderVPN ALERT</b>\n\n❌ Telegram bot — DOWN\n🕐 %s\n\n🔧 <code>cd /opt/remna-shop && docker compose up -d</code>' "$NOW")"
fi

log "Monitor check completed"
