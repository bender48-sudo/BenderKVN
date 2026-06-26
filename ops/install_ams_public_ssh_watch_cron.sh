#!/usr/bin/env bash
# Install AMS private ops SSH recovery watch on bvpn-lv (every 5 min).
set -euo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${LV_OPS_DIR:-/opt/scripts}"

for f in ams_ops_env.sh watch_ams_public_ssh_recovery.sh pull-latest-dump-ams-to-lv.sh push_sub_config_generation_ams.py; do
  src="${OPS}/${f}"
  dst="${TARGET}/${f}"
  if [[ ! -f "$src" ]]; then
    echo "missing repo file: $src" >&2
    exit 1
  fi
  if [[ "$f" == *.sh && "$f" != "ams_ops_env.sh" ]]; then
    mode=755
  else
    mode=644
  fi
  if [[ "$(readlink -f "$src" 2>/dev/null || echo "$src")" != "$(readlink -f "$dst" 2>/dev/null || echo "$dst")" ]]; then
    install -m "$mode" "$src" "$dst"
  else
    chmod "$mode" "$dst" 2>/dev/null || true
  fi
done

mkdir -p /var/lib/bvpn
touch /var/log/bvpn-ams-public-ssh-watch.log
chmod 644 /var/log/bvpn-ams-public-ssh-watch.log

MARK="# bvpn-ams-public-ssh-watch"
CRON_LINE="*/5 * * * * root ${TARGET}/watch_ams_public_ssh_recovery.sh >> /var/log/bvpn-ams-public-ssh-watch.log 2>&1"
CRON_FILE="/etc/cron.d/bvpn-ams-public-ssh-watch"
if grep -qF "$MARK" "$CRON_FILE" 2>/dev/null; then
  echo "OK: cron already installed ($CRON_FILE)"
else
  printf '%s\n%s\n' "$MARK" "$CRON_LINE" >"$CRON_FILE"
  chmod 644 "$CRON_FILE"
  echo "installed $CRON_FILE"
fi
echo "AMS_PUBLIC_SSH_WATCH_CRON_OK"
