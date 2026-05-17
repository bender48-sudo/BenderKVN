#!/bin/bash
# One-time: migrate Postgres docker volume to LUKS2 bind mount. Run on AMS during maintenance.
set -eu
CONFIRM="${CONFIRM:-}"
IMG=/opt/remnawave/postgres.luks.img
MAP=remnawave-pg
MNT=/mnt/remnawave-pgdata
OLD=/var/lib/docker/volumes/remnawave_remnawave-db-data/_data
COMPOSE=/opt/remnawave/docker-compose.yml
SIZE_GB=2

if [ "$CONFIRM" != "yes" ]; then
  echo "Set CONFIRM=yes to run (stops panel DB)." >&2
  exit 1
fi
if [ ! -f "$COMPOSE" ]; then
  echo "missing $COMPOSE" >&2
  exit 1
fi
if [ -z "${LUKS_PASS:-}" ]; then
  read -r -s LUKS_PASS
  echo
  read -r -s LUKS_PASS2
  echo
  [ "$LUKS_PASS" = "$LUKS_PASS2" ] || { echo "passphrase mismatch" >&2; exit 1; }
  unset LUKS_PASS2
fi

command -v cryptsetup >/dev/null
command -v rsync >/dev/null

echo "[1/7] stop stack..."
cd /opt/remnawave
docker compose stop remnawave remnawave-db 2>/dev/null || docker compose stop remnawave remnawave-db

if [ ! -f "$IMG" ]; then
  echo "[2/7] create ${SIZE_GB}G LUKS image..."
  mkdir -p /opt/remnawave
  fallocate -l "${SIZE_GB}G" "$IMG"
  chmod 600 "$IMG"
  printf '%s' "$LUKS_PASS" | cryptsetup luksFormat "$IMG" --type luks2 -
fi

if [ ! -e "/dev/mapper/$MAP" ]; then
  printf '%s' "$LUKS_PASS" | cryptsetup open "$IMG" "$MAP" -
fi
unset LUKS_PASS LUKS_PASS2

if ! blkid "/dev/mapper/$MAP" | grep -q ext4; then
  echo "[3/7] mkfs.ext4 on mapper..."
  mkfs.ext4 -L remnawave-pgdata "/dev/mapper/$MAP"
fi

mkdir -p "$MNT"
if ! mountpoint -q "$MNT"; then
  mount "/dev/mapper/$MAP" "$MNT"
fi

echo "[4/7] rsync data..."
if [ -d "$OLD" ]; then
  rsync -aHAX --delete "$OLD/" "$MNT/"
else
  echo "WARN: no old data at $OLD"
fi
chown -R 999:999 "$MNT" 2>/dev/null || chown -R 70:70 "$MNT" 2>/dev/null || true

echo "[5/7] patch compose bind mount..."
cp -a "$COMPOSE" "${COMPOSE}.before-luks-$(date +%Y%m%d%H%M)"
python3 - <<'PY'
from pathlib import Path
p = Path("/opt/remnawave/docker-compose.yml")
text = p.read_text()
old = "            - remnawave-db-data:/var/lib/postgresql/data"
new = "            - /mnt/remnawave-pgdata:/var/lib/postgresql/data"
if old not in text and new not in text:
    raise SystemExit("compose volume line not found")
if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("patched bind mount")
else:
    print("already bind mount")
PY

echo "[6/7] start db + panel..."
docker compose up -d remnawave-db
sleep 5
docker compose up -d remnawave

echo "[7/7] probe..."
python3 /opt/scripts/ams_postgres_crypt_probe.py

echo "DONE: save LUKS passphrase to Bitwarden BenderVPN/ams/postgres-luks-key (not on this host)."
