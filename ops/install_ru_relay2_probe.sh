#!/usr/bin/env bash
# Q120 / P2-OPS-RU-RELAY-02: bvpncheck + check.py on 2nd RU relay (probe path only).
# Hysteria / panel inbounds — отдельно (VPN-AUD-201). Запуск: root на relay#2.
set -euo pipefail

RELAY_SSH_PORT="${RELAY_SSH_PORT:-3345}"
LV_PUBKEY="${LV_PUBKEY:?set LV_PUBKEY (ed25519 pubkey for bvpncheck)}"
CHECK_SRC="${CHECK_SRC:-/tmp/check.py}"
LV_FROM="${LV_FROM:-176.126.162.158}"

if [[ ! -f "${CHECK_SRC}" ]]; then
  echo "missing ${CHECK_SRC}" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-minimal ufw >/dev/null

if ! id bvpncheck &>/dev/null; then
  useradd -r -s /bin/bash -d /home/bvpncheck -m bvpncheck
else
  usermod -s /bin/bash bvpncheck 2>/dev/null || true
fi

install -d -m 755 /opt/bvpn-check
install -m 755 "${CHECK_SRC}" /opt/bvpn-check/check.py
install -d -m 700 -o bvpncheck -g bvpncheck /home/bvpncheck/.ssh

AUTH="from=\"${LV_FROM}\",command=\"/opt/bvpn-check/check.py\",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ${LV_PUBKEY}"
printf '%s\n' "${AUTH}" > /home/bvpncheck/.ssh/authorized_keys
chmod 600 /home/bvpncheck/.ssh/authorized_keys
chown bvpncheck:bvpncheck /home/bvpncheck/.ssh/authorized_keys

if grep -qE '^#?Port ' /etc/ssh/sshd_config; then
  sed -i "s/^#\\?Port .*/Port ${RELAY_SSH_PORT}/" /etc/ssh/sshd_config
else
  echo "Port ${RELAY_SSH_PORT}" >> /etc/ssh/sshd_config
fi
if ! grep -qE '^Port 22' /etc/ssh/sshd_config; then
  echo "Port 22" >> /etc/ssh/sshd_config
fi

systemctl reload ssh 2>/dev/null || systemctl reload sshd

ufw --force reset >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow 22/tcp comment 'admin bootstrap' >/dev/null
ufw allow "${RELAY_SSH_PORT}/tcp" comment 'lv bvpncheck' >/dev/null
ufw allow 443/tcp comment 'hysteria future' >/dev/null
ufw allow 8443/tcp comment 'hysteria ams fwd future' >/dev/null
ufw --force enable >/dev/null

echo "RU_RELAY2_PROBE_INSTALL_OK port=${RELAY_SSH_PORT}"
