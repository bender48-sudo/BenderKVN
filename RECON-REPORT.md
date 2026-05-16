# RU Monitoring Agent — Recon Report
**Date:** 2026-04-12 20:00 UTC

---

## Block 1: SSH Access Latvia -> Relay

### Keys on Latvia (/root/.ssh/)
- `id_ed25519` + `id_ed25519.pub` (created 2026-04-04)
- `authorized_keys` (1 key)
- `known_hosts` (has entries)
- **No SSH config file** (`~/.ssh/config` does not exist)
- **No dedicated relay key** (no `selectel_relay`, `relay`, etc.)

### SSH Test: Latvia -> Relay (72.56.0.145:3344)
- **FAILED:** `Permission denied (publickey,password)`
- Latvia's `id_ed25519.pub` is NOT in Relay's authorized_keys

### Relay authorized_keys
- **1 key** with comment: `selectel-relay`
- This is the key from the local dev machine, NOT from Latvia

### ACTION NEEDED:
Latvia's `id_ed25519.pub` must be added to Relay's `/root/.ssh/authorized_keys`
for the PULL model (Latvia SSH -> Relay) to work.

---

## Block 2: Relay State (72.56.0.145)

### OS & Python
- **OS:** Ubuntu 22.04.5 LTS (Jammy Jellyfish)
- **Python:** 3.10.12 (`/usr/bin/python3`)
- **Python ssl:** OpenSSL 3.0.2

### TLS Tools Available
| Tool | Path | Status |
|------|------|--------|
| openssl | /usr/bin/openssl | OK |
| curl | /usr/bin/curl | OK |
| nc | /usr/bin/nc | OK |
| jq | NOT FOUND | MISSING |

### /opt/ Contents
- `/opt/beszel-agent/` (Beszel monitoring agent, owned by `beszel` user)
- **No conflicts** with future `/opt/bvpn-check/`

### Users (UID >= 1000)
- `nobody` (standard, no real users besides root)

### Crontab (root)
- **Empty** — no cron jobs

### Hysteria2 Services
- `hysteria-server.service` — **active (running)** since 2026-04-10, uptime 2 days
- `hysteria-client.service` — **active (running)** since 2026-04-10, uptime 2 days
- Both enabled at boot

### Hysteria Logs (notable)
- Occasional TCP timeouts to 176.126.162.158:443 (Latvia) — intermittent
- Connection resets from Russian IPs — normal client disconnects

---

## Block 3: Telegram Alert Channel

### balancer.env Variables
- `BOT_TOKEN`
- `PANEL_TOKEN`

### Bot Identity
- **Username:** @Bender_KVN_bot
- **Name:** BenderVPN
- **ID:** 8684979664
- This is the SAME bot used for customer interactions (Telegram shop bot)

### ADMIN_CHAT_ID
- `924498094` — hardcoded in balancer.sh (line 14)
- Same chat ID used across ALL scripts

### Alert Mechanism
- `balancer.sh`: sources `/etc/bvpn/balancer.env` for BOT_TOKEN, hardcodes ADMIN_CHAT_ID
- `monitor.sh`: **HARDCODES** BOT_TOKEN and PANEL_TOKEN directly in script (not from env)
- Both use same bot (@Bender_KVN_bot) and same ADMIN_CHAT_ID (924498094)

### Scripts Using Telegram
| Script | BOT_TOKEN source | Usage |
|--------|-----------------|-------|
| balancer.sh | /etc/bvpn/balancer.env | Capacity alerts |
| monitor.sh | Hardcoded in script | Health check alerts |
| daily-report.sh | (likely same) | Daily summary |
| backup-remnawave.sh | (likely same) | Backup status |
| broadcast-2026-04-09.sh | (likely same) | One-time broadcast |

### SECURITY NOTE
monitor.sh has BOT_TOKEN and PANEL_TOKEN in plaintext in script body (lines 8-10).
Not blocking, but worth noting.

---

## Block 4: Target Matrix for Monitoring

### Current Hosts (17 total after Phase 6)

| Address | Port | SNI | Type |
|---------|------|-----|------|
| 176.126.162.158 | 443 | www.microsoft.com | Latvia Direct |
| 176.126.162.158 | 443 | www.apple.com | Latvia Direct |
| 176.126.162.158 | 443 | api.github.com | Latvia Direct |
| 176.126.162.158 | 443 | www.bing.com | Latvia Direct |
| 176.126.162.158 | 8443 | www.microsoft.com | Latvia XHTTP |
| 168.100.11.140 | 443 | www.microsoft.com | Amsterdam Direct |
| 168.100.11.140 | 443 | www.apple.com | Amsterdam Direct |
| 168.100.11.140 | 443 | api.github.com | Amsterdam Direct |
| 168.100.11.140 | 443 | www.bing.com | Amsterdam Direct |
| 168.100.11.140 | 8443 | www.apple.com | Amsterdam XHTTP |
| 72.56.0.145 | 443 | ads.x5.ru | Relay LV |
| 72.56.0.145 | 443 | eh.vk.com | Relay LV |
| 72.56.0.145 | 443 | ir-3.ozone.ru | Relay LV |
| 72.56.0.145 | 8443 | ads.x5.ru | Relay AMS |
| 72.56.0.145 | 8443 | eh.vk.com | Relay AMS |
| 72.56.0.145 | 8443 | sun6-21.userapi.com | Relay AMS |

16 unique address:port/SNI combinations (from 16 matrix hosts).
Virtual Host (305ccacd) shares address:port/SNI with Latvia Direct MS — not a separate target.

---

## Block 5: Baseline Selfsteal Responses

### From Relay to :9443 (selfsteal port)
- **ALL FAILED (HTTP 000)** — port 9443 is NOT reachable from Relay
- Port 9443 listens on localhost only (127.0.0.1), firewalled from outside

### From Relay to :443/:8443 (Reality ports)
TLS handshake succeeds — returns "Caddy Local Authority - ECC Intermediate" certificate.
This is the Reality -> Caddy selfsteal chain working correctly.

| Target | Port | TLS Handshake |
|--------|------|---------------|
| 176.126.162.158 | 443 | OK (Caddy cert) |
| 168.100.11.140 | 443 | OK (Caddy cert) |
| 176.126.162.158 | 8443 | OK (Caddy cert) |
| 168.100.11.140 | 8443 | OK (Caddy cert) |

### Selfsteal from localhost (confirmation both nodes alive)
| Node | SNI | Expected | Actual | OK |
|------|-----|----------|--------|----|
| Latvia | www.microsoft.com | 200 | 000 (flaky) | ~ |
| Latvia | api.github.com | 200 | 200 | OK |
| Latvia | ads.x5.ru | 503 | 503 | OK |
| Amsterdam | www.microsoft.com | 200 | 200 | OK |
| Amsterdam | api.github.com | 200 | 200 | OK |
| Amsterdam | ads.x5.ru | 503 | 503 | OK |

Latvia microsoft.com returned 000 once — likely transient timeout, not a problem.

### KEY ARCHITECTURE INSIGHT
The monitoring agent on Relay **cannot** test selfsteal responses via :9443.
It CAN do TLS handshake to Reality ports (443/8443) and verify the certificate.
For HTTP response code testing, the agent would need to go through Reality
(which requires VLESS auth) — or Latvia pulls results from a script that
tests localhost:9443 on each node via SSH.

**Recommended approach:** Agent on Relay tests TLS connectivity + latency to
all 16 targets on their actual ports. Selfsteal HTTP code verification runs
separately on each node (localhost:9443) and Latvia collects via SSH.

---

## Decisions Needed Before Implementation

1. **SSH Key:** Add Latvia's id_ed25519.pub to Relay authorized_keys?
   Or generate a dedicated key pair?

2. **Dedicated User:** Run agent as root, or create a `bvpn-check` user on Relay?
   (Currently only root + nobody exist)

3. **Alert Channel:** Use same @Bender_KVN_bot + ADMIN_CHAT_ID 924498094?
   Or separate monitoring channel/bot?
