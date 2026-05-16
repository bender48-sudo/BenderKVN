with open('/opt/scripts/daily-report.sh', 'r') as f:
    content = f.read()

with open('/opt/scripts/daily-report.sh.bak', 'w') as f:
    f.write(content)

# Replace the STATS python block (user stats section)
old_stats = '''STATS=$(curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \\
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \\
    "${PANEL_URL}/api/users" | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    users=data.get('response',{}).get('users',[]) if isinstance(data,dict) else []
    active = [u for u in users if u.get('status') == 'ACTIVE']
    online = [u for u in users if u.get('onlineAt')]
    total_traffic = sum(u.get('usedTrafficBytes',0) for u in users)
    top_users = sorted(users, key=lambda x: x.get('usedTrafficBytes',0), reverse=True)[:3]
    print('TOTAL:' + str(len(users)))
    print('ACTIVE:' + str(len(active)))
    print('ONLINE:' + str(len(online)))
    print('TRAFFIC:' + str(total_traffic))
    for i,u in enumerate(top_users):
        gb = u.get('usedTrafficBytes',0) / (1024**3)
        name = (u.get('username') or u.get('shortUuid') or 'unknown')[:20]
        print('TOP' + str(i+1) + ':' + name + ':' + format(gb, '.2f') + ' GB')
except Exception as e:
    print('ERROR:' + str(e))
" 2>/dev/null)'''

new_stats = '''STATS=$(curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \\
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \\
    "${PANEL_URL}/api/users" | python3 -c "
import json,sys
from datetime import datetime, timezone
try:
    data=json.load(sys.stdin)
    users=data.get('response',{}).get('users',[]) if isinstance(data,dict) else []
    active = [u for u in users if u.get('status') == 'ACTIVE']
    now = datetime.now(timezone.utc)
    online = []
    for u in users:
        ut = u.get('userTraffic') or {}
        oa = ut.get('onlineAt') or u.get('onlineAt')
        if oa:
            try:
                t = datetime.fromisoformat(oa.replace('Z','+00:00'))
                if (now - t).total_seconds() < 600:
                    online.append(u)
            except: pass
    top_users = sorted(users, key=lambda x: (x.get('userTraffic') or {}).get('lifetimeUsedTrafficBytes', 0), reverse=True)[:3]
    print('TOTAL:' + str(len(users)))
    print('ACTIVE:' + str(len(active)))
    print('ONLINE:' + str(len(online)))
    for i,u in enumerate(top_users):
        ut = u.get('userTraffic') or {}
        gb = ut.get('lifetimeUsedTrafficBytes', 0) / (1024**3)
        name = (u.get('username') or u.get('shortUuid') or 'unknown')[:20]
        print('TOP' + str(i+1) + ':' + name + ':' + format(gb, '.2f') + ' GB')
except Exception as e:
    print('ERROR:' + str(e))
" 2>/dev/null)'''

if old_stats in content:
    content = content.replace(old_stats, new_stats)
    print("FIX 1: Replaced STATS block (online + top users from userTraffic)")
else:
    print("ERROR: STATS block not found")

# Replace TRAFFIC_BYTES parsing — now get from nodes, not users
old_traffic = '''TOTAL=$(echo "$STATS" | grep "^TOTAL:" | cut -d: -f2)
ACTIVE=$(echo "$STATS" | grep "^ACTIVE:" | cut -d: -f2)
ONLINE=$(echo "$STATS" | grep "^ONLINE:" | cut -d: -f2)
TRAFFIC_BYTES=$(echo "$STATS" | grep "^TRAFFIC:" | cut -d: -f2)
TRAFFIC_GB=$(python3 -c "print(f'{${TRAFFIC_BYTES:-0}/1073741824:.2f}')" 2>/dev/null || echo "0")

TOP1=$(echo "$STATS" | grep "^TOP1:" | cut -d: -f2-)
TOP2=$(echo "$STATS" | grep "^TOP2:" | cut -d: -f2-)
TOP3=$(echo "$STATS" | grep "^TOP3:" | cut -d: -f2-)'''

new_traffic = '''TOTAL=$(echo "$STATS" | grep "^TOTAL:" | cut -d: -f2)
ACTIVE=$(echo "$STATS" | grep "^ACTIVE:" | cut -d: -f2)
ONLINE=$(echo "$STATS" | grep "^ONLINE:" | cut -d: -f2)

TOP1=$(echo "$STATS" | grep "^TOP1:" | cut -d: -f2-)
TOP2=$(echo "$STATS" | grep "^TOP2:" | cut -d: -f2-)
TOP3=$(echo "$STATS" | grep "^TOP3:" | cut -d: -f2-)'''

if old_traffic in content:
    content = content.replace(old_traffic, new_traffic)
    print("FIX 2: Removed TRAFFIC from user stats parsing")
else:
    print("ERROR: TRAFFIC parsing block not found")

# Replace NODE_STATS block to also compute total traffic
old_nodes = '''# Get node stats
NODE_STATS=$(curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \\
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \\
    "${PANEL_URL}/api/nodes" | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    nodes=data.get('response',[]) if isinstance(data,dict) else []
    for n in nodes:
        icon = '\\U0001f7e2' if n.get('isConnected') else '\\U0001f534'
        name = n.get('name','?')
        gb = n.get('trafficUsedBytes',0) / (1024**3)
        print(icon + ' ' + name + ': ' + format(gb, '.1f') + ' GB')
except Exception as e:
    print('\\U0001f534 Error: ' + str(e))
" 2>/dev/null)'''

new_nodes = '''# Get node stats and total traffic
NODE_DATA=$(curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \\
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \\
    "${PANEL_URL}/api/nodes" | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    nodes=data.get('response',[]) if isinstance(data,dict) else []
    total = 0
    for n in nodes:
        icon = '\\U0001f7e2' if n.get('isConnected') else '\\U0001f534'
        name = n.get('name','?')
        tb = n.get('trafficUsedBytes',0)
        total += tb
        gb = tb / (1024**3)
        print('NODE:' + icon + ' ' + name + ': ' + format(gb, '.1f') + ' GB')
    print('TOTAL_TRAFFIC:' + format(total / (1024**3), '.2f'))
except Exception as e:
    print('NODE:\\U0001f534 Error: ' + str(e))
    print('TOTAL_TRAFFIC:0')
" 2>/dev/null)

NODE_STATS=$(echo "$NODE_DATA" | grep "^NODE:" | cut -d: -f2-)
TRAFFIC_GB=$(echo "$NODE_DATA" | grep "^TOTAL_TRAFFIC:" | cut -d: -f2)'''

if old_nodes in content:
    content = content.replace(old_nodes, new_nodes)
    print("FIX 3: Replaced NODE_STATS to compute total traffic from nodes")
else:
    print("ERROR: NODE_STATS block not found")
    # Debug: show what's actually there
    import re
    m = re.search(r'# Get node stats.*?2>/dev/null\)', content, re.DOTALL)
    if m:
        print("Found block:", repr(m.group(0)[:200]))

with open('/opt/scripts/daily-report.sh', 'w') as f:
    f.write(content)

print("\nDone. File updated.")
