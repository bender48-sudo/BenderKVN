#!/bin/bash
# Unlock LUKS Postgres volume on AMS. Passphrase via LUKS_PASS env or stdin (not on disk).
set -eu
IMG=/opt/remnawave/postgres.luks.img
MAP=remnawave-pg
MNT=/mnt/remnawave-pgdata

if [ ! -f "$IMG" ]; then
  echo "missing $IMG" >&2
  exit 1
fi
if [ -e "/dev/mapper/$MAP" ]; then
  echo "already open: /dev/mapper/$MAP"
else
  if [ -z "${LUKS_PASS:-}" ]; then
    read -r -s LUKS_PASS
    echo
  fi
  printf '%s' "$LUKS_PASS" | cryptsetup open "$IMG" "$MAP" --
  unset LUKS_PASS
fi
mkdir -p "$MNT"
if ! mountpoint -q "$MNT"; then
  mount "/dev/mapper/$MAP" "$MNT"
fi
echo "OK: $MNT mounted"
