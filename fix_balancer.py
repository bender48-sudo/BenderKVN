# -*- coding: utf-8 -*-
with open('/opt/scripts/balancer.sh') as f:
    content = f.read()

with open('/opt/scripts/balancer.sh.bak', 'w') as f:
    f.write(content)

# Step 2: Update thresholds
replacements = {
    'THRESHOLD_OVERLOAD=500': 'THRESHOLD_OVERLOAD=800',
    'THRESHOLD_NORMAL=350': 'THRESHOLD_NORMAL=600',
    'CPU_THRESHOLD=140  # 1.40 load avg * 100 = ~70% on 2-core': 'CPU_THRESHOLD=175  # 1.75 load avg * 100 = ~87% on 2-core',
}

for old, new in replacements.items():
    if old in content:
        content = content.replace(old, new)
        print(f'Changed: {old} -> {new}')
    else:
        print(f'WARNING: not found: {old}')

# Update comments
content = content.replace(
    '#   connections > 500 AND CPU load avg > 1.4 (70% on 2-core)',
    '#   connections > 800 AND CPU load avg > 1.75 (~87% on 2-core)'
)
content = content.replace(
    '# Recovery when connections < 350',
    '# Recovery when connections < 600'
)
content = content.replace(
    '# OVERLOAD: connections > 500 AND CPU > 1.4',
    '# OVERLOAD: connections > 800 AND CPU > 1.75'
)
content = content.replace(
    '# NORMAL: connections < 350',
    '# NORMAL: connections < 600'
)

# Step 3: Add WARNING block before OVERLOAD
warning_block = '''# ==========================================
# WARNING: approaching limits (notify only, no host changes)
# ==========================================
CPU_WARN=100   # 1.0 load avg * 100 = ~50% on 2-core
WARN_CONNS=600
WARN_STATE="$STATE_DIR/balancer_warning"

if [ "$LV_CONNECTIONS" -gt "$WARN_CONNS" ] || [ "$CPU_LOAD" -gt "$CPU_WARN" ]; then
    if [ ! -f "$WARN_STATE" ]; then
        touch "$WARN_STATE"
        notify "$(printf '\\u26a0\\ufe0f <b>BenderVPN WARNING</b>\\n\\n\\U0001f4c8 Latvia \\u043f\\u0440\\u0438\\u0431\\u043b\\u0438\\u0436\\u0430\\u0435\\u0442\\u0441\\u044f \\u043a \\u043f\\u0440\\u0435\\u0434\\u0435\\u043b\\u0443:\\n\\u2022 \\u0421\\u043e\\u0435\\u0434\\u0438\\u043d\\u0435\\u043d\\u0438\\u0439: <b>%s</b> (\\u043b\\u0438\\u043c\\u0438\\u0442: 800)\\n\\u2022 CPU load: <b>%s</b> (\\u043b\\u0438\\u043c\\u0438\\u0442: 1.75)\\n\\n\\U0001f7e1 \\u0425\\u043e\\u0441\\u0442\\u044b \\u043d\\u0435 \\u043e\\u0442\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u044b \\u2014 \\u043f\\u0440\\u043e\\u0441\\u0442\\u043e \\u043d\\u0430\\u0431\\u043b\\u044e\\u0434\\u0430\\u0435\\u043c\\n\\U0001f550 %s' \\"$LV_CONNECTIONS\\" \\"$CPU_DISPLAY\\" \\"$(date '+%Y-%m-%d %H:%M UTC')\\")"
        log "WARNING: approaching limits (conns=$LV_CONNECTIONS cpu=$CPU_DISPLAY)"
    fi
elif [ -f "$WARN_STATE" ]; then
    rm -f "$WARN_STATE"
    log "WARNING cleared"
fi

'''

marker = '# ==========================================\n# OVERLOAD'
if marker in content:
    content = content.replace(marker, warning_block + marker)
    print('Added: WARNING block before OVERLOAD')
else:
    print('ERROR: OVERLOAD marker not found')

with open('/opt/scripts/balancer.sh', 'w') as f:
    f.write(content)

print('\nDone.')
