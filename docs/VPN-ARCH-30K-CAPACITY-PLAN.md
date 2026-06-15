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
| **Node registry / assignment** | **Registry v1 DONE**; assignment **dry-run only** | [`ops/config/vpn_node_registry.yaml`](../ops/config/vpn_node_registry.yaml) + [`ops/vpn_node_selector.py`](../ops/vpn_node_selector.py); live sub gen unchanged |
| **Subscription strategy** | Static 6-outbound list for all users | **SUB-GEN-SELECTOR-INTEGRATION-001** OPEN — no per-device cohort in prod yet |
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

### 4.2 Node lifecycle (statuses)

Full lifecycle — see also §13 procurement policy:

```text
candidate → purchased_trial → staging → canary → active → draining / failed / decommissioned
```

| Status | Meaning |
|--------|---------|
| `candidate` | Shortlisted VPS/provider; **not purchased**; AUP/traffic/diversity reviewed |
| `purchased_trial` | Monthly or short test window paid; **not production**; refund window tracked |
| `disabled` | In inventory; never issued to users (e.g. NL awaiting A2/A4) |
| `staging` | Provisioned; internal smoke only — **no automatic promotion after purchase** |
| `canary` | Issued to small tester cohort (1–5%) via selector |
| `active` | Production delivery participant — only after acceptance + owner sign-off |
| `draining` | No new assignments; existing users migrate off |
| `failed` | Removed from assignment; alert + postmortem |
| `decommissioned` | Retired; historical record only |

**Rule:** purchase ≠ production. New spend always enters at `candidate` or `purchased_trial`, never `active`.

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
| 1 | **VPN-NODE-REGISTRY-001** | **DONE** — [`ops/config/vpn_node_registry.yaml`](../ops/config/vpn_node_registry.yaml) + [`ops/validate_vpn_node_registry.py`](../ops/validate_vpn_node_registry.py) |
| 2 | **SUB-GEN-SELECTOR-STRATEGY-001** | **DONE** — [`ops/vpn_node_selector.py`](../ops/vpn_node_selector.py) dry-run only |
| 2b | **SUB-GEN-SELECTOR-INTEGRATION-001** | **OPEN** — wire selector into live subscription generator (owner review) |
| 2c | **VPN-NODE-PROCUREMENT-POLICY-001** | **DONE** — owner-safe node purchase policy (§13) |
| 2d | **UX-AUTO-CONNECT-PRINCIPLE-001** | **DONE** — one-button BenderVPN Auto UX (§14) |
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

## 10. Node registry v1 (implemented)

**Canonical file:** [`ops/config/vpn_node_registry.yaml`](../ops/config/vpn_node_registry.yaml)

**Validation:** `python ops/validate_vpn_node_registry.py`

| Property | Value |
|----------|-------|
| Repo SoT | **Yes** — redacted metadata only |
| Drives live subscription generation | **No** — selector dry-run only; **SUB-GEN-SELECTOR-INTEGRATION-001** OPEN |
| `delivery_path_nodes` (current) | **1** — insufficient for 300/30k gates |
| 300 / 30k verdict | **NO-GO** until ≥2 proven paths + generator integration |

Example schema (non-canonical): [`examples/node-registry.example.yaml`](examples/node-registry.example.yaml).

---

## 11. Selector strategy v1 (dry-run)

**Module:** [`ops/vpn_node_selector.py`](../ops/vpn_node_selector.py)

**CLI:**

```bash
python ops/vpn_node_selector.py --cohort LAB_OWNER
python ops/vpn_node_selector.py --cohort PUBLIC_PROD
python ops/vpn_node_selector.py --cohort CANARY
```

| Property | Value |
|----------|-------|
| Reads registry | Yes — via validated load |
| Alters live subscription generation | **No** |
| Cohorts | `LAB_OWNER`, `OWNER_FF`, `PAID_BETA_MANUAL`, `PUBLIC_PROD`, `CANARY`, `FALLBACK_MANUAL` |
| `PUBLIC_PROD` while `delivery_path_nodes < 2` | **NO-GO** (hard gate; empty selection) |
| Next step | **SUB-GEN-SELECTOR-INTEGRATION-001** after owner review |

### 11.1 Shadow diff (integration — shadow stage)

**Module:** [`ops/vpn_sub_assignment_shadow.py`](../ops/vpn_sub_assignment_shadow.py) · **SUB-GEN-SELECTOR-INTEGRATION-001** (shadow stage) + **SUB-GEN-SHADOW-REPORT-001**

```bash
python ops/vpn_sub_assignment_shadow.py --cohort PUBLIC_PROD
python ops/vpn_sub_assignment_shadow.py --all --json
python ops/vpn_sub_assignment_shadow.py --cohort OWNER_FF --baseline-file <owner_export.json>
```

| Property | Value |
|----------|-------|
| Reads | Redacted registry + optional owner baseline file only |
| Changes live subscription generation | **No** — `dry_run=True`, `applied=False` always |
| Output | Redacted node IDs + group diffs (would_add / would_remove); no UUIDs/URLs/secrets |
| Baseline | Registry-derived (labelled "not live-confirmed") unless `--baseline-file` supplied |
| `apply_safe` flag | GO precondition only — **does not** authorise apply |
| Apply | **SUB-GEN-SELECTOR-APPLY-001** — separate, owner-reviewed, snapshot+rollback |

---

## 12. Document maintenance

- Revisit formula coefficients after first 1k active configs with real metrics.
- Link implementation PRs to backlog IDs in §8 — do not mark DONE without verify evidence.

---

## 13. Node procurement policy (owner-safe purchasing)

**ID:** VPN-NODE-PROCUREMENT-POLICY-001 · **Status:** **DONE** (architecture/docs) · **Does not authorize spend**

Before any VPS purchase, owner and ops must follow this policy so BenderVPN does **not** buy unsuitable nodes.

### 13.1 Purchase rules

| Rule | Requirement |
|------|-------------|
| **No long-term prepaid before acceptance** | Do not buy annual/multi-year plans until node passes [`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md) P0 and owner canary sign-off |
| **Monthly / test window first** | Default billing: monthly or short trial; track `procurement.refund_window_days` |
| **KVM / full root / dedicated IPv4** | Required — no shared NAT-only or panel-only access without root |
| **Traffic policy / fair-use** | Provider bandwidth cap and fair-use terms must be **documented and understood** — no vague “unlimited” without written policy |
| **AUP for VPN/proxy/tunneling** | Must confirm provider AUP **allows** VPN, proxy, or tunneling use — **reject** if prohibited or ambiguous |
| **Provider / DC / ASN diversity** | New node must improve or preserve geographic and network diversity vs existing prod — not same DC+AS as primary exit **and** backup |
| **No automatic production status** | Purchase creates `purchased_trial` or `staging` only — never `active` on invoice |
| **Owner purchase approval** | `procurement.purchase_approved_by_owner: true` before spend |

### 13.2 Reject node (do not buy, or decommission trial)

Reject or stop trial if **any** of:

| Reject reason | Examples |
|---------------|----------|
| VPN/proxy **prohibited** in AUP | “No proxy servers”, “no tunneling”, crypto-mining-only VPS |
| Traffic policy **vague** | “Fair use” with no Mbps/TB cap; sudden throttle history |
| **Bad IP reputation** | Recycled ranges with poor RU reachability; prior abuse listings |
| **Unstable network** | Packet loss, flap, or routing blackholes in pre-purchase probe |
| **Cannot support required scale** | No upgrade path, no additional IPs, no headroom for N+1 |

Record rejection in registry notes — do not retry same SKU without new evidence.

### 13.3 Registry procurement fields (proposal v1.1)

Schema extension — example in [`examples/node-registry.example.yaml`](examples/node-registry.example.yaml):

| Field | Purpose |
|-------|---------|
| `procurement.provider_label` | Redacted provider class (not live account name in git) |
| `procurement.billing_period` | `monthly` \| `trial_7d` \| `annual` (annual only after acceptance) |
| `procurement.refund_window_days` | Days to cancel trial without sunk cost |
| `procurement.traffic_policy` | Documented cap / fair-use summary |
| `procurement.vpn_allowed_by_aup` | `yes` \| `no` \| `unclear` — **no** or **unclear** blocks purchase |
| `procurement.provider_diversity_group` | Logical provider bucket for N+1 diversity |
| `procurement.datacenter_diversity_group` | DC/region bucket — must differ from saturated prod |
| `procurement.purchase_approved_by_owner` | Explicit owner OK before money |
| `procurement.long_prepaid_allowed` | `false` until acceptance PASS |
| `procurement.acceptance_status` | `pending` \| `passed` \| `failed` — gates promotion past staging |

**Not in git:** real provider account IDs, invoices, live IPs, credentials.

---

## 14. UX auto-connect principle (one button, no server choice)

**ID:** UX-AUTO-CONNECT-PRINCIPLE-001 · **Status:** **DONE** (architecture/docs) · **Product rule**

```text
Normal users must NOT choose a server, relay, region, or outbound in product UX.
They press one action — connect / get BenderVPN Auto — and receive a working profile.
Backend selector chooses cohort and node group; support may override; public UX stays one-click.
```

| Surface | User sees | User does NOT see |
|---------|-----------|-------------------|
| **Bot / Mini App** | “Подключить VPN”, “Получить BenderVPN Auto”, setup deeplink | Server list, NL/LV pick, relay #1 vs #2, turbo/wl-direct |
| **Portal / setup** | One config path, import routing pack, connect | Manual outbound selection, “choose fastest server” |
| **Happ (user)** | Import sub + **BenderVPN RU** routing; tap connect | Picking among six outbounds as product strategy |

| Role | May override assignment? |
|------|--------------------------|
| **Backend selector** | Yes — primary control plane |
| **Support / admin** | Yes — explicit fallback/manual profiles (`FALLBACK_MANUAL`, lab) |
| **End user (normal)** | **No** — no server picker in bot, portal, or marketing |

**Advanced / manual profiles** (relay2-only lab, v2rayN LV-direct, diagnostic urltest) are **support or owner tools** — hidden from public acquisition UX, not advertised as the product.

Even when internal profiles differ (lab vs prod vs fallback), **external product promise** remains: **one button → BenderVPN Auto**.

Aligns with product policy PT-11 (no user-facing NL/LV/relay pick) and [`VPN-ROUTING-PROFILE-STRATEGY.md`](VPN-ROUTING-PROFILE-STRATEGY.md) §10.

---

## 15. Backend selector principle (capacity-safe assignment)

**Complements:** §11 selector dry-run · **SUB-GEN-SELECTOR-INTEGRATION-001** (implementation OPEN)

| Layer | Responsibility |
|-------|----------------|
| **Backend selector** | Chooses **safe node group and cohort first** — before subscription JSON is emitted |
| **Subscription generator** | Emits outbounds **only** from backend-approved group for that device/cohort |
| **Client (Happ urltest / leastLoad)** | May operate **only inside** the backend-approved outbound set — tie-break / health, **not** capacity planning |

**Anti-patterns (forbidden as main strategy):**

- Sending **all nodes to all users** in one identical subscription blob.
- Relying on Happ to “randomly” load-balance across the entire fleet.
- Treating six relay outbounds as six capacity units when they share one exit.

**Current state:** dry-run selector exists; live subscription generation **unchanged**. **`PUBLIC_PROD` = NO-GO** while `delivery_path_nodes < 2`. Integration requires owner review — see **SUB-GEN-SELECTOR-INTEGRATION-001**.
