# -*- coding: utf-8 -*-
with open('/opt/scripts/daily-report.sh', 'r') as f:
    content = f.read()

old = """# Get node stats
NODE_STATS=$(curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \\
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \\
    "${PANEL_URL}/api/nodes" | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    nodes=data.get('response',[]) if isinstance(data,dict) else []
    for n in nodes:
        icon = '\U0001f7e2' if n.get('isConnected') else '\U0001f534'
        name = n.get('name','?')
        gb = n.get('trafficUsedBytes',0) / (1024**3)
        print(icon + ' ' + name + ': ' + format(gb, '.1f') + ' GB')
except Exception as e:
    print('\U0001f534 Error: ' + str(e))
" 2>/dev/null)"""

new = """# Get node stats and total traffic
NODE_DATA=$(curl -s -H "Authorization: Bearer ${PANEL_TOKEN}" \\
    -H "X-Forwarded-Proto: https" -H "X-Forwarded-For: 127.0.0.1" \\
    "${PANEL_URL}/api/nodes" | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    nodes=data.get('response',[]) if isinstance(data,dict) else []
    total = 0
    for n in nodes:
        icon = '\U0001f7e2' if n.get('isConnected') else '\U0001f534'
        name = n.get('name','?')
        tb = n.get('trafficUsedBytes',0)
        total += tb
        gb = tb / (1024**3)
        print('NODE:' + icon + ' ' + name + ': ' + format(gb, '.1f') + ' GB')
    print('TOTAL_TRAFFIC:' + format(total / (1024**3), '.2f'))
except Exception as e:
    print('NODE:\U0001f534 Error: ' + str(e))
    print('TOTAL_TRAFFIC:0')
" 2>/dev/null)

NODE_STATS=$(echo "$NODE_DATA" | grep "^NODE:" | sed 's/^NODE://')
TRAFFIC_GB=$(echo "$NODE_DATA" | grep "^TOTAL_TRAFFIC:" | cut -d: -f2)"""

if old in content:
    content = content.replace(old, new)
    with open('/opt/scripts/daily-report.sh', 'w') as f:
        f.write(content)
    print("FIX 3: NODE_STATS replaced to compute total traffic from nodes")
else:
    print("ERROR: block not found")
    # Show what lines 58-74 look like as repr
    lines = content.split('\n')
    for i in range(57, min(74, len(lines))):
        print(f"  {i+1}: {repr(lines[i])}")
