# AUDIT-002 — VPN Architecture Map + Profile Restoration Dry Run

**Date:** 2026-06-09
**Mode:** dry-run only · no `--apply` · no prod mutation
**Prior:** [`AUDIT-2026-06-09-VPN-RELIABILITY.md`](AUDIT-2026-06-09-VPN-RELIABILITY.md)
**Branch:** `product-referral-cabinet-ui-v1` @ `4d837f1` (local, not pushed)
**Symptom:** VPN unstable — tunnel disconnects / reconnects (RC-1 82%, RC-2 68%, RC-4 55%)

---

## 1. Executive summary

Read-only inspection found a **configuration integrity bug** worse than simple relay2 SPOF:

| Layer | Expected (stealth split design) | **Actual prod (2026-06-09)** |
|-------|------------------------------|------------------------------|
| `injectHosts` | 6 (relay#1×3 + relay#2×3) or 10+ with NL | **3** (relay#2 only) |
| Live VLESS outbounds | Same as injectHosts | **3** (`proxy`, `proxy-2`, `proxy-3`) |
| `Intl_Direct` selector | Matches outbounds (e.g. 6 tags) | **6 tags** (`proxy`…`proxy-6`) |
| `Intl_Stealth` selector | Matches outbounds | **6 tags** |
| Catch-all rule | → `Intl_Direct` | **Present** → `Intl_Direct` |
| Observatory | Off | **Off** (correct) |
| Template DNS | DoH split OK | **OK** in template |
| Live sub DNS | DoH split OK | **BROKEN** (missing DoH per verify) |

**Random balancers reference `proxy-4`…`proxy-6` but only three outbounds exist.** This is a direct mechanism for connect failures, fallback churn, and perceived reconnect loops (RC-2).

**Recommendation:** **Candidate D** — minimal safe fix: restore **6 relay injectHosts** (relay#1 + relay#2), align **both** stealth selectors to `RELAY6_SELECTOR`, restore **DoH** on emitted sub, keep **observatory off**, keep **LV/NL direct out** for first test. **Not** full 14-host restore (B) on first apply.

**Owner approval required** before any `--apply`.

---

## 2. Safety constraints

| Rule | Status |
|------|--------|
| No `--apply` on any patch script | Honored |
| No Remna/Caddy/template writes | Honored |
| Panel GET read-only for template state | Used once |
| Dry-run: `patch_restore_14_relay_no_obs.py` (no flag) | Run |
| `patch_trim_injecthosts_relay_only.py` | Aborted (stealth split guard) |
| `latency_selector_autotrim.py` | Stopped at SSH probe fail (expected off-LV) |
| No secrets/UUIDs/sub URLs in this doc | Honored |

---

## 3. Files inspected

### Present and read

| File | Role |
|------|------|
| `docs/AUDIT-2026-06-09-VPN-RELIABILITY.md` | AUDIT-001 findings |
| `docs/VPN-INCIDENT-LESSONS-2026-05-25.md` | Observatory, relay, gen=20 canon |
| `docs/TRANSPORT-MUX-MATRIX.md` | Primary+alt transport policy |
| `docs/NODE-POLICY-LV-NL.md` | NL reentry / soft cap |
| `docs/VPN-ROUTING-GEO-GUARDRAILS.md` | Happ geo guardrails |
| `docs/RUNBOOK-RU-RELAY-EXPANSION.md` | relay#2 inventory |
| `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md` | Failover runbook |
| `ops/patch_restore_14_relay_no_obs.py` | Candidate B dry-run |
| `ops/patch_trim_injecthosts_relay_only.py` | Candidate C reference (aborts on stealth) |
| `ops/patch_intl_stealth_split.py` | Stealth split architecture |
| `ops/latency_selector_autotrim.py` | Selector trim (not injectHosts) |
| `ops/verify_vpn_balancer_profile.py` | Verify gate (permits broken 3-proxy) |
| `ops/verify_nl_failover_sub.py` | NL failover smoke |
| `ops/probe_balancer_catchall.py` | Legacy Super_Balancer smoke |
| `ops/balancer_selectors.py` | Selector canon |
| `ops/dns_split_config.py` | DoH split DNS |
| `ops/happ_routing_profile_ru.json` | Happ routing profile reference |
| `ops/generate_happ_routing_link.py` | Routing link helper |

### Requested but **not in repo**

| File | Substitute |
|------|------------|
| `patch_restore_prod_stealth_16.py` | `patch_intl_stealth_split.py` + VPN-AUD-279 docs |
| `patch_restore_wifi_lte_hybrid.py` | — |
| `patch_stealth_hybrid_restore.py` | — |
| `patch_emergency_*.py` | — |
| `patch_add_nl_gen101_gated.py` | `patch_add_nl_intl_gated.py` (not executed) |
| `probe_balancer_outbound_parity.py` | Manual parity check in §6 |
| `RUNBOOK-NL-SAFE-RETURN-GEN101-RU.md` | `NODE-POLICY-LV-NL.md` § P6-SCALE-NL-VERIFY |
| `RUNBOOK-VPN-TG-ONLY-RU.md` | `.cursor/skills/vpn-incident-tg-only-ru` (not expanded here) |
| `NL-REENTRY-CRITERIA.md` | `NODE-POLICY-LV-NL.md` |

---

## 4. Current architecture map

```
Happ (BenderVPN Auto)
  │  GET /api/sub/{shortUuid}  UA: Happ/1.9.4
  ▼
Caddy edge (p4n7q / k9x2m1 :8443)
  ▼
subscription-page HA (:3010/:3011 on AMS path)
  │  Happ UA filter (strip xhttp)
  ▼
Remna panel — templateJson (REMNA_TEMPLATE_UUID)
  │  injectHosts[N UUIDs] → N vless outbounds
  │  routing.rules + balancers
  │  dns.servers (split DoH)
  ▼
Client Xray core
  │  Intl_Stealth → TG/Meta (relay pool)
  │  Intl_Direct  → catch-all tcp,udp
  ▼
RU relay#1 72.56.0.145 ──┐
RU relay#2 46.173.28.252 ─┴→ LV / NL exit nodes
```

### Component table

| Component | Current state | Intended stable state | Risk |
|-----------|---------------|----------------------|------|
| **injectHosts** | **3** hosts, relay#2 only | **6** relay (both RU relays) | **P0** SPOF + selector skew |
| **Outbound tags** | `proxy`, `proxy-2`, `proxy-3` | `proxy`…`proxy-6` | **P0** balancer refs missing tags |
| **Intl_Stealth** | random × **6** selector | random × **6** aligned to injectHosts | **P0** TG/Meta path roulette |
| **Intl_Direct** | random × **6** + catch-all | same, aligned | **P0** reconnect on bad pick |
| **Super_Balancer** | Absent (stealth design) | Absent for stealth split | OK |
| **Catch-all** | Present → Intl_Direct | Present | OK (selector must match) |
| **Observatory** | Absent | **Stay absent** until staging | OK (avoid E1 closed-pipe) |
| **DNS / DoH** | Template OK; **live sub broken** | `dns_split_config.build_split_dns_config()` | **P1** RC-4 |
| **Transport mux** | 0% primary+alt (no LV/NL in sub) | Defer until relay stable | **P2** |
| **Autotrim cron** | May set `relay2_only` selector mode | Must not shrink injectHosts; probe from LV only | **P1** false trim off-LV |
| **Sub refresh notify** | `subscription_refresh.py` | After fix only, owner-approved | **P2** profile churn |

### Root cause chain (reconnect loops)

1. `injectHosts` trimmed to **3** (relay#2) — likely manual/autotrim-adjacent ops, not documented in this pass.
2. Balancers still use **RELAY6_SELECTOR** (6 tags).
3. `random` strategy picks `proxy-4`…`proxy-6` → **non-existent or stale outbounds** → connect fail → Happ reconnect.
4. Single relay IP amplifies SPOF when tag selection happens to hit live paths on degraded relay#2.

---

## 5. Candidate profile comparison

| Dimension | **A: Current live** | **B: 14-relay restore** | **C: 6-relay stealth** | **D: Minimal safe (recommended)** |
|-----------|---------------------|-------------------------|------------------------|-----------------------------------|
| **Script ref** | (prod) | `patch_restore_14_relay_no_obs.py` dry-run | `patch_trim` + stealth split | Custom: 6 inject + selector parity + DoH |
| **injectHosts** | 3 | **14** (LV+NL+RELAY) | **6** relay | **6** relay |
| **Proxy count** | 3 | ~14 | 6 | 6 |
| **relay#1** | 0 | Yes (3 RELAY→LV) | Yes ×3 | Yes ×3 |
| **relay#2** | 3 | Yes (3 RELAY→NL) | Yes ×3 | Yes ×3 |
| **LV/NL direct** | 0 | **4+4 direct** | No | **No** (phase 2) |
| **Failover** | None (SPOF) | **High** | **Good** (2 relays) | **Good** |
| **Catch-all** | Yes (broken selector) | Super_Balancer | Intl_Direct | Intl_Direct (fixed) |
| **Stealth split** | Yes (broken) | **No** (reverts architecture) | Yes | Yes |
| **Observatory** | Off | Off | Off | Off |
| **DoH** | Live broken | Restore w/ template | Restore | **Restore immediately** |
| **Sub size (est.)** | 5896 B | ~10–11 KB | ~7–8 KB | ~7–8 KB |
| **Ping UX** | Best (1 relay) | Worst (Happ pings 14) | Good | Good |
| **Reconnect impact** | **Worst** | Better path diversity | **Strong fix** | **Strong fix, lowest risk** |
| **TSPU/DPI risk** | High (one path) | Medium (many paths) | Medium (6 relay) | Medium |
| **Ops risk** | — | **High** (arch revert) | Medium | **Low** |
| **Rollback** | — | Snapshot + gen=20 restore | Snapshot | Snapshot current 3-host |
| **Confidence** | — | 70% stability / 40% ping | 85% | **88%** |

### Dry-run evidence

**B — `python ops/patch_restore_14_relay_no_obs.py` (no --apply):**

```
injectHosts 3 -> 14 (with RU Relay)
routing -> 7 rules
Dry-run. Apply with --apply
```

**C — `python ops/patch_trim_injecthosts_relay_only.py`:**

```
ABORT: stealth split profile (gen>=48). Do NOT apply relay-only injectHosts trim.
```

→ Candidate C must be implemented as **stealth-aware injectHosts restore** (6 UUIDs), not legacy trim script.

**Panel template read-only (2026-06-09):**

```
template_injectHosts: 3
stealth_split: True
observatory: False
Intl_Direct: random, selector_len 6
Intl_Stealth: random, selector_len 6
catch_all_rules: 1 → Intl_Direct
template dns_warnings: none
```

**Live sub sample:**

```
live_bytes: 5896
vless_tags: ['proxy', 'proxy-2', 'proxy-3']
balancers: Intl_Direct×6, Intl_Stealth×6
catch_all: ['Intl_Direct']
dns_servers: 4 (verify still flags missing DoH entry)
```

---

## 6. Dry-run artifact (no secrets)

### A — Current profile summary

| Field | Value |
|-------|-------|
| Architecture | Stealth split (gen≥48) |
| injectHosts | 3 |
| Outbound diversity | 1 IP (relay#2) |
| Selector parity | **FAIL** (6 vs 3) |
| Mux | FAIL |
| batch_risk | LOW |

### D — Proposed profile summary (target)

| Field | Value |
|-------|-------|
| Architecture | Stealth split (unchanged) |
| injectHosts | **6** (relay#1×3 + relay#2×3) |
| Intl_Stealth selector | `RELAY6_SELECTOR` (`proxy`…`proxy-6`) |
| Intl_Direct selector | `RELAY6_SELECTOR` (phase 1; NL deferred) |
| Catch-all | `tcp,udp` → `Intl_Direct` (unchanged) |
| Observatory | **Removed / absent** |
| DNS | `build_split_dns_config()` in templateJson.dns |
| LV/NL direct | **Not in injectHosts** (phase 2) |
| Est. sub size | ~7–8 KB |

### Diff summary (conceptual)

| Change | A → D |
|--------|-------|
| injectHosts count | 3 → **6** |
| relay#1 paths | 0 → **3** |
| Selector/outbound parity | **Broken → aligned** |
| Failover | SPOF → **dual relay** |
| DoH on live sub | Broken → **fixed** |
| Super_Balancer | — → still absent (by design) |
| Architecture family | stealth split → **same** |

---

## 7. Decision answers

| # | Question | Answer |
|---|----------|--------|
| 1 | Best stability / ping / failover balance? | **D (6-relay parity fix)** — fixes RC-1+RC-2 without 14-host ping noise or arch revert |
| 2 | Is relay#1 safe to reintroduce? | **Yes, with LV-vantage probe first.** Docs: relay#2 live 2026-05-29; autotrim `relay2_only` may reflect **off-LV false probe** (SSH keys missing on Windows). Run `relay_latency_probe.py` + `tspu_block_probe_ru.py` from **bvpn-lv** before apply |
| 3 | Keep LV/NL direct out for now? | **Yes** — defer until relay 6-host stable 48h + `transport_mux_audit` planned phase 2. See `NODE-POLICY-LV-NL.md` NL-VERIFY |
| 4 | Observatory disabled? | **Yes — stay off.** E1 closed-pipe; staging only per `RUNBOOK-OBSERVATORY-STAGING.md` |
| 5 | Restore DoH immediately? | **Yes** — template has split DNS; live sub missing DoH is RC-4. Apply with profile fix; verify `verify_vpn_balancer_profile` dns≠BROKEN |
| 6 | Restore Super_Balancer? | **No** for stealth split. Fix **Intl_Direct** catch-all + selector parity instead |
| 7 | First test profile? | **D on owner/test Telegram ID only** — not broad notify |
| 8 | Rollback path? | Snapshot `template-before-*` → re-apply current 3-host JSON; optional `sub_config_generation` bump only after owner OK |
| 9 | Must not touch? | See §9 |

---

## 8. Recommendation

### Primary: **Option 3 — Minimal relay#1 fallback + DoH + catch-all parity (Candidate D)**

Same operational target as Candidate C but explicitly scoped as **smallest fix** from current broken state.

**Why this addresses reconnect loops:**

1. **Eliminates selector/outbound mismatch** (6 tags ↔ 6 outbounds).
2. **Removes relay#2 SPOF** — relay#1 fallback paths return.
3. **Keeps observatory off** — avoids May `closed pipe` regression.
4. **Restores DoH** — reduces DNS-timeout disconnect class (RC-4).
5. **Preserves stealth split** — TG/Meta still use relay pool; no gen=20 arch revert risk from B.

**Why not B (14-relay) first:**

- Reverts to Super_Balancer / 14-host model conflicting with gen≥48 stealth split.
- Reintroduces LV/NL direct Happ ping noise and RU direct reachability risk (E2 lessons).
- Larger blast radius; harder rollback psychology.

**Why not do nothing:**

- Current state is **internally inconsistent** (6-selector / 3-outbound) — not a stable equilibrium.

---

## 9. What must not be changed (without owner + rollback)

- `burstObservatory` / `leastLoad` on prod
- `geosite:ru` / `geosite:category-ru` in routing or dns
- Removing **both** relays from injectHosts
- `patch_injecthosts_lv_direct_only` / `patch_injecthosts_no_relay`
- Mass `broadcast_refresh_sub.py` / `push_sub_config_generation_ams.py`
- Autotrim `--apply` from non-LV host while injectHosts broken
- User-facing NL/LV manual pick (product policy)

---

## 10. Owner / test-user rollout plan

### Pre-apply (ops, read-only)

1. From **bvpn-lv**: `python ops/relay_latency_probe.py`
2. `python ops/tspu_block_probe_ru.py` — both relays OK
3. `python ops/happ_geosite_guard.py`
4. Snapshot template to `.secrets/snapshots/template-before-6relay-restore-*.json`

### Apply (owner approval only — **not this audit**)

1. Restore **6 relay UUIDs** in `injectHosts` (panel hosts API read → pick relay#1×3 + relay#2×3 per `patch_trim_injecthosts_relay_only.py` logic, stealth-safe).
2. Set `Intl_Stealth` + `Intl_Direct` selectors to `RELAY6_SELECTOR`.
3. Ensure `templateJson.dns` = `build_split_dns_config()`.
4. Confirm observatory absent.
5. `happ_geosite_guard.py` → `vpn_verify_gate.py` subset.

### Post-apply verification

```bash
python ops/probe_subscription.py          # expect >3 proxies, both relay IPs
python ops/diagnose_happ_import.py        # batch_risk=LOW
python ops/probe_injecthosts_sub_parity.py # injectHosts == live proxy count
python ops/verify_vpn_balancer_profile.py # dns not BROKEN; proxy count matches
```

### Test-user only (48h)

1. Owner/test account: refresh Happ sub.
2. Collect Happ `access_log` 30 min — count outbound tag changes (flap rate).
3. Instagram + Telegram 15 min continuous use on **Wi‑Fi and LTE**.
4. Compare sub size (~7–8 KB) vs broken 5896 B.

### Broad rollout gate

- Test user clean 48h
- No `closed pipe` in error_log
- `relay_latency_probe` green from LV
- **Then** owner-approved notify batch (`SUB_REFRESH_NOTIFY_ENABLED`) — not mass broadcast

---

## 11. Rollback plan

| Step | Action |
|------|--------|
| 1 | Stop autotrim cron apply if running |
| 2 | Restore snapshot `template-before-6relay-restore-*.json` via panel PATCH (owner) |
| 3 | Verify 5896 B / 3-proxy state returns if needed |
| 4 | Do **not** notify all users until rollback verified on test user |

**No-go conditions (abort apply):**

- `happ_geosite_guard` fails
- Both relays fail RU probe
- Dry-run shows observatory would be enabled
- injectHosts / selector counts still mismatched after patch plan

---

## 12. Exact next implementation prompt (do not run now)

> **VPN profile restore — Candidate D — owner/test user only**
>
> Prereq: owner approval + AUDIT-002 accepted.
>
> 1. SSH to **bvpn-lv**; run `relay_latency_probe.py` + `tspu_block_probe_ru.py` (read-only).
> 2. Snapshot current template JSON.
> 3. Implement **stealth-safe 6-relay injectHosts restore** (new script or guarded patch — **not** `patch_trim_injecthosts_relay_only.py` on stealth).
> 4. Align `Intl_Stealth` + `Intl_Direct` to `RELAY6_SELECTOR`; ensure catch-all → `Intl_Direct`.
> 5. Apply `build_split_dns_config()` to template dns block.
> 6. `--apply` only after dry-run + owner OK.
> 7. Verify gate; test **one** owner Telegram ID; 48h soak.
> 8. No broadcast; no NL/LV direct; no observatory.
>
> **Stop if:** verify fails, relay probe fails, or test user flap rate worse than baseline.

---

## 13. Git status (PHASE 0)

```
Branch: product-referral-cabinet-ui-v1 @ 4d837f1 (local)
Ahead of origin: AUDIT-001 commit + policy/backlog commits (not pushed unless owner asks)
Uncommitted: .cursor/skills, guardrails, playwright artifacts, screenshots (unchanged)
```

---

**AUDIT-002 status:** complete (dry-run) · **Next:** owner approval → LV relay probe → Candidate D apply on test user
