#!/usr/bin/env bash
# VPN-AUD-201: Hysteria relay stack on 2nd RU VPS (mirror relay#1 LV+AMS forwards).
set -euo pipefail

LV_IP="${LV_IP:-176.126.162.158}"
AMS_IP="${AMS_IP:-168.100.11.140}"
HYSTERIA_VERSION="${HYSTERIA_VERSION:-v2.8.1}"
HYSTERIA_PASS="${HYSTERIA_PASS:-e315f6882a9e2b567524fd07170925aa}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates openssl >/dev/null

if [[ ! -x /usr/local/bin/hysteria ]]; then
  tmp=$(mktemp)
  curl -fsSL -o "$tmp" "https://github.com/apernet/hysteria/releases/download/app/${HYSTERIA_VERSION}/hysteria-linux-amd64"
  install -m 755 "$tmp" /usr/local/bin/hysteria
  rm -f "$tmp"
fi

if ! id hysteria &>/dev/null; then
  useradd -r -s /usr/sbin/nologin -d /var/lib/hysteria -m hysteria
fi

install -d -m 755 /etc/hysteria
if [[ ! -f /etc/hysteria/server.crt ]]; then
  openssl req -x509 -nodes -newkey ec:<(openssl ecparam -name prime256v1) \
    -keyout /etc/hysteria/server.key -out /etc/hysteria/server.crt -days 3650 \
    -subj "/CN=localhost" 2>/dev/null || \
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout /etc/hysteria/server.key -out /etc/hysteria/server.crt -days 3650 \
    -subj "/CN=localhost"
  chown hysteria:hysteria /etc/hysteria/server.key /etc/hysteria/server.crt
  chmod 600 /etc/hysteria/server.key
fi

cat >/etc/hysteria/config.yaml <<EOF
listen: :443

tls:
  cert: /etc/hysteria/server.crt
  key: /etc/hysteria/server.key

auth:
  type: password
  password: "${HYSTERIA_PASS}"

masquerade:
  type: proxy
  proxy:
    url: https://bing.com
    rewriteHost: true
EOF

cat >/etc/hysteria/client.yaml <<EOF
server: 127.0.0.1:443

auth: "${HYSTERIA_PASS}"

tls:
  insecure: true

tcpForwarding:
  - listen: 0.0.0.0:443
    remote: ${LV_IP}:443
  - listen: 0.0.0.0:8443
    remote: ${AMS_IP}:443
EOF

cat >/etc/systemd/system/hysteria-server.service <<'EOF'
[Unit]
Description=Hysteria Server Service (config.yaml)
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/hysteria server --config /etc/hysteria/config.yaml
WorkingDirectory=~
User=hysteria
Group=hysteria
Environment=HYSTERIA_LOG_LEVEL=info
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE CAP_NET_RAW
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/hysteria-client.service <<'EOF'
[Unit]
Description=Hysteria Client Service (client.yaml)
After=network.target hysteria-server.service

[Service]
Type=simple
ExecStart=/usr/local/bin/hysteria client --config /etc/hysteria/client.yaml
WorkingDirectory=/etc/hysteria
User=root
Restart=on-failure
RestartSec=5
Environment=HYSTERIA_LOG_LEVEL=info

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hysteria-server hysteria-client
systemctl restart hysteria-server
sleep 2
systemctl restart hysteria-client

ufw allow 443/tcp comment 'relay hysteria' >/dev/null 2>&1 || true
ufw allow 8443/tcp comment 'relay ams fwd' >/dev/null 2>&1 || true

ss -tlnp | grep -E ':443|:8443' || true
echo "RU_RELAY2_HYSTERIA_OK $(hysteria version 2>/dev/null | head -1)"
