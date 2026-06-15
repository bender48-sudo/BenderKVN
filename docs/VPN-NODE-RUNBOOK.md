# VPN Node Runbook — Fast Production Node Bring-Up

**ID:** VPN-NODE-RUNBOOK-001 (documentation **DONE** · automation **OPEN**)  
**Date:** 2026-06-15  
**Purpose:** Repeatable template to raise a **production-capable** VPN node/relay and promote it through staging → canary → active.

**Consolidates:** [`DEPLOY.md`](DEPLOY.md) · [`THIRD-PROD-NODE-ONBOARDING.md`](THIRD-PROD-NODE-ONBOARDING.md) · [`NODE-POLICY-LV-NL.md`](NODE-POLICY-LV-NL.md) · [`CAPACITY-AND-FAILOVER-ROADMAP.md`](CAPACITY-AND-FAILOVER-ROADMAP.md) · [`RUNBOOK-LV-DOWN-NL-FAILOVER.md`](RUNBOOK-LV-DOWN-NL-FAILOVER.md)

**Safety:** No secrets in this doc. Tokens via vault / interactive env only ([`SECRETS.md`](SECRETS.md)).

---

## 0. Preconditions

| Check | Required |
|-------|----------|
| Owner approval for **new node spend** | Yes |
| Owner approval for **routing inclusion** | Yes — separate from provisioning |
| Node registry entry drafted | [`examples/node-registry.example.yaml`](examples/node-registry.example.yaml) |
| Rollback path documented | drain + template snapshot |
| Monitoring alert hygiene | [`MONITOR-FLAP-001`](CHECKPOINT-2026-06-12-CLIENT-NODES-MONITORING.md) acceptable |
| Not a substitute for multi-node architecture | Read [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) |

---

## 1. VPS / provider checklist

| Item | Guidance |
|------|----------|
| **Region / AS** | Diversify vs existing prod nodes (not same DC/AS as LV **and** NL) |
| **RAM** | ≥ 2 GiB (match LV/NL baseline) |
| **CPU** | ≥ 2 vCPU recommended for prod |
| **Ports** | :443 VPN, :8443 reserve/xhttp, SSH (non-default if policy requires) |
| **OS** | Ubuntu 22.04 LTS |
| **IPv4** | Stable public IPv4; document in registry (not in git) |
| **Abuse / reputation** | Avoid recycled IP ranges with poor RU reachability |
| **Billing** | Owner records provider + renewal date in registry |

Owner delivers to agent: **root SSH**, **public IP**, **region/provider label** — via secure channel, not commit.

---

## 2. OS / network / kernel checklist

| Step | Action | Verify |
|------|--------|--------|
| SSH hardening | Per-host key ([`SSH-KEY-INVENTORY`](SSH-KEY-INVENTORY.md) if present) | `ssh -o BatchMode=yes root@… true` |
| Time sync | `systemd-timesyncd` or chrony | `timedatectl` |
| Firewall | UFW / nft — only required ports public | external port scan from workstation |
| **BBR + fq** | `99-tcp-bbr.conf` if used on LV/NL | `sysctl net.ipv4.tcp_congestion_control` → `bbr` |
| DNS resolver | Node policy ([`RUNBOOK-NODE-DNS-RESOLVER.md`](RUNBOOK-NODE-DNS-RESOLVER.md)) | resolver smoke |
| Unattended upgrades | Security patches — owner policy | — |

---

## 3. Remna / Xray / Caddy / Reality / selfsteal

| Step | Action | Notes |
|------|--------|-------|
| 1 | Run `ops/deploy-node.sh` per [`DEPLOY.md`](DEPLOY.md) | Token via env — never in `ps` argv |
| 2 | Panel: node **connected**, inbound hosts created | 4× Direct :443 typical pattern |
| 3 | Caddy selfsteal | SNI set per TSPU policy — no github cluster |
| 4 | Reality / VLESS params | From panel — **not** copied from SafeVPN or other products |
| 5 | `injectHosts` | Add UUIDs via deploy script — **dry-run gate first** |
| 6 | Balancer pools | Include in `Intl_Direct` only after stealth split review |
| 7 | Template PATCH | **One change → probe → smoke** ([`VPN-INCIDENT-LESSONS-2026-05-25.md`](VPN-INCIDENT-LESSONS-2026-05-25.md)) |

**Forbidden without owner approval:** mass `--apply` · observatory panic · removing relay diversity blindly · making relay2-only production default.

Post-PATCH always:

```bash
python ops/vpn_verify_gate.py
python ops/probe_subscription.py
python ops/transport_mux_audit.py   # sample cohort
```

---

## 4. Monitoring integration

| Script | Host | Cadence |
|--------|------|---------|
| `selfsteal-monitor.py` | LV (and node-specific if applicable) | `*/5` |
| `ru-monitor.py` | LV | `*/5` |
| `monitor.sh` / `balancer.sh` | LV | 5 min / 1 h |
| Node-specific health | TBD — **NODE-SMOKE-MATRIX-001** | on deploy + cron |

Update registry: `health.monitor_status`, `health.last_smoke`.

Ensure new node does not reintroduce alert spam ([`MONITORING.md`](MONITORING.md)).

---

## 5. Node registry update

1. Add entry to registry (YAML v1 → future DB).
2. Set `status: staging`.
3. Assign `groups` (e.g. `RU_RELAY_CANARY` — not `ACTIVE` yet).
4. Record `capacity.reserved_headroom_percent` (default **40**).
5. Set `rollout.canary_percent: 0` until owner smoke PASS.

See [`examples/node-registry.example.yaml`](examples/node-registry.example.yaml).

---

## 6. Smoke test matrix (summary)

Full matrix: **NODE-SMOKE-MATRIX-001** · checklist: [`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md)

| Phase | Who | Tests |
|-------|-----|-------|
| **Staging** | Agent | TCP, Reality handshake, generated sub import, `vpn_verify_gate` |
| **Owner** | Owner | Happ connect, TG/Google/Gmail, RU direct sanity |
| **Canary 1–5%** | Internal cohort | 24–48 h reconnect + support silence |
| **Active** | Rollout manager | Weight increase + capacity snapshot |

---

## 7. Canary rollout

```text
staging → owner smoke PASS → canary 1–5% (internal) → 10–25% → active
```

| Gate | Requirement |
|------|-------------|
| Enter canary | All staging smokes PASS + owner sign-off |
| Increase weight | No elevated reconnect tickets; monitor clean |
| Promote to active | `delivery_path_nodes` math updated; post-inclusion audit scheduled |

Assignment must use **cohort engine** (future) — until then: **manual user list** only for canary.

---

## 8. Drain / rollback / decommission

### Drain (bad or retiring node)

1. Set registry `status: draining`.
2. Set `rollout.cohort_weight: 0` — no new assignments.
3. Remove from template `injectHosts` / selector pools (**snapshot first**).
4. Run `subscription_config_notify` for affected generation bump.
5. Monitor reconnect rate + support queue.
6. When active users on node ≈ 0 → `decommissioned`.

### Emergency rollback

1. Restore template from `.secrets/snapshots/template-before-*.json`.
2. Known paths: `patch_restore_6relay_stealth.py` (relay stealth restore — **owner approval only**).
3. Re-run verify gate + probe_subscription.
4. Postmortem doc within 24 h.

### Decommission

- Panel: disable hosts, disconnect node.
- Registry: `decommissioned` + reason.
- Do not delete historical records (support/debug).

---

## 9. Post-deploy acceptance

Use [`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md) — all **P0** boxes checked before canary.

Record in registry:

- `health.last_owner_test`
- `health.last_smoke`
- `rollout.owner_approval_notes`

---

## 10. Owner approval gates (summary)

| Gate | Owner must say |
|------|----------------|
| Provision VPS | Budget + region OK |
| Routing inclusion | Explicit approval for template PATCH / injectHosts |
| Canary → active | Review smoke + monitor logs |
| NL A2/A4 | Separate gate — [`VPN-ARCH-001`](BENDERVPN-MASTER-BACKLOG.md) |
| Prod relay selector reduction | **Not auto** — [`CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001`](CLIENT-STABILITY-HAPP-RELAY2-LAB.md) |
| Emergency rollback | Approve restore script + comms |

---

## 11. Related ops scripts (repo)

| Script | Use |
|--------|-----|
| `ops/deploy-node.sh` | Node bootstrap |
| `ops/vpn_verify_gate.py` | Post-change gate |
| `ops/probe_subscription.py` | Sub profile shape |
| `ops/transport_mux_audit.py` | Per-user outbound parity |
| `ops/nl_node_health_probe.py` | NL-specific (pre/post inclusion) |
| `ops/nl_reachability_probe_ru.py` | RU→NL TCP from LV |
| `ops/capacity_snapshot.py` | Soft cap / N+1 planning |
| `ops/patch_add_nl_intl_gated.py` | NL A2/A4 — **dry-run first** |
| `ops/happ_routing_directip_guard.py` | Routing regression guard |

---

## 12. What this runbook does NOT do

- Replace **SUB-GEN-SELECTOR-STRATEGY-001** (cohort assignment).
- Prove **30k capacity** by itself.
- Authorize prod changes without owner approval.
- Copy SafeVPN or third-party configs into production.
