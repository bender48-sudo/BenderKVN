# VPN Architecture — 30k Active Configs Capacity Plan

**ID:** VPN-ARCH-30K-CAPACITY-PLAN-001  
**Date:** 2026-06-15  
**Branch:** `product-referral-cabinet-ui-v1`  
**Status:** Architecture doc **DONE** · implementation **OPEN**  
**Mode:** development preparation · **no prod mutation**

**Related:** [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) · [`CAPACITY-AND-FAILOVER-ROADMAP.md`](CAPACITY-AND-FAILOVER-ROADMAP.md) · [`NODE-POLICY-LV-NL.md`](NODE-POLICY-LV-NL.md) · [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md) · [`VPN-ROUTING-PROFILE-STRATEGY.md`](VPN-ROUTING-PROFILE-STRATEGY.md) · [`CLIENT-STABILITY-HAPP-RELAY2-LAB.md`](CLIENT-STABILITY-HAPP-RELAY2-LAB.md)

---

## 1. Executive decision

```text
BenderVPN must NOT scale through “one lucky relay2-only profile”.

Target model: backend-controlled multi-node delivery architecture.
Each config/device receives a managed node group assignment.
Capacity, canary, drain, and rollback are system decisions — not Happ randomly
picking among outbounds in a static JSON blob.
```

**What relay2-only proved:** a **controlled lab/workaround** can stabilize one owner path ([`CLIENT-STABILITY-HAPP-RELAY2-LAB.md`](CLIENT-STABILITY-HAPP-RELAY2-LAB.md) report(8) PASS). That is **evidence**, not **launch architecture**.

**What it did not prove:** multi-geography delivery, N+1 capacity, canary rollout, drain, or support visibility at scale.

---

## 2. Current state (2026-06-15)

| Dimension | State | Evidence |
|-----------|-------|----------|
| **Live Auto profile** | Candidate **D** — relay-only×6 | relay #1×3 + relay #2×3 in `injectHosts`; **NL=0**, LV direct=0 |
| **Effective delivery geography** | **~1** (LV exit behind relays) | PROOF-001 + QUALITY-PROOF-001 |
| **`delivery_path_nodes`** | **< 2** | NL connected but **not** in normal Auto subs |
| **Relay #1** | Under suspicion (dial/open storms in lab) | report(6–7); relay2 lab mitigates locally only |
| **Relay2-only lab** | **LAB_OWNER** — PASS repeat soak | Must stay **non-production default** |
| **Happ DirectIp fix** | **Deployed** — do **not** rollback | `0258d00`, owner retest `0635067` |
| **Node bootstrap template** | **Partial** — `deploy-node.sh`, scattered docs | Unified runbook: [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md) |
| **Node registry / assignment** | **Missing** | No YAML/DB SoT; no cohort engine |
| **Subscription strategy** | Static 6-outbound list for all users | No per-device cohort assignment |
| **Monitoring for capacity** | Partial — flap tuned; cert digest OK | **MONITOR-CAPACITY-001** not implemented |
| **30k verdict** | **NO-GO** | See §5 launch gates |

---

## 3. Why relay2-only is not enough

| Claim | Reality |
|-------|---------|
| “Client works great” | True for **one lab profile** on **one relay path** |
| “We fixed stability” | Fixed **client-side routing leak** (DirectIp) + **path isolation** — not backend capacity |
| “Six outbounds = six nodes” | **False** — six relay outbounds can share **one LV exit** |
| “Relay diversity = capacity” | Relay #1 + #2 to same geography ≠ **two production delivery nodes** |
| “Safe to grow” | **NO** until `delivery_path_nodes ≥ 2` **and** registry + rollout exist |

Relay2-only belongs in group **`LAB_OWNER`** or **`FALLBACK_MANUAL`**, not **`RU_RELAY_ACTIVE`** production default.

---

## 4. Target architecture

### 4.1 Control plane vs data plane

```text
┌─────────────────────────────────────────────────────────────┐
│ CONTROL PLANE (AMS/LV ops + bot + portal + Remna API)       │
│  Node registry · Assignment engine · Sub generator          │
│  Capacity policy · Rollout manager · Support view           │
└──────────────────────────┬──────────────────────────────────┘
                           │ generates subs / routing / weights
┌──────────────────────────▼──────────────────────────────────┐
│ DATA PLANE (VPN nodes, relays, exits)                       │
│  LV · NL · RU relays · future nodes · staging/canary/active │
└─────────────────────────────────────────────────────────────┘
```

| Control plane component | Responsibility |
|-------------------------|----------------|
| **Node registry** | Inventory: id, region, role, status, groups, capacity, health |
| **Assignment engine** | Maps config/device → node group + cohort + weight |
| **Subscription generator** | Emits profile for client class (Happ / fallback / lab) |
| **Capacity policy** | Blocks assignment to overloaded / failed nodes |
| **Rollout manager** | staging → canary → active → drain → decommission |
| **Support view** | Shows user’s cohort, node group, last smoke, remediation |

### 4.2 Node statuses

| Status | Meaning |
|--------|---------|
| `disabled` | In inventory; never issued to users |
| `staging` | Provisioned; internal smoke only |
| `canary` | Issued to small tester cohort (1–5%) |
| `active` | Production delivery participant |
| `draining` | No new assignments; existing users migrate off |
| `failed` | Removed from assignment; alert + postmortem |
| `decommissioned` | Retired; historical record only |

### 4.3 Node groups (minimum)

| Group | Purpose |
|-------|---------|
| `RU_RELAY_ACTIVE` | Primary RU-facing relay delivery paths |
| `RU_RELAY_CANARY` | New or suspect RU relays under test |
| `INTL_DIRECT_ACTIVE` | Direct intl exits (e.g. LV/NL after gates) |
| `INTL_STEALTH_ACTIVE` | TG/IG/Meta and stealth-only paths |
| `FALLBACK_MANUAL` | Support emergency profiles |
| `LAB_OWNER` | Owner/lab profiles (relay2-only, etc.) — **not mass issue** |

### 4.4 Assignment model (target)

```text
one subscription/config = one device (policy)
each device has: assigned_node_group, cohort_id, rollout_weight
subscription JSON is generated FOR that assignment — not identical for everyone
```

| User class | Profile behavior |
|------------|------------------|
| Owner / lab | `LAB_OWNER` — relay2-only or experiment |
| F&F | Stable primary group + documented fallback |
| Paid beta ≤10 | Named cohort; manual override allowed |
| Public / growth | Only after capacity gates + canary pipeline |

**Anti-pattern (current):** “Here is a JSON with 6 outbounds; Happ leastLoad will figure it out.”

**Target:** backend decides **which** outbounds exist and **who** gets them.

---

## 5. Capacity model

### 5.1 Formula

```text
required_peak_mbps =
  active_configs
  × peak_concurrency_ratio
  × avg_mbps_per_active_connection
  × safety_factor
```

| Variable | Starter assumption (calibrate with ops) |
|----------|----------------------------------------|
| `active_configs` | Count from panel + policy definition |
| `peak_concurrency_ratio` | 0.30–0.50 at 10k accounts (see `COMMERCIAL-BACKLOG` §10.3) |
| `avg_mbps_per_active_connection` | 2–5 Mbps blended (video + browsing) |
| `safety_factor` | 1.3–1.5 (headroom) |

### 5.2 N+1 / N+2

| Principle | Rule |
|-----------|------|
| **N+1** | Survive loss of **one** active delivery node without service collapse |
| **N+2** | Target at **30k** active configs — plan spare capacity for rollout + failure overlap |
| **Per-node soft cap** | `USERS_PER_NODE = 50` heuristic ([`NODE-POLICY-LV-NL.md`](NODE-POLICY-LV-NL.md)) — tune with real metrics |

### 5.3 Launch gates

| Gate | Minimum architecture requirement |
|------|----------------------------------|
| **Owner / F&F** | One stable path acceptable with disclosed limits + fallback doc |
| **Small paid beta ≤10** | Manual cohort control + support fallback + billing gates |
| **300 active configs** | **`delivery_path_nodes ≥ 2`** verified in generated subs + node registry v1 + smoke matrix |
| **1k+ active configs** | **≥3** active delivery paths + monitoring capacity signals + drain runbook tested |
| **10k+ active configs** | Registry SoT + weighted assignment + automated health gates + canary pipeline |
| **30k active configs** | N+1/N+2 proven + fast node bootstrap + canary/drain/rollback automation + capacity dashboard |

**Current verdict:** **30k = NO-GO** until §5.3 rows for 300+ are met.

---

## 6. Required monitoring metrics (capacity)

| Metric | Use |
|--------|-----|
| Active configs / devices | Capacity numerator |
| Concurrent sessions (estimate) | Peak load |
| Per-node CPU / RAM / bandwidth | Overload detection |
| Per-node active user share | Balance verification |
| Reconnect rate / support tickets | Quality gate |
| Sub generation latency | Control plane health |
| Node smoke last_pass | Rollout gate |
| Alert noise rate | Trust gate ([`MONITOR-FLAP-001`](CHECKPOINT-2026-06-12-CLIENT-NODES-MONITORING.md)) |

**ID:** MONITOR-CAPACITY-001 — dashboard + alerts (implementation OPEN).

---

## 7. Risks and blockers

| Risk | Severity | Mitigation task |
|------|----------|-----------------|
| Single LV exit masked as 6 relays | P0 | SUB-GEN-SELECTOR-STRATEGY-001; count **geographic** exits |
| Relay2-only becomes silent default | P0 | Keep in `LAB_OWNER`; owner approval for prod selector |
| NL counted without inclusion proof | P0 | VPN-ARCH-001 A2/A4 controlled smoke only |
| No registry → manual PATCH roulette | P1 | VPN-NODE-REGISTRY-001 |
| No canary → blast radius | P1 | ROLLOUT-CANARY-DRAIN-001 |
| Happ client-side randomness | P1 | Assignment engine; stop identical global JSON |
| Relay #1 instability | P0 | Diagnosis path; PROD-SELECTOR only with owner OK |
| Monitoring false positives | P1 | MONITOR-FLAP-TUNE closeout before NL apply |

---

## 8. Implementation backlog (after this doc pack)

Order — do **not** skip registry/strategy before mass node adds:

| # | ID | Deliverable |
|---|-----|-------------|
| 1 | **VPN-NODE-REGISTRY-001** | SoT schema → repo YAML → later DB/admin |
| 2 | **SUB-GEN-SELECTOR-STRATEGY-001** | Cohort assignment + subscription generator rules |
| 3 | **VPN-NODE-RUNBOOK-001** (automation) | Script/checklist runner atop [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md) |
| 4 | **NODE-SMOKE-MATRIX-001** | Unified smoke runner per node |
| 5 | **MONITOR-CAPACITY-001** | Capacity metrics + alerts |
| 6 | **ROLLOUT-CANARY-DRAIN-001** | Weight/canary/drain automation |
| 7 | **ROUTING-PROFILE-RU-DIRECT-001** | Curated Happ routing pack + tests |
| 8 | **VPN-ARCH-001** | NL A2/A4 decision after monitoring + owner approval |
| 9 | Relay #1 | Diagnose / reduce / replace path |

**Explicitly not next:** blind relay2 prod default · blind NL `--apply` · rollback of fixed happRouting.

---

## 9. SafeVPN reference boundary

SafeVPN is a **routing reference only** — see [`VPN-ROUTING-PROFILE-STRATEGY.md`](VPN-ROUTING-PROFILE-STRATEGY.md).

Borrow concepts (UseIPv4, split DNS, private CIDR direct, sniffing, curated RU direct list).  
Do **not** copy credentials, endpoints, domain lists wholesale, or single-proxy architecture as capacity proof.

---

## 10. Document maintenance

- Update when `delivery_path_nodes` changes (post-inclusion audit).
- Revisit formula coefficients after first 1k active configs with real metrics.
- Link implementation PRs to backlog IDs in §8 — do not mark DONE without verify evidence.
