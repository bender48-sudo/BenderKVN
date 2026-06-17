# DESKTOP-RELAY1-SERVICE-REPAIR-DEPLOY-001 — Relay #1 Service Repair Attempt

**Task:** DESKTOP-RELAY1-SERVICE-REPAIR-DEPLOY-001
**Date:** 2026-06-17
**Mode:** Action-first affected-relay repair (scoped, rollbackable; ru-relay-1 only)
**Parents:** [`CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md) ·
[`CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md) ·
[`RELAY1-DRAIN-OR-RETEST-DECISION.md`](RELAY1-DRAIN-OR-RETEST-DECISION.md)
**Branch / HEAD baseline:** `product-referral-cabinet-ui-v1` @ `b3d3465`

> No LV/relay2/subscription/template/Remna/Caddy mutation. One scoped service restart
> on ru-relay-1 only. Endpoints redacted to `ep_<hash>:port`. No raw IPs/UUIDs/secrets.

---

## 1. Pre-repair snapshot (ru-relay-1, read-only)

- Backup dir (off-repo, on node): `/root/bender-backups/relay1-repair-20260617-204504/`
  (captured `listeners.txt`, service status; no xray config/unit existed to back up).
- Host up 48d, load ~0.1, RAM/disk healthy, time synced, firewall active (443/tcp, 8443/tcp, 443/udp, SSH).

**Decisive architecture finding — relay #1 is NOT an xray/REALITY node:**

| Aspect | Finding |
|--------|---------|
| `xray.service` | **not installed** ("could not be found") |
| docker / remnanode | none |
| caddy | inactive |
| `hysteria-server.service` | active (pid 633), **UDP :443** (QUIC entry) |
| `hysteria-client.service` | active (pid 327103), **owns TCP 443/8443/9443**, `tcpForwarding` to upstream |
| client.yaml keys | `server`, `auth`, `tls`, `tcpForwarding` (values not printed) |

This **diverges from `VPN-NODE-RUNBOOK.md`** (relays documented as Xray/Caddy/Reality/VLESS).
relay #1 is a **hysteria TCP-forwarding relay**: BenderVPN VLESS-over-TCP clients hit
relay TCP:443 → `hysteria-client` tunnels to a co-located upstream → exit.

---

## 2. Expected vs actual + upstream check

| Check | ru-relay-1 (actual) | Expected (runbook) |
|-------|---------------------|--------------------|
| Service owning :443 | hysteria (QUIC server + TCP forward client) | xray VLESS/REALITY |
| Transport | hysteria QUIC tunnel + TCP forward | TCP/REALITY |
| Upstream `ep_4b84b15b:443` reachability | ping 0% loss, ~0.017ms (co-located), TCP OPEN, UDP reachable | n/a |
| Forwarder health | **continuous "TCP forwarding error: connection reset by peer / timed out"** | clean |

Upstream is healthy/reachable, so the resets are not an unreachable-exit problem; they
occur on the forwarded streams themselves.

---

## 3. Chosen path

**PATH A attempted → fell back to PATH B.**

- The forwarder was **clearly unhealthy and stale** (34-day uptime, config last changed
  May 14, continuous forwarding errors) and the owner approved a scoped restart, so a
  restart of `hysteria-client` was justified to rule out a wedged local process.
- It did not resolve the resets → keep relay #1 degraded (PATH B); relay2-only owner
  canary remains the desktop workaround; escalate deeper fix.

---

## 4. Correction performed

| Item | Value |
|------|-------|
| Service touched | `hysteria-client.service` (ru-relay-1 only) |
| Command class | `systemctl restart hysteria-client` (unit `Restart=on-failure`, enabled) |
| Not touched | `hysteria-server` (UDP:443), LV, ru-relay-2, subscriptions, templates, Remna, Caddy |
| PID before → after | 327103 → 1307567 |
| Listeners after | TCP 443/8443/9443 rebound to new PID; local TCP:443 OPEN |
| Forwarding errors | **pre 8 / 120s → post 7 / 90s (no improvement)** |
| Established :443 | 1699 → 749 (churn from restart; reconnecting) |
| Rollback | none needed — service active/healthy; `Restart=on-failure` self-heals; idempotent re-restart available |

**Verdict: restart succeeded operationally but did NOT fix the dropouts.** Root cause is
upstream-app / QUIC-tunnel quality / relay design — not a stale local process.

---

## 5. Registry / policy update (`ops/config/vpn_node_registry.yaml`)

`ru-relay-1`:
- `repair_status: restarted_no_improvement`, `last_repair_ref: DESKTOP-RELAY1-SERVICE-REPAIR-DEPLOY-001`, `retest_required: true`
- `incident: true`, `exclude_from_desktop_canary: true` (kept)
- `exclude_reason`/`notes` updated: hysteria relay (no xray), upstream reachable, restart
  did not clear resets, deeper fix owner-gated. Status stays `active` (no unilateral live drain).

`ru-relay-2`: unchanged (read-only compare only).
`PUBLIC_PROD`: NO-GO (`delivery_path_nodes=1`).

---

## 6. Owner/staging desktop canary (workaround, unchanged & regenerated)

- Generator: `ops/generate_desktop_relay_path_canary.py` → `.local/desktop_relay_path_canary.{json,md}` (not committed).
- Excludes `ep_20e413bd` (relay #1, proxy/proxy-2/proxy-3); keeps `ep_d1a601f6` (relay #2,
  proxy-4/5/6); pins Intl_Direct + Intl_Stealth to relay #2; preserves stealth split +
  DirectIp guard; no geoip:ru / relay-IP / FallbackTag=direct / server picker.
- Build importable JSON: `ops/generate_happ_relay2_lab_profile.py --from-json <owner_sub.json> --write-json .local/desktop_relay2_only.json`.
- Rollback: switch back to normal "BenderVPN Auto".

---

## 7. Tests / smoke

| Check | Result |
|-------|--------|
| `validate_vpn_node_registry.py` | PASS (no secrets) |
| `vpn_node_smoke_matrix.py --markdown` | relay-1 FAIL/excluded; PUBLIC_PROD NO-GO |
| `vpn_selector_apply_gate.py --cohort PUBLIC_PROD` | NO-GO (expected) |
| `generate_desktop_relay_path_canary.py` | tokens correct; prod default unchanged |
| pytest (analyzer + canary + relay1 policy) | 33 passed |
| `git diff --check` | clean |
| post-repair remote health | service active, listeners up, upstream reachable |

---

## 8. Gate status

| Gate | Status |
|------|--------|
| Desktop stability | OPEN — restart did not fix; relay2-only canary is the path to a stable owner test |
| Relay #1 | DEGRADED — hysteria forwarder resets persist; restart ineffective; needs rebuild/upstream fix (owner-gated) |
| Owner relay-path canary | READY |
| PUBLIC_PROD | NO-GO (`delivery_path_nodes=1`) |
| 300 / 30k | NO-GO |

---

## 9. Owner next action — choose ONE

- **`RUN OWNER RELAY2-ONLY DESKTOP CANARY 15 MIN`** — import the relay-2-only canary and run a
  10–15 min long-session test (recommended immediate stability path).
- **`APPROVE DEEP RELAY1 REBUILD`** — authorize rebuilding ru-relay-1 to the documented
  xray/REALITY design (or a controlled upstream/QUIC-tunnel investigation) to restore it as a
  second healthy delivery path.

> Desktop PASS NOT claimed. 300/30k GO NOT claimed.
