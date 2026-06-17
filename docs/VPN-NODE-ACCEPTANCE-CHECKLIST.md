# VPN Node Acceptance Checklist

**ID:** NODE-SMOKE-MATRIX-001 companion (operational checklist)
**Date:** 2026-06-15
**Use with:** [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md) · [`examples/node-registry.example.yaml`](examples/node-registry.example.yaml)

Mark **PASS / FAIL / N/A**. **P0** items block canary. Record evidence links in registry — not raw secrets.

**Node ID:** _______________ **Date:** _______________ **Operator:** _______________

---

## 0. Procurement (before VPS pay — P0)

**Policy:** [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) §13 · **VPN-NODE-PROCUREMENT-POLICY-001**

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 0.1 | P0 | Registry `candidate` row drafted with procurement fields | ☐ | ☐ | ☐ | |
| 0.2 | P0 | **Monthly / test billing** — no long-term prepaid before acceptance | ☐ | ☐ | ☐ | |
| 0.3 | P0 | KVM, full root, dedicated IPv4 confirmed | ☐ | ☐ | ☐ | |
| 0.4 | P0 | Traffic policy documented (Mbps/TB / fair-use) | ☐ | ☐ | ☐ | |
| 0.5 | P0 | AUP allows VPN/proxy/tunneling (`vpn_allowed_by_aup: yes`) | ☐ | ☐ | ☐ | Reject if no/unclear |
| 0.6 | P0 | Provider + DC/ASN diversity vs existing prod | ☐ | ☐ | ☐ | |
| 0.7 | P0 | Owner purchase approval recorded | ☐ | ☐ | ☐ | |
| 0.8 | P0 | **No auto-promote to active** on purchase — enter `purchased_trial` / `staging` only | ☐ | ☐ | ☐ | |

---

## 1. Provisioning

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 1.1 | P0 | VPS meets region/AS diversification vs existing prod | ☐ | ☐ | ☐ | |
| 1.2 | P0 | Ubuntu 22.04+, SSH key-only access | ☐ | ☐ | ☐ | |
| 1.3 | P0 | Required ports open (:443, SSH; :8443 if used) | ☐ | ☐ | ☐ | |
| 1.4 | P1 | BBR/fq enabled if policy requires | ☐ | ☐ | ☐ | |
| 1.5 | P0 | Entry added to node registry (`staging`) | ☐ | ☐ | ☐ | |

---

## 2. Security

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 2.1 | P0 | No secrets committed to git | ☐ | ☐ | ☐ | |
| 2.2 | P0 | Panel/API tokens not logged | ☐ | ☐ | ☐ | |
| 2.3 | P1 | Firewall default deny except service ports | ☐ | ☐ | ☐ | |
| 2.4 | P1 | SSH from restricted keys/inventory | ☐ | ☐ | ☐ | |

---

## 3. Network

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 3.1 | P0 | Public IPv4 reachable on VPN port | ☐ | ☐ | ☐ | |
| 3.2 | P0 | DNS resolver policy applied on node | ☐ | ☐ | ☐ | |
| 3.3 | P1 | RU reachability probe PASS (if RU-facing relay) | ☐ | ☐ | ☐ | `nl_reachability_probe_ru.py` pattern |
| 3.4 | P1 | Latency within gate (document threshold) | ☐ | ☐ | ☐ | |

---

## 4. Remna / Xray / Caddy

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 4.1 | P0 | Node **connected** in panel | ☐ | ☐ | ☐ | |
| 4.2 | P0 | Inbound hosts created (expected count) | ☐ | ☐ | ☐ | |
| 4.3 | P0 | Selfsteal/Caddy healthy (no flap spam) | ☐ | ☐ | ☐ | |
| 4.4 | P0 | `injectHosts` updated (dry-run reviewed) | ☐ | ☐ | ☐ | |
| 4.5 | P0 | `vpn_verify_gate.py` PASS | ☐ | ☐ | ☐ | |

---

## 5. Generated subscription

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 5.1 | P0 | `probe_subscription.py` — expected outbound count/shape | ☐ | ☐ | ☐ | |
| 5.2 | P0 | New node appears in smoke cohort sub (if inclusion goal) | ☐ | ☐ | ☐ | |
| 5.3 | P1 | `transport_mux_audit.py` — sample users match template | ☐ | ☐ | ☐ | |
| 5.4 | P0 | Stealth split preserved (TG/IG via stealth path) | ☐ | ☐ | ☐ | |

---

## 6. Happ import (desktop)

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 6.1 | P0 | Sub imports without “0 servers” | ☐ | ☐ | ☐ | |
| 6.2 | P0 | TUN connects ≤ reasonable time | ☐ | ☐ | ☐ | |
| 6.3 | P0 | **BenderVPN RU** routing profile imported | ☐ | ☐ | ☐ | |
| 6.4 | P1 | No DirectIp leak to proxy server IPs | ☐ | ☐ | ☐ | `happ_routing_directip_guard.py` |

---

## 7. Mobile import (if applicable)

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 7.1 | P1 | Happ iOS or Android import PASS | ☐ | ☐ | ☐ | [`CLIENT-STABILITY-MOBILE-SMOKE.md`](CLIENT-STABILITY-MOBILE-SMOKE.md) |
| 7.2 | P1 | LTE handoff soft PASS | ☐ | ☐ | ☐ | |
| 7.3 | P2 | Lock/wake quick check | ☐ | ☐ | ☐ | |

---

## 8. Routing sanity

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 8.1 | P0 | Private/system CIDR → direct (no VPN loop) | ☐ | ☐ | ☐ | |
| 8.2 | P0 | RU/domestic sites → direct as designed | ☐ | ☐ | ☐ | |
| 8.3 | P0 | **`geoip:ru` NOT in DirectIp** (regression) | ☐ | ☐ | ☐ | Do not rollback fixed happRouting |
| 8.4 | P1 | Intl sites exit via expected selector | ☐ | ☐ | ☐ | |

---

## 9. User traffic smoke

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 9.1 | P0 | Telegram loads | ☐ | ☐ | ☐ | |
| 9.2 | P0 | Google / Gmail loads | ☐ | ☐ | ☐ | |
| 9.3 | P1 | Instagram / Meta (stealth path) | ☐ | ☐ | ☐ | |
| 9.4 | P1 | ipinfo / ifconfig shows expected exit class | ☐ | ☐ | ☐ | |

---

## 10. Sleep / wake (desktop)

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 10.1 | P1 | 10–30 min sleep → resume without reconnect storm | ☐ | ☐ | ☐ | CLIENT-SMOKE-001 |
| 10.2 | P1 | Export Happ report **before** switching VPN | ☐ | ☐ | ☐ | [`CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md`](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md) |

---

## 11. Monitoring

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 11.1 | P0 | Node monitored (selfsteal / ru-monitor as applicable) | ☐ | ☐ | ☐ | |
| 11.2 | P0 | No new alert spam after add | ☐ | ☐ | ☐ | |
| 11.3 | P1 | Cert digest / anti-flap behavior unchanged | ☐ | ☐ | ☐ | |

---

## 12. Capacity

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 12.1 | P0 | `delivery_path_nodes` count updated honestly | ☐ | ☐ | ☐ | |
| 12.2 | P1 | `capacity_snapshot.py` within soft cap | ☐ | ☐ | ☐ | |
| 12.3 | P1 | Headroom ≥ reserved % in registry | ☐ | ☐ | ☐ | |
| 12.4 | P0 | `procurement.acceptance_status: passed` before canary | ☐ | ☐ | ☐ | |

---

## 13. Rollback

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 13.1 | P0 | Template snapshot taken before apply | ☐ | ☐ | ☐ | |
| 13.2 | P0 | Rollback script/path identified | ☐ | ☐ | ☐ | |
| 13.3 | P0 | Owner notified of generation bump plan | ☐ | ☐ | ☐ | |

---

## 13a. Independent exit path (INDEPENDENT_EXIT_PATH_V1 — P0 for capacity count)

Required before a node can count toward `independent_exit_paths` / `delivery_path_nodes`.
See [`NEW-INDEPENDENT-EXIT-PATH-2026-06-17.md`](NEW-INDEPENDENT-EXIT-PATH-2026-06-17.md).

| # | P | Check | PASS | FAIL | N/A | Notes |
|---|-----|-------|------|------|-----|-------|
| 13a.1 | P0 | `path_role: exit` (not relay frontend) | ☐ | ☐ | ☐ | |
| 13a.2 | P0 | Egress token DISTINCT from every existing exit + relay upstream | ☐ | ☐ | ☐ | `ep_<hash>` only |
| 13a.3 | P0 | **No** `shared_upstream_group` with existing relays/exits | ☐ | ☐ | ☐ | shared = counts as 1 |
| 13a.4 | P0 | `architecture_compliance: compliant` (real exit stack) | ☐ | ☐ | ☐ | |
| 13a.5 | P0 | Generator CANARY preview includes the node | ☐ | ☐ | ☐ | synthetic overlay |
| 13a.6 | P0 | Controlled A2/A4 traffic smoke PASS (owner) | ☐ | ☐ | ☐ | then `delivery_path_eligible=true` |

---

## 14. Sign-off

| Role | Name | Date | Decision |
|------|------|------|----------|
| Agent / ops | | | staging complete ☐ |
| Owner | | | canary approved ☐ / active approved ☐ |

**Registry updates:** `health.last_smoke` · `health.last_owner_test` · `status` · `rollout.canary_percent` · `procurement.acceptance_status`
