#!/bin/bash
# Install setup verify service on bvpn-lv.
set -euo pipefail
ENV_FILE=/etc/bvpn/portal-setup.env
install -d -m 0750 /etc/bvpn
if [[ ! -f "$ENV_FILE" ]]; then
  umask 077
  {
    echo "PORTAL_SETUP_HMAC_SECRET=$(openssl rand -hex 32)"
    echo "PORTAL_WEB_TRIAL_SECRET=$(openssl rand -hex 32)"
  } >"$ENV_FILE"
  chmod 640 "$ENV_FILE"
  echo "created $ENV_FILE"
elif ! grep -q '^PORTAL_WEB_TRIAL_SECRET=' "$ENV_FILE" 2>/dev/null; then
  echo "PORTAL_WEB_TRIAL_SECRET=$(openssl rand -hex 32)" >>"$ENV_FILE"
  echo "appended PORTAL_WEB_TRIAL_SECRET"
fi
for f in portal_setup_token.py setup_verify_service.py site_urls.py load_env_file.py; do
  install -m 0755 "/tmp/$f" "/opt/scripts/$f"
done
UNIT=/etc/systemd/system/bvpn-setup-verify.service
cat >"$UNIT" <<'UNIT'
[Unit]
Description=BenderVPN setup token verify API
After=network.target

[Service]
Type=simple
EnvironmentFile=/etc/bvpn/portal-setup.env
Environment=SETUP_VERIFY_BIND=127.0.0.1
Environment=SETUP_VERIFY_PORT=8871
Environment=PYTHONPATH=/opt/scripts
ExecStart=/usr/bin/python3 /opt/scripts/setup_verify_service.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now bvpn-setup-verify.service
sleep 1
systemctl is-active --quiet bvpn-setup-verify.service
curl -fsS "http://127.0.0.1:8871/verify?t=bad" >/dev/null || true
echo "INSTALL_SETUP_VERIFY_LV_OK"
