#!/bin/bash
set -euo pipefail

# ============================================================
# BenderVPN Node Deployment Script — Matrix v2.4
#
# Usage:
#     bash deploy-node.sh [--dry-run] [--sni-set="d1,d2,d3,d4"] \
#         <IP> <SSH_PORT> <NODE_NAME> <COUNTRY_CODE>
#
# Example:
#     PANEL_TOKEN="$(cat .secrets/panel-token.txt)" \
#         bash deploy-node.sh 95.216.1.1 3344 Germany-01 DE
#
# Panel token resolution order (P0-OPS-01 — keep token out of argv / ps / history):
#   1. $PANEL_TOKEN env var (preferred)
#   2. /etc/bvpn/balancer.env -> PANEL_TOKEN= line (if readable)
#   3. ./.secrets/panel-token.txt (relative to invocation dir)
#   4. interactive `read -rs` prompt (no echo)
#   5. legacy: 5th positional arg with a loud warning (will be removed in v2.6)
# ============================================================

_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -r "$_REPO_ROOT/ops/site.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$_REPO_ROOT/ops/site.env"
  set +a
fi

# --- Configuration ---
PANEL_URL="${PANEL_URL:-https://k9x2m1.conntest.xyz:2053}"
NODE_CONNECT_PORT=2222
TEMPLATE_UUID="${REMNA_TEMPLATE_UUID:-9ebbce97-ae45-4f39-a7e6-d7e675a94a73}"
RELAY_IP="${RU_RELAY_HOST:-72.56.0.145}"
RELAY_SSH_KEY="$HOME/.ssh/selectel_relay"
RELAY_SSH_PORT="${RU_RELAY_SSH_PORT:-3344}"
SUB_URL="${SUB_PUBLIC_ORIGIN:-https://p4n7q.conntest.xyz:2053}"
SHORTID_COUNT=2

# --- SNI Lists ---
WESTERN_SNI=(
    "www.microsoft.com"
    "www.apple.com"
    "api.github.com"
    "www.bing.com"
)
RUSSIAN_SNI=(
    "ads.x5.ru"
    "eh.vk.com"
    "ir-3.ozone.ru"
    "sun6-21.userapi.com"
    "google-analytics.com"
    "pimg.mycdn.me"
    "fonts.googleapis.com"
    "id.x5.ru"
    "5post-gate.x5.ru"
)
# Relay hosts use first 3 Russian SNI
RELAY_SNI=("${RUSSIAN_SNI[0]}" "${RUSSIAN_SNI[1]}" "${RUSSIAN_SNI[2]}")

# sockoptParams for anti-DPI fragmentation (same as all 16 matrix hosts)
SOCKOPT_PARAMS='{"tcpNoDelay":true,"tcpKeepAliveIdle":30,"tcpKeepAliveInterval":15,"fragment":{"length":"50-100","packets":"1-3","interval":"10-20"}}'

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step() { echo -e "\n${CYAN}=== STEP $1 ===${NC}"; }

# --- Parse options ---
DRY_RUN=false
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            echo -e "${YELLOW}=== DRY RUN MODE — no changes will be made ===${NC}"
            ;;
        --sni-set=*)
            IFS=',' read -ra WESTERN_SNI <<< "${1#--sni-set=}"
            if [[ ${#WESTERN_SNI[@]} -lt 1 ]]; then
                err "--sni-set requires at least 1 domain"
            fi
            echo "Custom Western SNI: ${WESTERN_SNI[*]}"
            shift
            ;;
        *)
            err "Unknown option: $1"
            ;;
    esac
done

# Combine SNI lists
ALL_SNI=("${WESTERN_SNI[@]}" "${RUSSIAN_SNI[@]}")

# --- Parse positional arguments ---
NODE_IP="${1:-}"
SSH_PORT="${2:-}"
NODE_NAME="${3:-}"
COUNTRY_CODE="${4:-}"

# --- Resolve PANEL_TOKEN (P0-OPS-01: never accept it via argv silently) ---
PANEL_TOKEN_SOURCE=""

# 5th positional arg is *legacy only*. If someone still passes it,
# loudly warn and proceed — but the long-term path is env/file/prompt.
LEGACY_TOKEN_ARG="${5:-}"

if [[ -n "${PANEL_TOKEN:-}" ]]; then
    PANEL_TOKEN_SOURCE="env:PANEL_TOKEN"
elif [[ -r /etc/bvpn/balancer.env ]]; then
    _t=$(grep -E '^[[:space:]]*PANEL_TOKEN=' /etc/bvpn/balancer.env \
         | head -n 1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '\r\n')
    if [[ -n "$_t" ]]; then
        PANEL_TOKEN="$_t"
        PANEL_TOKEN_SOURCE="/etc/bvpn/balancer.env"
    fi
    unset _t
elif [[ -r .secrets/panel-token.txt ]]; then
    PANEL_TOKEN=$(tr -d '\r\n' < .secrets/panel-token.txt)
    PANEL_TOKEN_SOURCE=".secrets/panel-token.txt"
fi

if [[ -z "${PANEL_TOKEN:-}" && -n "$LEGACY_TOKEN_ARG" ]]; then
    echo -e "${YELLOW}[WARN]${NC} Passing PANEL_TOKEN via argv is deprecated (visible in ps/history)." >&2
    echo -e "${YELLOW}[WARN]${NC} Prefer:  PANEL_TOKEN=\"\$(cat .secrets/panel-token.txt)\" bash deploy-node.sh ..." >&2
    PANEL_TOKEN="$LEGACY_TOKEN_ARG"
    PANEL_TOKEN_SOURCE="argv[5] (DEPRECATED)"
fi

if [[ -z "${PANEL_TOKEN:-}" && -t 0 ]]; then
    # Interactive fallback — no echo, no history.
    echo -n "PANEL_TOKEN (input hidden): " >&2
    IFS= read -rs PANEL_TOKEN
    echo >&2
    [[ -n "$PANEL_TOKEN" ]] && PANEL_TOKEN_SOURCE="interactive prompt"
fi

# Best-effort: ensure the token is not in the next caller's history
# by removing the matching history entry (no-op when not in bash interactive).
if [[ -n "$LEGACY_TOKEN_ARG" ]] && command -v history >/dev/null 2>&1; then
    history -d "$(history 1 | awk '{print $1}')" 2>/dev/null || true
fi

if [[ -z "$NODE_IP" || -z "$SSH_PORT" || -z "$NODE_NAME" || -z "$COUNTRY_CODE" || -z "${PANEL_TOKEN:-}" ]]; then
    echo "Usage: bash deploy-node.sh [--dry-run] [--sni-set=\"d1,d2,d3,d4\"] <IP> <SSH_PORT> <NODE_NAME> <COUNTRY_CODE>"
    echo "Token: set \$PANEL_TOKEN env var (preferred), or put it in .secrets/panel-token.txt,"
    echo "       or let the script read it via /etc/bvpn/balancer.env / interactive prompt."
    echo "Example: PANEL_TOKEN=\"\$(cat .secrets/panel-token.txt)\" bash deploy-node.sh 95.216.1.1 3344 Germany-01 DE"
    exit 1
fi

# --- Helper functions ---
remote() {
    if $DRY_RUN; then
        echo "  [DRY] ssh -p $SSH_PORT root@$NODE_IP '$1'"
    else
        ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -p "$SSH_PORT" "root@$NODE_IP" "$1"
    fi
}

relay_ssh() {
    if $DRY_RUN; then
        echo "  [DRY] ssh -i $RELAY_SSH_KEY -p $RELAY_SSH_PORT root@$RELAY_IP '$1'"
    else
        ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i "$RELAY_SSH_KEY" -p "$RELAY_SSH_PORT" "root@$RELAY_IP" "$1"
    fi
}

# P0-OPS-01 hardening: pass Authorization header via curl --config (read from
# stdin) so it never appears in `ps -ef` / shell history. Other args remain
# visible (URL, method) but the secret stays out of /proc/$pid/cmdline.
_curl_auth_config() {
    # Emit a curl config file body to stdout. The header value is enclosed in
    # double quotes; backslashes and quotes are escaped to keep parsing sane.
    local tok_escaped=${PANEL_TOKEN//\\/\\\\}
    tok_escaped=${tok_escaped//\"/\\\"}
    printf 'header = "Authorization: Bearer %s"\n' "$tok_escaped"
}

api_get() {
    _curl_auth_config | curl -sf --config - "$PANEL_URL$1"
}

api_post() {
    _curl_auth_config | curl -sf --config - -X POST -H "Content-Type: application/json" -d "$2" "$PANEL_URL$1"
}

api_patch() {
    _curl_auth_config | curl -sf --config - -X PATCH -H "Content-Type: application/json" -d "$2" "$PANEL_URL$1"
}

# Timestamp for backups
TS=$(date +%Y%m%d_%H%M%S)

# Collect host UUIDs for template update
NEW_HOST_UUIDS=()

# ============================================================
step "A — Validate inputs"
# ============================================================

echo "  Node IP:       $NODE_IP"
echo "  SSH Port:      $SSH_PORT"
echo "  Node Name:     $NODE_NAME"
echo "  Country:       $COUNTRY_CODE"
echo "  Panel URL:     $PANEL_URL"
echo "  Panel Token:   ${PANEL_TOKEN:0:8}…${PANEL_TOKEN: -4} (len=${#PANEL_TOKEN}, source: ${PANEL_TOKEN_SOURCE:-unknown})"
echo "  Western SNI:   ${WESTERN_SNI[*]}"
echo "  Russian SNI:   ${RUSSIAN_SNI[*]}"
echo "  Total SNI:     ${#ALL_SNI[@]}"

if ! $DRY_RUN; then
    # Test SSH to new node
    remote "echo 'SSH connection OK'" || err "Cannot SSH to $NODE_IP:$SSH_PORT"
    log "SSH to new node verified"

    # Test SSH to Relay
    relay_ssh "echo 'Relay SSH OK'" || err "Cannot SSH to Relay $RELAY_IP:$RELAY_SSH_PORT"
    log "SSH to Relay verified"

    # Test panel API
    api_get "/api/nodes" > /dev/null || err "Cannot reach panel API at $PANEL_URL"
    log "Panel API reachable"

    # Check node not already registered
    EXISTING=$(api_get "/api/nodes" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for n in d.get('response', []):
    if n.get('address') == '$NODE_IP':
        print(n.get('name'))
" 2>/dev/null)
    if [[ -n "$EXISTING" ]]; then
        warn "Node $NODE_IP already registered as '$EXISTING'"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
    fi
else
    log "Inputs validated (dry-run)"
fi

# ============================================================
step "B — Install Docker"
# ============================================================

DOCKER_SCRIPT='
if command -v docker &>/dev/null; then
    echo "Docker already installed: $(docker --version)"
else
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    echo "Docker installed: $(docker --version)"
fi
'
remote "$DOCKER_SCRIPT"
log "Docker ready"

# ============================================================
step "C — Configure UFW"
# ============================================================

UFW_SCRIPT="
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ${SSH_PORT}/tcp comment 'SSH'
ufw allow 443/tcp comment 'VLESS Reality'
ufw allow 8443/tcp comment 'VLESS XHTTP'
ufw deny 9443/tcp comment 'Selfsteal internal only'
ufw allow from 176.126.162.158 to any port ${NODE_CONNECT_PORT} comment 'Remnawave panel Latvia'
ufw allow from 168.100.11.140 to any port ${NODE_CONNECT_PORT} comment 'Remnawave panel Amsterdam'
# Panel in Docker on same host uses bridge (172.17/172.18); without this, health-check to NODE_IP:2222 times out.
ufw allow from 172.17.0.0/16 to any port ${NODE_CONNECT_PORT} proto tcp comment 'Remnawave panel Docker default bridge'
ufw allow from 172.18.0.0/16 to any port ${NODE_CONNECT_PORT} proto tcp comment 'Remnawave panel Docker compose network'
echo 'UFW configured'
ufw status numbered
"
remote "$UFW_SCRIPT"
log "UFW configured"

# ============================================================
step "D — Generate Reality keypair"
# ============================================================

if $DRY_RUN; then
    PRIVATE_KEY="DRY_RUN_PRIVATE_KEY_PLACEHOLDER"
    PUBLIC_KEY="DRY_RUN_PUBLIC_KEY_PLACEHOLDER"
    log "Keys generated (dry-run placeholder)"
else
    KEYS=$(remote 'docker pull ghcr.io/xtls/xray-core:latest >/dev/null 2>&1; docker run --rm ghcr.io/xtls/xray-core:latest x25519 2>/dev/null')
    # xray-core 1.8.x: "Private key:" / "Public key:"
    # xray-core 1.250+: "PrivateKey:" / "Password (PublicKey):"
    PRIVATE_KEY=$(echo "$KEYS" | grep -iE '^private|^PrivateKey' | head -1 | awk '{print $NF}')
    PUBLIC_KEY=$(echo "$KEYS" | grep -iE 'public' | head -1 | awk '{print $NF}')

    if [[ -z "$PRIVATE_KEY" || -z "$PUBLIC_KEY" ]]; then
        err "Failed to generate Reality keys"
    fi
    log "Reality keys generated"
    echo "  Private: $PRIVATE_KEY"
    echo "  Public:  $PUBLIC_KEY"
fi

# ============================================================
step "E — Generate short IDs"
# ============================================================

if $DRY_RUN; then
    SHORT_ID_1="0123456789abcdef"
    SHORT_ID_2="fedcba9876543210"
else
    SHORT_ID_1=$(openssl rand -hex 8)
    SHORT_ID_2=$(openssl rand -hex 8)
fi
log "Short IDs: $SHORT_ID_1, $SHORT_ID_2"

# ============================================================
step "F — Deploy Caddy selfsteal (reverse_proxy)"
# ============================================================

# Generate Caddyfile with 13 reverse_proxy blocks (one per SNI)
CADDYFILE_CONTENT=""
for SNI in "${ALL_SNI[@]}"; do
    CADDYFILE_CONTENT+="
${SNI}:9443 {
    tls internal
    reverse_proxy https://${SNI} {
        header_up Host ${SNI}
        header_up -X-Forwarded-For
        header_up -X-Forwarded-Proto
        header_up -X-Real-IP
        header_up -X-Forwarded-Host
        transport http {
            tls
            tls_server_name ${SNI}
            dial_timeout 5s
            versions 1.1 2
        }
    }
}
"
done

# Write Caddyfile to temp file on local machine, then transfer
CADDY_TMP="/tmp/caddyfile-${NODE_NAME}-${TS}"
echo "$CADDYFILE_CONTENT" > "$CADDY_TMP"

CADDY_SETUP_SCRIPT="
mkdir -p /opt/caddy

# docker-compose.yml for Caddy
cat > /opt/caddy/docker-compose.yml << 'COMPEOF'
services:
  caddy-selfsteal:
    image: caddy:2.9
    container_name: caddy-selfsteal
    network_mode: host
    restart: always
    volumes:
      - /opt/caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_selfsteal_data:/data
      - caddy_selfsteal_config:/config

volumes:
  caddy_selfsteal_data:
  caddy_selfsteal_config:
COMPEOF
"

if $DRY_RUN; then
    echo "  [DRY] Would write Caddyfile with ${#ALL_SNI[@]} reverse_proxy blocks"
    echo "  [DRY] Would deploy Caddy Docker container"
    remote "$CADDY_SETUP_SCRIPT"
else
    # Transfer Caddyfile
    remote "mkdir -p /opt/caddy"
    scp -o StrictHostKeyChecking=accept-new -P "$SSH_PORT" "$CADDY_TMP" "root@$NODE_IP:/opt/caddy/Caddyfile"
    rm -f "$CADDY_TMP"

    # Deploy docker-compose
    remote "$CADDY_SETUP_SCRIPT"

    # Start Caddy
    remote "cd /opt/caddy && docker compose up -d"

    # Validate Caddyfile inside container
    sleep 3
    remote "docker exec caddy-selfsteal caddy validate --config /etc/caddy/Caddyfile" || warn "Caddy validate failed — check config"

    # Verify reverse_proxy works (test 3 SNI)
    sleep 5
    VERIFY_OK=0
    for TEST_SNI in "${WESTERN_SNI[0]}" "${RUSSIAN_SNI[0]}" "${RUSSIAN_SNI[1]}"; do
        RESULT=$(remote "curl -s -o /dev/null -w '%{http_code}' --resolve '${TEST_SNI}:9443:127.0.0.1' 'https://${TEST_SNI}:9443' -k --max-time 10")
        if [[ "$RESULT" =~ ^(200|301|302|303|307|308|403)$ ]]; then
            log "Selfsteal $TEST_SNI: HTTP $RESULT (real content)"
            VERIFY_OK=$((VERIFY_OK + 1))
        else
            warn "Selfsteal $TEST_SNI: HTTP $RESULT (unexpected)"
        fi
    done
    if [[ $VERIFY_OK -lt 2 ]]; then
        warn "Only $VERIFY_OK/3 selfsteal checks passed — verify manually"
    fi
fi

log "Caddy selfsteal deployed with ${#ALL_SNI[@]} reverse_proxy blocks"

# ============================================================
step "G — Create config profile in panel"
# ============================================================

# Build serverNames JSON with ALL 13 SNI
SNI_JSON=$(python3 -c "
import json
sni = '${ALL_SNI[*]}'.split()
print(json.dumps(sni))
")

XRAY_CONFIG=$(python3 -c "
import json

config = {
    'log': {'loglevel': 'warning'},
    'dns': {'servers': ['1.1.1.1', '8.8.8.8']},
    'inbounds': [
        {
            'tag': 'VLESS_REALITY_${COUNTRY_CODE}',
            'port': 443,
            'protocol': 'vless',
            'settings': {'clients': [], 'decryption': 'none'},
            'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
            'streamSettings': {
                'network': 'tcp',
                'sockopt': {'tcpNoDelay': True, 'tcpFastOpen': True},
                'security': 'reality',
                'realitySettings': {
                    'dest': '127.0.0.1:9443',
                    'show': False,
                    'xver': 0,
                    'shortIds': ['${SHORT_ID_1}', '${SHORT_ID_2}'],
                    'privateKey': '${PRIVATE_KEY}',
                    'serverNames': ${SNI_JSON}
                }
            }
        },
        {
            'tag': 'VLESS_XHTTP_${COUNTRY_CODE}',
            'port': 8443,
            'protocol': 'vless',
            'settings': {'clients': [], 'decryption': 'none'},
            'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
            'streamSettings': {
                'network': 'xhttp',
                'security': 'reality',
                'xhttpSettings': {'path': '/'},
                'realitySettings': {
                    'dest': '127.0.0.1:9443',
                    'show': False,
                    'xver': 0,
                    'shortIds': ['${SHORT_ID_1}', '${SHORT_ID_2}'],
                    'privateKey': '${PRIVATE_KEY}',
                    'serverNames': ${SNI_JSON}
                }
            }
        }
    ],
    'outbounds': [
        {'tag': 'DIRECT', 'protocol': 'freedom', 'settings': {'domainStrategy': 'UseIPv4'}},
        {'tag': 'BLOCK', 'protocol': 'blackhole'}
    ],
    'routing': {
        'rules': [{'ip': ['geoip:private'], 'type': 'field', 'outboundTag': 'BLOCK'}]
    }
}
print(json.dumps(config))
")

PROFILE_NAME="${NODE_NAME} Selfsteal"
PROFILE_BODY=$(python3 -c "
import json
config = json.loads('''${XRAY_CONFIG}''')
body = {'name': '${PROFILE_NAME}', 'config': config}
print(json.dumps(body))
")

if $DRY_RUN; then
    echo "  [DRY] POST /api/config-profiles with name='$PROFILE_NAME'"
    echo "  [DRY] serverNames includes ${#ALL_SNI[@]} SNI"
    PROFILE_UUID="dry-run-profile-uuid"
    INBOUND_REALITY_UUID="dry-run-reality-inbound-uuid"
    INBOUND_XHTTP_UUID="dry-run-xhttp-inbound-uuid"
else
    PROFILE_RESP=$(api_post "/api/config-profiles" "$PROFILE_BODY")
    PROFILE_UUID=$(echo "$PROFILE_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['response']['uuid'])")

    # Get inbound UUIDs from the created profile
    PROFILE_DETAIL=$(api_get "/api/config-profiles/inbounds" | python3 -c "
import json,sys
d = json.load(sys.stdin)
inbounds = d['response']['inbounds']
for inb in inbounds:
    if inb['profileUuid'] == '$PROFILE_UUID':
        print(inb['uuid'], inb['tag'])
")
    INBOUND_REALITY_UUID=$(echo "$PROFILE_DETAIL" | grep "REALITY" | awk '{print $1}')
    INBOUND_XHTTP_UUID=$(echo "$PROFILE_DETAIL" | grep "XHTTP" | awk '{print $1}')

    if [[ -z "$PROFILE_UUID" || -z "$INBOUND_REALITY_UUID" || -z "$INBOUND_XHTTP_UUID" ]]; then
        err "Failed to create config profile or get inbound UUIDs"
    fi
    log "Config profile created: $PROFILE_UUID"
    echo "  Reality inbound: $INBOUND_REALITY_UUID"
    echo "  XHTTP inbound:   $INBOUND_XHTTP_UUID"
fi

# ============================================================
step "H — Register node in panel"
# ============================================================

NODE_BODY=$(python3 -c "
import json
body = {
    'name': '$NODE_NAME',
    'address': '$NODE_IP',
    'port': $NODE_CONNECT_PORT,
    'countryCode': '$COUNTRY_CODE',
    'configProfile': {
        'activeConfigProfileUuid': '$PROFILE_UUID',
        'activeInbounds': ['$INBOUND_REALITY_UUID', '$INBOUND_XHTTP_UUID']
    }
}
print(json.dumps(body))
")

if $DRY_RUN; then
    echo "  [DRY] POST /api/nodes with name='$NODE_NAME', address='$NODE_IP'"
    echo "  [DRY] GET  /api/keygen  → SECRET_KEY"
    SECRET_KEY="dry-run-secret-key-placeholder"
    NODE_UUID="dry-run-node-uuid"
else
    NODE_RESP=$(api_post "/api/nodes" "$NODE_BODY")
    NODE_UUID=$(echo "$NODE_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['response']['uuid'])")
    [[ -z "$NODE_UUID" || "$NODE_UUID" == "None" ]] && err "Failed to register node: $NODE_RESP"
    log "Node registered: $NODE_UUID"

    # Newer Remnawave returns the node SECRET_KEY (base64-JSON containing
    # per-node TLS cert + CA + JWT pubkey) from /api/keygen, not from the
    # node-create response. Each call generates a fresh keypair signed by
    # the panel CA; remnanode validates traffic from panel using this blob.
    KEYGEN_RESP=$(api_get "/api/keygen")
    SECRET_KEY=$(echo "$KEYGEN_RESP" | python3 -c "
import json, sys
d = json.load(sys.stdin)
r = d.get('response', {})
for key in ('pubKey', 'secretKey', 'secret_key', 'connectionString'):
    if key in r and r[key]:
        print(r[key])
        break
")
    [[ -z "$SECRET_KEY" ]] && err "Could not obtain SECRET_KEY from /api/keygen: $KEYGEN_RESP"
    log "SECRET_KEY obtained from /api/keygen (${#SECRET_KEY} chars)"
fi

# ============================================================
step "I — Deploy remnanode"
# ============================================================

REMNANODE_SETUP="
mkdir -p /opt/remnanode
cat > /opt/remnanode/docker-compose.yml << 'RNEOF'
services:
  remnanode:
    container_name: remnanode
    hostname: remnanode
    image: remnawave/node:latest
    network_mode: host
    restart: always
    cap_add:
      - NET_ADMIN
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    environment:
      - NODE_PORT=${NODE_CONNECT_PORT}
      - SECRET_KEY=${SECRET_KEY}
RNEOF
cd /opt/remnanode && docker compose pull && docker compose up -d
echo 'Remnanode deployed'
"
remote "$REMNANODE_SETUP"
log "Remnanode container started"

# ============================================================
step "J — Wait for node to connect"
# ============================================================

if ! $DRY_RUN; then
    echo "  Waiting for node to connect to panel..."
    STATUS=""
    for i in $(seq 1 12); do
        sleep 5
        STATUS=$(api_get "/api/nodes" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for n in d.get('response', []):
    if n.get('address') == '$NODE_IP':
        print('connected' if n.get('isConnected') else 'connecting')
" 2>/dev/null)
        if [[ "$STATUS" == "connected" ]]; then
            log "Node connected to panel!"
            break
        fi
        echo "  ... attempt $i/12 ($STATUS)"
    done
    if [[ "$STATUS" != "connected" ]]; then
        warn "Node not connected after 60s — check logs: ssh -p $SSH_PORT root@$NODE_IP 'docker logs remnanode --tail 30'"
    fi
else
    log "Node connection check (dry-run skipped)"
fi

# ============================================================
step "K' — Update Russia Relay (Hysteria2 forwarding)"
# ============================================================

if $DRY_RUN; then
    echo "  [DRY] Would SSH to Relay $RELAY_IP and add tcpForwarding for $NODE_IP:443"
    RELAY_PORT=9443
    log "Relay update (dry-run): port $RELAY_PORT"
else
    # Backup current client.yaml on Relay
    relay_ssh "cp /etc/hysteria/client.yaml /etc/hysteria/client.yaml.bak.${TS}"
    log "Relay client.yaml backed up"

    # Find next available port and add forwarding
    # Write Python script to relay, execute it
    RELAY_SCRIPT=$(cat << 'PYEOF'
import sys, re, os

config_path = "/etc/hysteria/client.yaml"
new_node_ip = sys.argv[1]

with open(config_path, 'r') as f:
    content = f.read()

# Parse existing listen ports from tcpForwarding entries
# Format in YAML: "  listen: 0.0.0.0:PORT" or "  listen: :PORT"
existing_ports = set()
for m in re.finditer(r'listen:\s*(?:0\.0\.0\.0)?:(\d+)', content):
    existing_ports.add(int(m.group(1)))

# Port sequence: 443, 8443, 9443, 10443, 11443...
# Find first available starting from 9443
next_port = 9443
while next_port in existing_ports:
    next_port += 1000

# Append new tcpForwarding entry to the file
# Hysteria2 client.yaml uses list format under tcpForwarding
new_entry = f"""  - listen: 0.0.0.0:{next_port}
    remote: {new_node_ip}:443
"""

# If tcpForwarding section exists, append to it; otherwise create it
if 'tcpForwarding:' in content:
    # Append before the next top-level key or at end
    # Find the end of tcpForwarding section
    lines = content.split('\n')
    insert_idx = len(lines)
    in_tcp = False
    for i, line in enumerate(lines):
        if line.startswith('tcpForwarding:'):
            in_tcp = True
            continue
        if in_tcp and line and not line.startswith(' ') and not line.startswith('\t'):
            insert_idx = i
            break
    lines.insert(insert_idx, new_entry.rstrip())
    content = '\n'.join(lines)
else:
    content += f"\ntcpForwarding:\n{new_entry}"

with open(config_path, 'w') as f:
    f.write(content)

print(next_port)
PYEOF
    )

    # Transfer script and execute
    relay_ssh "cat > /tmp/update_relay.py << 'SCRIPT_END'
${RELAY_SCRIPT}
SCRIPT_END"

    RELAY_PORT=$(relay_ssh "python3 /tmp/update_relay.py '$NODE_IP'")
    RELAY_PORT=$(echo "$RELAY_PORT" | tr -d '[:space:]')

    if [[ -z "$RELAY_PORT" || ! "$RELAY_PORT" =~ ^[0-9]+$ ]]; then
        warn "Failed to determine relay port, got: '$RELAY_PORT'"
        # Rollback relay
        relay_ssh "cp /etc/hysteria/client.yaml.bak.${TS} /etc/hysteria/client.yaml"
        err "Relay update failed — rolled back client.yaml"
    fi
    log "Relay forwarding added: :${RELAY_PORT} → ${NODE_IP}:443"

    # Restart Hysteria on Relay
    # Find the correct service name
    HYSTERIA_SVC=$(relay_ssh "systemctl list-units --type=service --no-legend | grep -i hysteria | awk '{print \$1}' | head -1")
    HYSTERIA_SVC=$(echo "$HYSTERIA_SVC" | tr -d '[:space:]')

    if [[ -z "$HYSTERIA_SVC" ]]; then
        warn "Could not find Hysteria service — trying common names"
        for svc in hysteria-client hysteria2-client hysteria; do
            if relay_ssh "systemctl is-enabled $svc 2>/dev/null" &>/dev/null; then
                HYSTERIA_SVC="$svc"
                break
            fi
        done
    fi

    if [[ -n "$HYSTERIA_SVC" ]]; then
        relay_ssh "systemctl restart $HYSTERIA_SVC"
        log "Relay Hysteria restarted ($HYSTERIA_SVC)"
    else
        warn "Could not find Hysteria service to restart — manual restart needed"
    fi

    # Verify relay port is listening
    sleep 3
    if nc -z -w 5 "$RELAY_IP" "$RELAY_PORT" 2>/dev/null; then
        log "Relay port $RELAY_PORT is reachable"
    else
        warn "Relay port $RELAY_PORT not reachable from Latvia — may need time or manual check"
    fi

    # Cleanup
    relay_ssh "rm -f /tmp/update_relay.py"
fi

# ============================================================
step "K — Create 8 matrix hosts in panel"
# ============================================================

# Determine emoji flag from country code
FLAG=$(python3 -c "
cc = '$COUNTRY_CODE'.upper()
flag = chr(0x1F1E6 + ord(cc[0]) - ord('A')) + chr(0x1F1E6 + ord(cc[1]) - ord('A'))
print(flag)
")

# SNI short names for remarks
sni_short() {
    case "$1" in
        www.microsoft.com)  echo "MS" ;;
        www.apple.com)      echo "Apple" ;;
        api.github.com)     echo "GitHub" ;;
        www.bing.com)       echo "Bing" ;;
        ads.x5.ru)          echo "X5" ;;
        eh.vk.com)          echo "VK" ;;
        ir-3.ozone.ru)      echo "Ozon" ;;
        sun6-21.userapi.com) echo "Userapi" ;;
        *)                  echo "$1" | cut -d. -f1 ;;
    esac
}

create_host() {
    local REMARK="$1"
    local ADDRESS="$2"
    local PORT="$3"
    local INB_UUID="$4"
    local SNI="$5"

    local BODY
    BODY=$(python3 -c "
import json
body = {
    'remark': '''${REMARK}''',
    'address': '${ADDRESS}',
    'port': ${PORT},
    'sni': '${SNI}',
    'fingerprint': 'chrome',
    'isDisabled': False,
    'isHidden': True,
    'inbound': {
        'configProfileUuid': '${PROFILE_UUID}',
        'configProfileInboundUuid': '${INB_UUID}'
    },
    'nodes': ['${NODE_UUID}'],
    'sockoptParams': json.loads('''${SOCKOPT_PARAMS}''')
}
print(json.dumps(body))
")

    if $DRY_RUN; then
        echo "  [DRY] POST /api/hosts: $REMARK ($ADDRESS:$PORT, SNI=$SNI)" >&2
        echo "dry-run-host-uuid-$(echo "$REMARK" | md5sum | cut -c1-8)"
    else
        local RESP
        RESP=$(api_post "/api/hosts" "$BODY")
        local HOST_UUID
        HOST_UUID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['response']['uuid'])" 2>/dev/null)
        if [[ -n "$HOST_UUID" && "$HOST_UUID" != "None" ]]; then
            log "Host created: $REMARK ($HOST_UUID)" >&2
            echo "$HOST_UUID"
        else
            warn "Host creation may have failed for: $REMARK" >&2
            echo "$RESP" | head -5 >&2
            echo ""
        fi
    fi
}

echo "Creating 8 matrix hosts (all isHidden=true)..."

# --- 4 Direct hosts (one per Western SNI, REALITY inbound, node IP) ---
for W_SNI in "${WESTERN_SNI[@]}"; do
    SHORT=$(sni_short "$W_SNI")
    UUID=$(create_host "$FLAG $NODE_NAME · Direct · $SHORT" "$NODE_IP" 443 "$INBOUND_REALITY_UUID" "$W_SNI")
    [[ -n "$UUID" ]] && NEW_HOST_UUIDS+=("$UUID")
done

# --- 1 XHTTP host (first Western SNI, XHTTP inbound, node IP) ---
XHTTP_SNI="${WESTERN_SNI[0]}"
XHTTP_SHORT=$(sni_short "$XHTTP_SNI")
UUID=$(create_host "$FLAG $NODE_NAME · XHTTP · $XHTTP_SHORT" "$NODE_IP" 8443 "$INBOUND_XHTTP_UUID" "$XHTTP_SNI")
[[ -n "$UUID" ]] && NEW_HOST_UUIDS+=("$UUID")

# --- 3 Relay hosts (first 3 Russian SNI, REALITY inbound, Relay IP, Relay port) ---
for R_SNI in "${RELAY_SNI[@]}"; do
    SHORT=$(sni_short "$R_SNI")
    UUID=$(create_host "$FLAG Relay $NODE_NAME · $SHORT" "$RELAY_IP" "${RELAY_PORT:-9443}" "$INBOUND_REALITY_UUID" "$R_SNI")
    [[ -n "$UUID" ]] && NEW_HOST_UUIDS+=("$UUID")
done

echo ""
echo "  Created ${#NEW_HOST_UUIDS[@]} hosts"
if [[ ${#NEW_HOST_UUIDS[@]} -ne 8 ]]; then
    warn "Expected 8 hosts, got ${#NEW_HOST_UUIDS[@]} — some creations may have failed"
fi
log "All matrix hosts created"

# ============================================================
step "L' — Update injectHosts in subscription template"
# ============================================================

if [[ ${#NEW_HOST_UUIDS[@]} -eq 0 ]]; then
    warn "No host UUIDs collected — skipping template update"
else
    echo "  Hosts to add to template: ${NEW_HOST_UUIDS[*]}"

    if $DRY_RUN; then
        echo "  [DRY] Would backup template $TEMPLATE_UUID"
        echo "  [DRY] Would add ${#NEW_HOST_UUIDS[@]} UUIDs to injectHosts.values"
        echo "  [DRY] Would verify via Happ subscription test"
    else
        # 1. Backup template
        mkdir -p /opt/diagnostics/matrix-migration
        TEMPLATE_BACKUP="/opt/diagnostics/matrix-migration/template-backup-${TS}.json"
        api_get "/api/subscription-templates/${TEMPLATE_UUID}" > "$TEMPLATE_BACKUP"
        log "Template backed up to $TEMPLATE_BACKUP"

        # 2. Validate all new host UUIDs exist
        echo "  Validating host UUIDs..."
        for HID in "${NEW_HOST_UUIDS[@]}"; do
            if ! api_get "/api/hosts/${HID}" > /dev/null 2>&1; then
                err "Host UUID $HID does not exist in panel — aborting template update"
            fi
        done
        log "All ${#NEW_HOST_UUIDS[@]} host UUIDs verified"

        # 3. Parse template, add UUIDs, send full template via PATCH.
        # Remnawave panel exposes the xray-with-injectHosts JSON under the
        # `templateJson` field, and expects PATCH on /api/subscription-templates
        # (no UUID path) with the full template object in the body.
        NEW_UUIDS_JSON=$(python3 -c "import json; print(json.dumps('${NEW_HOST_UUIDS[*]}'.split()))")

        cat > /tmp/update_template.py << 'PYEOF'
import json, sys

template_file = sys.argv[1]
new_uuids = json.loads(sys.argv[2])
output_file = sys.argv[3]

with open(template_file, 'r') as f:
    data = json.load(f)

template = data.get('response', data)
doc = template.get('templateJson')
if not isinstance(doc, dict):
    print("ERROR: template.templateJson is missing or not an object", file=sys.stderr)
    sys.exit(1)

inject_hosts = doc.get('remnawave', {}).get('injectHosts', [])
if not inject_hosts:
    print("ERROR: No remnawave.injectHosts in templateJson", file=sys.stderr)
    sys.exit(1)

selector = inject_hosts[0].setdefault('selector', {})
current_values = list(selector.get('values') or [])
print(f"Current injectHosts count: {len(current_values)}", file=sys.stderr)

for uid in new_uuids:
    if uid in current_values:
        print(f"ERROR: UUID {uid} already in injectHosts — duplicate!", file=sys.stderr)
        sys.exit(1)

updated_values = current_values + new_uuids
selector['values'] = updated_values
print(f"Updated injectHosts count: {len(updated_values)}", file=sys.stderr)

minimal = {
    'uuid': template.get('uuid'),
    'templateJson': doc,
    'viewPosition': template.get('viewPosition'),
    'templateType': template.get('templateType'),
}
with open(output_file, 'w') as f:
    json.dump(minimal, f, ensure_ascii=False)

print(f"OK: {len(new_uuids)} UUIDs added", file=sys.stderr)
print(len(updated_values))
PYEOF

        UPDATE_RESULT=$(python3 /tmp/update_template.py "$TEMPLATE_BACKUP" "$NEW_UUIDS_JSON" /tmp/new-template.json 2>&1)
        UPDATE_COUNT=$(echo "$UPDATE_RESULT" | tail -1)
        echo "$UPDATE_RESULT" | head -n -1 | while IFS= read -r line; do echo "  $line"; done

        if [[ ! "$UPDATE_COUNT" =~ ^[0-9]+$ ]]; then
            err "Template update script failed: $UPDATE_RESULT"
        fi

        # 4. Show diff summary
        echo "  Template diff: injectHosts.values grew to $UPDATE_COUNT entries"

        # 5. Apply via PATCH /api/subscription-templates (no UUID in path,
        #    uuid is part of body).
        PATCH_BODY=$(cat /tmp/new-template.json)
        HTTP_CODE=$(_curl_auth_config | curl -s --config - \
            -o /tmp/template-patch-response.txt -w '%{http_code}' \
            -X PATCH \
            -H "Content-Type: application/json" \
            -d "$PATCH_BODY" \
            "$PANEL_URL/api/subscription-templates")

        if [[ "$HTTP_CODE" =~ ^(200|201|204)$ ]]; then
            log "Template PATCH applied (HTTP $HTTP_CODE)"
        else
            warn "Template PATCH returned HTTP $HTTP_CODE"
            cat /tmp/template-patch-response.txt | head -10
            echo ""
            warn "ROLLING BACK template from backup..."
            ROLLBACK_BODY=$(python3 -c "
import json
with open('$TEMPLATE_BACKUP') as f:
    d = json.load(f)
t = d.get('response', d)
out = {
    'uuid': t.get('uuid'),
    'templateJson': t.get('templateJson'),
    'viewPosition': t.get('viewPosition'),
    'templateType': t.get('templateType'),
}
print(json.dumps(out))
")
            api_patch "/api/subscription-templates" "$ROLLBACK_BODY" \
                || warn "Rollback also failed — manual intervention needed"
            err "Template update failed — rolled back"
        fi

        # 6. Verify template was updated
        VERIFY_COUNT=$(api_get "/api/subscription-templates/${TEMPLATE_UUID}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
t = d.get('response', d)
doc = t.get('templateJson') or {}
values = (doc.get('remnawave', {}).get('injectHosts') or [{}])[0].get('selector', {}).get('values', [])
print(len(values))
" 2>/dev/null)

        if [[ "$VERIFY_COUNT" == "$UPDATE_COUNT" ]]; then
            log "Template verified: $VERIFY_COUNT hosts in injectHosts"
        else
            warn "Template verification mismatch: expected $UPDATE_COUNT, got $VERIFY_COUNT"
        fi

        # 7. Cleanup temp files
        rm -f /tmp/update_template.py /tmp/new-template.json /tmp/template-patch-response.txt

        log "Template updated: ${#NEW_HOST_UUIDS[@]} hosts added to injectHosts"
    fi
fi

# ============================================================
step "L'' — Append new inbounds to internal squads"
# ============================================================
# Without this, the new node's inbounds are not in any squad and users
# (who have activeInternalSquads set) will not see the new node's hosts
# in their subscription, regardless of injectHosts.

if $DRY_RUN; then
    echo "  [DRY] Would PATCH each internal-squad that already includes"
    echo "  [DRY] another node's REALITY inbound; append NL Reality + XHTTP"
    log "Internal-squad update (dry-run)"
else
    SQUAD_BODY=$(python3 -c "
import json
new_inbounds = ['$INBOUND_REALITY_UUID', '$INBOUND_XHTTP_UUID']
print(json.dumps(new_inbounds))
")

    SQUADS_JSON=$(api_get "/api/internal-squads")
    SQUADS_TO_UPDATE=$(echo "$SQUADS_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
payload = d.get('response')
squads = payload.get('internalSquads') if isinstance(payload, dict) and 'internalSquads' in payload else payload
if not isinstance(squads, list):
    sys.exit(0)
for sq in squads:
    # Update squads whose inbound list overlaps with the same proto (vless reality/xhttp)
    tags = {(ib or {}).get('tag', '') for ib in (sq.get('inbounds') or [])}
    if any(t.startswith('VLESS_REALITY_') for t in tags) or any(t.startswith('VLESS_XHTTP_') for t in tags):
        ids = [ib['uuid'] for ib in sq['inbounds']]
        print(sq['uuid'] + ' ' + ','.join(ids))
")

    if [[ -z "$SQUADS_TO_UPDATE" ]]; then
        warn "No internal-squad found with VLESS_REALITY_*/VLESS_XHTTP_* inbounds — new node will not appear in any user's subscription"
    else
        while IFS=' ' read -r SQUAD_UUID OLD_IDS; do
            [[ -z "$SQUAD_UUID" ]] && continue
            NEW_INBOUNDS=$(python3 -c "
old = '${OLD_IDS}'.split(',') if '${OLD_IDS}' else []
new = ['$INBOUND_REALITY_UUID', '$INBOUND_XHTTP_UUID']
combined = list(dict.fromkeys(old + new))
import json
print(json.dumps({'uuid': '$SQUAD_UUID', 'inbounds': combined}))
")
            RESP=$(api_patch "/api/internal-squads" "$NEW_INBOUNDS" || echo "")
            COUNT=$(echo "$RESP" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(len((d.get('response', {}).get('inbounds') or [])))
except Exception:
    print('?')
" 2>/dev/null)
            log "Squad $SQUAD_UUID now has $COUNT inbounds"
        done <<< "$SQUADS_TO_UPDATE"
    fi
fi

# ============================================================
step "L — Final verification"
# ============================================================

if ! $DRY_RUN; then
    echo ""
    echo "=== XRay ports ==="
    remote 'ss -tlnp | grep -E ":443|:8443"'

    echo ""
    echo "=== Caddy selfsteal (13 reverse_proxy) ==="
    CADDY_OK=0
    for SNI in "${ALL_SNI[@]}"; do
        RESULT=$(remote "curl -s -o /dev/null -w '%{http_code}' --resolve '${SNI}:9443:127.0.0.1' 'https://${SNI}:9443' -k --max-time 10" 2>/dev/null || echo "fail")
        echo "  $SNI: $RESULT"
        [[ "$RESULT" =~ ^(200|301|302|303|307|308|403)$ ]] && CADDY_OK=$((CADDY_OK + 1))
    done
    echo "  Passed: $CADDY_OK/${#ALL_SNI[@]}"

    echo ""
    echo "=== Matrix hosts verification ==="
    for HID in "${NEW_HOST_UUIDS[@]}"; do
        HOST_INFO=$(api_get "/api/hosts/${HID}" | python3 -c "
import json,sys
d = json.load(sys.stdin).get('response', {})
print(f\"{d.get('remark','?')} | hidden={d.get('isHidden')} disabled={d.get('isDisabled')}\")
" 2>/dev/null)
        echo "  $HID: $HOST_INFO"
    done

    echo ""
    echo "=== Connectivity checks ==="
    # Direct to new node
    if nc -z -w 5 "$NODE_IP" 443 2>/dev/null; then
        log "Direct $NODE_IP:443 — reachable"
    else
        warn "Direct $NODE_IP:443 — not reachable"
    fi

    # Via Relay
    if [[ -n "${RELAY_PORT:-}" ]]; then
        if nc -z -w 5 "$RELAY_IP" "$RELAY_PORT" 2>/dev/null; then
            log "Relay $RELAY_IP:$RELAY_PORT — reachable"
        else
            warn "Relay $RELAY_IP:$RELAY_PORT — not reachable"
        fi
    fi

    echo ""
    echo "=== Subscription check (random active user) ==="
    SUB_CHECK=$(api_get "/api/users?limit=1&start=0" | python3 -c "
import json, sys, urllib.request, ssl
d = json.load(sys.stdin)
users = (d.get('response', {}).get('users') or [])
short = (users[0].get('shortUuid') if users else None)
if not short:
    print('NO_USERS')
    raise SystemExit(0)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('${SUB_URL}/api/sub/' + short)
req.add_header('User-Agent', 'Happ/1.9.4 (iOS)')
body = urllib.request.urlopen(req, context=ctx, timeout=20).read().decode('utf-8', errors='replace')
sub = json.loads(body)
inner = sub[0] if isinstance(sub, list) and sub else sub
outbounds = inner.get('outbounds') or []
total = 0
for o in outbounds:
    vnext = (o.get('settings') or {}).get('vnext') or []
    if vnext and vnext[0].get('address') == '$NODE_IP':
        total += 1
print(f'short={short} new_node_outbounds={total} total_outbounds={len(outbounds)}')
" 2>&1)
    echo "  $SUB_CHECK"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}  Node ${NODE_NAME} (${NODE_IP}) deployment complete!${NC}"
echo "============================================================"
echo "  Country:          $COUNTRY_CODE ($FLAG)"
echo "  SSH:              ssh -p $SSH_PORT root@$NODE_IP"
echo "  Reality Public:   $PUBLIC_KEY"
echo "  Short IDs:        $SHORT_ID_1, $SHORT_ID_2"
echo "  Profile UUID:     $PROFILE_UUID"
echo "  Node UUID:        ${NODE_UUID:-unknown}"
echo "  Hosts created:    ${#NEW_HOST_UUIDS[@]} (all isHidden=true)"
if [[ -n "${RELAY_PORT:-}" ]]; then
echo "  Relay port:       $RELAY_IP:$RELAY_PORT → $NODE_IP:443"
fi
echo "  Template:         $TEMPLATE_UUID (${#NEW_HOST_UUIDS[@]} UUIDs added)"
echo "  Panel:            $PANEL_URL"
echo "============================================================"
echo ""
echo "MANUAL ACTIONS (if any):"
echo "  - Verify Happ client sees new outbounds (update subscription)"
echo "  - Monitor balancer.sh capacity alerts after adding node"
echo "  - Update monitor.sh if new node needs health checks"
echo "============================================================"
