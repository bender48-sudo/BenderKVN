#!/bin/bash

# --- P2-BAK / миграция панели на AMS ---
# Канонический путь бэкапа: **AMS** `ops/pg_dump_remnawave.sh` → LV `ops/pull-latest-dump-ams-to-lv.sh`.
# Подробности: **`docs/RUNBOOK-BACKUP-REMNAWAVE.md`**. Этот скрипт — для случая, когда `remnawave-db`
# локально на той же машине, что и cron (исторически LV).

# OPSEC Stage 4 (post-task-2c cleanup): secrets sourced from balancer.env
source /etc/bvpn/balancer.env

# Anti-correlation jitter: random delay 0-600s
sleep $((RANDOM % 600))
set -e

# Config
ADMIN_CHAT_ID="924498094"
BACKUP_DIR="/opt/backups/remnawave"
MAX_BACKUPS=7
DB_CONTAINER="remnawave-db"
DB_USER="postgres"
DB_NAME="postgres"

# Create backup dir
mkdir -p "$BACKUP_DIR"

# Generate filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/remnawave_${TIMESTAMP}.sql.gz"

# Create dump
echo "[$(date)] Starting backup..."
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ ! -s "$BACKUP_FILE" ]; then
    echo "[$(date)] ERROR: Backup file not created or empty"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"         -d "chat_id=${ADMIN_CHAT_ID}"         -d "text=❌ Remnawave DB backup FAILED at $(date)" > /dev/null
    exit 1
fi

FILE_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup created: $BACKUP_FILE ($FILE_SIZE)"

# Success: log only (no Telegram). Set REMNA_BACKUP_NOTIFY=1 to restore TG document on success.
REMNA_BACKUP_NOTIFY="${REMNA_BACKUP_NOTIFY:-0}"
if [ "$REMNA_BACKUP_NOTIFY" = "1" ]; then
    SEND_RESULT=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
        -F "chat_id=${ADMIN_CHAT_ID}" \
        -F "document=@${BACKUP_FILE}" \
        -F "caption=💾 Remnawave DB Backup
📅 Time: $(date '+%Y-%m-%d %H:%M UTC')
📦 Size: ${FILE_SIZE}" \
        -F "parse_mode=HTML")
    if echo "$SEND_RESULT" | grep -q '"ok":true'; then
        echo "[$(date)] Sent to Telegram OK"
    else
        echo "[$(date)] ERROR: Failed to send to Telegram: $SEND_RESULT"
        exit 1
    fi
else
    echo "[$(date)] Telegram notify skipped (REMNA_BACKUP_NOTIFY=0)"
fi

# Keep only last MAX_BACKUPS files
ls -t "$BACKUP_DIR"/remnawave_*.sql.gz 2>/dev/null | tail -n +$((MAX_BACKUPS+1)) | xargs -r rm -f
REMAINING=$(ls "$BACKUP_DIR"/remnawave_*.sql.gz 2>/dev/null | wc -l)
echo "[$(date)] Cleanup done. Keeping $REMAINING backups."

echo "[$(date)] Backup complete!"
