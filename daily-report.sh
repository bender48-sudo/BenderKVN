#!/bin/bash

# OPSEC Stage 4 (post-task-2c cleanup): secrets sourced from balancer.env
source /etc/bvpn/balancer.env

# Optional overrides (fallbacks match ops/site.env.example); see docs/DEPLOY.md
SUB_PUBLIC_ORIGIN="${SUB_PUBLIC_ORIGIN:-https://p4n7q.conntest.xyz:2053}"
export SUB_PUBLIC_ORIGIN
SUB_MONITOR_PROBE_URL="${SUB_MONITOR_PROBE_URL:-${SUB_PUBLIC_ORIGIN}/api/sub/JLCF43RGjyq4ML78Qcsbq7Kf2}"

# Anti-correlation jitter: random delay 0-600s
sleep $((RANDOM % 600))

# ==========================================
# BenderVPN Daily Report
# Runs at 09:00 UTC via cron
# ==========================================

ADMIN_CHAT_ID="924498094"
# Remnawave API на AMS (HTTPS). На LV локального :3000 после миграции панели нет.
PANEL_URL="${PANEL_URL:-https://k9x2m1.conntest.xyz:2053}"
AMS_IP="168.100.11.140"
AMS_SSH_PORT="3344"
AMS_SSH_KEY="/root/.ssh/id_ed25519"

# User stats: /api/users без size/start отдаёт только первую страницу (~25) — см. grandfather_panel_users_expire.py
STATS=$(PANEL_URL="$PANEL_URL" PANEL_TOKEN="$PANEL_TOKEN" python3 <<'PY'
import json, os, ssl, urllib.error, urllib.request
from datetime import datetime, timezone

def fetch_all_users():
    base = os.environ["PANEL_URL"].rstrip("/")
    token = os.environ["PANEL_TOKEN"]
    ctx = ssl.create_default_context()
    out = []
    seen = set()
    start = 0
    size = 100
    while True:
        url = f"{base}/api/users?size={size}&start={start}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-For": "127.0.0.1",
            },
        )
        with urllib.request.urlopen(req, context=ctx, timeout=90) as resp:
            data = json.load(resp)
        chunk = (data.get("response") or {}).get("users") or []
        if not isinstance(chunk, list):
            chunk = []
        n_new = 0
        for u in chunk:
            uid = u.get("uuid") or u.get("shortUuid") or u.get("email")
            if uid:
                if uid in seen:
                    continue
                seen.add(uid)
            out.append(u)
            n_new += 1
        if len(chunk) < size:
            break
        if n_new == 0:
            break
        start += len(chunk)
        if start > 100000:
            break
    return out

try:
    users = fetch_all_users()
    active = [u for u in users if u.get("status") == "ACTIVE"]
    now = datetime.now(timezone.utc)
    online = []
    for u in users:
        ut = u.get("userTraffic") or {}
        oa = ut.get("onlineAt") or u.get("onlineAt")
        if oa:
            try:
                t = datetime.fromisoformat(str(oa).replace("Z", "+00:00"))
                if (now - t).total_seconds() < 600:
                    online.append(u)
            except Exception:
                pass
    top_users = sorted(
        users,
        key=lambda x: (x.get("userTraffic") or {}).get("lifetimeUsedTrafficBytes", 0),
        reverse=True,
    )[:3]
    print("TOTAL:" + str(len(users)))
    print("ACTIVE:" + str(len(active)))
    print("ONLINE:" + str(len(online)))
    for i, u in enumerate(top_users):
        ut = u.get("userTraffic") or {}
        gb = ut.get("lifetimeUsedTrafficBytes", 0) / (1024**3)
        name = (u.get("username") or u.get("shortUuid") or "unknown")[:20]
        print("TOP" + str(i + 1) + ":" + name + ":" + format(gb, ".2f") + " GB")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:400]
    print("ERROR:HTTP " + str(e.code) + " " + body)
except Exception as e:
    print("ERROR:" + str(e))
PY
)

TOTAL=$(echo "$STATS" | grep "^TOTAL:" | cut -d: -f2)
ACTIVE=$(echo "$STATS" | grep "^ACTIVE:" | cut -d: -f2)
ONLINE=$(echo "$STATS" | grep "^ONLINE:" | cut -d: -f2)

TOP1=$(echo "$STATS" | grep "^TOP1:" | cut -d: -f2-)
TOP2=$(echo "$STATS" | grep "^TOP2:" | cut -d: -f2-)
TOP3=$(echo "$STATS" | grep "^TOP3:" | cut -d: -f2-)

# Get node stats and total traffic
NODE_DATA=$(curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \
    "${PANEL_URL}/api/nodes" | python3 -c "
import json,sys
# Decommissioning whitelist: these nodes are expected to be disconnected
# (e.g. during P1-ARCH-AMS-DECOM drain). Don't paint them red.
DECOM = {'Amsterdam-01'}
try:
    data=json.load(sys.stdin)
    nodes=data.get('response',[]) if isinstance(data,dict) else []
    total = 0
    for n in nodes:
        name = n.get('name','?')
        is_conn = n.get('isConnected')
        if name in DECOM:
            icon = '🟡'
            suffix = ' (decom)'
        elif is_conn:
            icon = '🟢'
            suffix = ''
        else:
            icon = '🔴'
            suffix = ''
        tb = n.get('trafficUsedBytes',0)
        total += tb
        gb = tb / (1024**3)
        print('NODE:' + icon + ' ' + name + suffix + ': ' + format(gb, '.1f') + ' GB')
    print('TOTAL_TRAFFIC:' + format(total / (1024**3), '.2f'))
except Exception as e:
    print('NODE:🔴 Error: ' + str(e))
    print('TOTAL_TRAFFIC:0')
" 2>/dev/null)

NODE_STATS=$(echo "$NODE_DATA" | grep "^NODE:" | sed 's/^NODE://')
TRAFFIC_GB=$(echo "$NODE_DATA" | grep "^TOTAL_TRAFFIC:" | cut -d: -f2)

# Disk usage
DISK_LV=$(df / | awk 'NR==2 {print $5}')
DISK_AMS=$(ssh -i "$AMS_SSH_KEY" -p "$AMS_SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    root@"$AMS_IP" "df / | awk 'NR==2 {print \$5}'" 2>/dev/null || echo "N/A")

# Last backup info
LAST_BACKUP=$(ls -t /opt/backups/remnawave/*.sql.gz 2>/dev/null | head -1)
if [ -n "$LAST_BACKUP" ]; then
    LAST_BACKUP_TIME=$(stat -c %y "$LAST_BACKUP" 2>/dev/null | cut -d. -f1)
    LAST_BACKUP_SIZE=$(du -sh "$LAST_BACKUP" 2>/dev/null | cut -f1)
else
    LAST_BACKUP_TIME="no backups"
    LAST_BACKUP_SIZE="0"
fi

# Active alerts
ALERT_COUNT=$(ls /var/lib/bvpn-monitor/alert_* /tmp/bvpn_states/alert_* 2>/dev/null | wc -l)
if [ "$ALERT_COUNT" -gt 0 ]; then
    ALERT_LIST=$(ls /var/lib/bvpn-monitor/alert_* /tmp/bvpn_states/alert_* 2>/dev/null | xargs -I{} basename {} | sort -u | sed 's/alert_/⚠️ /g' | tr '\n' ', ' | sed 's/,$//')
    ALERT_LINE="🔴 Active alerts ($ALERT_COUNT): $ALERT_LIST"
else
    ALERT_LINE="🟢 No active alerts"
fi

# Service checks
AMS_TOUCH_USERS="n/a"
if [ -f /opt/scripts/count_users_with_ams_sub.py ]; then
    _ams_raw="$(
        PANEL_URL="${PANEL_URL}" PANEL_TOKEN="${PANEL_TOKEN}" REMNA_API_TOKEN="${REMNA_API_TOKEN}" \
            SUB_PUBLIC_ORIGIN="${SUB_PUBLIC_ORIGIN}" RU_RELAY_HOST="${RU_RELAY_HOST:-}" \
            python3 /opt/scripts/count_users_with_ams_sub.py --brief 2>/dev/null || true
    )"
    case "${_ams_raw}" in
        '' | *[!0-9]*) AMS_TOUCH_USERS="n/a" ;;
        *) AMS_TOUCH_USERS="${_ams_raw}" ;;
    esac
    unset _ams_raw
fi

SUB_OK=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 \
    "${SUB_MONITOR_PROBE_URL}" 2>/dev/null)
RELAY_OK="❌"
nc -zw3 72.56.0.145 443 2>/dev/null && RELAY_OK="✅"

MESSAGE="$(cat <<MSGEOF
📊 <b>BenderVPN — Daily Report</b>
📅 $(date '+%Y-%m-%d %H:%M UTC')

👥 <b>Users:</b>
• Total: ${TOTAL:-0}
• Active: ${ACTIVE:-0}
• Online now: ${ONLINE:-0}
• ACTIVE with AMS outbound in Happ sub (probe): ${AMS_TOUCH_USERS}

📈 <b>Total traffic:</b> ${TRAFFIC_GB} GB

🏆 <b>Top users:</b>
${TOP1:+• $TOP1}
${TOP2:+• $TOP2}
${TOP3:+• $TOP3}

🖥 <b>Nodes:</b>
${NODE_STATS}

🌐 <b>Services:</b>
• Subscription: $([ "$SUB_OK" = "200" ] && echo "✅" || echo "❌ HTTP $SUB_OK")
• Relay RU: ${RELAY_OK}

💾 <b>Disk:</b>
• Latvia: ${DISK_LV}
• Amsterdam: ${DISK_AMS}

🗄 <b>Last backup:</b>
• ${LAST_BACKUP_TIME} (${LAST_BACKUP_SIZE})

${ALERT_LINE}
MSGEOF
)"

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d "chat_id=${ADMIN_CHAT_ID}" \
    -d "parse_mode=HTML" \
    --data-urlencode "text=${MESSAGE}" > /dev/null 2>&1

echo "[$(date)] Daily report sent" >> /var/log/bvpn-monitor.log
