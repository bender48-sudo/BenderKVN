#!/bin/bash
# Security fix v3: skip logging /api/sub/* URIs + fix .env permissions
# Caddy uses admin off so reload via API fails; we use restart instead.
# Run on bvpn-lv as root

set -e

CF=/etc/caddy/Caddyfile
BK=/etc/caddy/Caddyfile.bak-20260511-security

echo "[0] Restore clean backup"
cp "$BK" "$CF"
echo "  Restored OK"

python3 << 'PYEOF'
with open('/etc/caddy/Caddyfile', 'r') as f:
    content = f.read()

old_log_block = """    log {
        output file /var/log/caddy/sub-access.log
        format json
    }"""

new_log_block = """    @sub_path path /api/sub/*
    log_skip @sub_path

    log {
        output file /var/log/caddy/sub-access.log {
            roll_size 10mb
            roll_keep 3
        }
        format json
    }"""

if old_log_block in content:
    content = content.replace(old_log_block, new_log_block)
    with open('/etc/caddy/Caddyfile', 'w') as f:
        f.write(content)
    print("OK: log_skip /api/sub/* added")
else:
    print("ERROR: expected log block not found in Caddyfile")
    import sys; sys.exit(1)
PYEOF

echo "[1] Validate syntax"
caddy validate --config "$CF" 2>&1 | grep -E "Valid|Error|error" || true
echo "  Syntax check done"

echo "[2] Restart Caddy (brief interruption ~1s)"
systemctl restart caddy
sleep 2
systemctl is-active caddy && echo "  Caddy active OK" || {
    echo "  FAIL - restoring backup and restarting"
    cp "$BK" "$CF"
    systemctl restart caddy
    echo "  Rollback done - original config restored"
    exit 1
}

echo "[3] Fix .env permissions (644 -> 600)"
paths=(/opt/remnanode/.env)
if [ -f /opt/remnawave/.env ]; then paths+=(/opt/remnawave/.env); fi
shopt -s nullglob
for d in /opt/_archive/remnawave-legacy-*/; do
  [ -f "${d}.env" ] && paths+=("${d}.env")
done
shopt -u nullglob
for p in "${paths[@]}"; do
  chmod 600 "$p" && echo "  $p -> 600"
done
ls -la "${paths[@]}" 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Sub tokens no longer logged. Verify:"
echo "  tail -5 /var/log/caddy/sub-access.log"
