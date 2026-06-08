# AUDIT-001 — BenderVPN VPN Reliability Diagnostic

**Date:** 2026-06-09
**Mode:** read-only diagnostic · no patches · no prod mutation
**Symptom:** user reports VPN feels unstable — tunnel disconnects and reconnects repeatedly
**Branch:** `product-referral-cabinet-ui-v1` @ `a38a0a3`
**Backlog:** VPN-REL-001 · roadmap AUDIT-001

---

## 1. Executive summary

Live read-only probes show the **subscription profile has regressed** from the documented multipath design (14–18 LV/NL/RELAY outbounds, gen≈20) to a **minimal relay2-only profile**:

| Metric | May 2025 (post-fix) | **2026-06-09 (today)** |
|--------|---------------------|-------------------------|
| Sub size | ~10–11 KB | **5896 B** |
| VLESS proxies | 14–16 tcp | **3** |
| Node mix | LV + NL + RELAY#1 + RELAY#2 | **RELAY#2 only** (`46.173.28.252`) |
| `Super_Balancer` | present (various gens) | **MISSING** |
| Catch-all rule | expected | **0 rules** |
| `burstObservatory` | was present (Phase 3) | **absent** (good for closed-pipe) |
| Happ `batch_risk` | LOW (after xhttp trim) | **LOW** |
| Transport mux | primary+alt OK | **FAIL** (0/3 users) |

**Most likely explanation for reconnect loops:** the client profile is a **single-path / single-relay SPOF** with **random balancer strategy** across few outbounds and **no health-check observatory**, so when relay#2 or one path degrades (TSPU, relay load, ISP), Happ/Xray **cycles connections** without usable failover to LV/NL/relay#1.

**Ruled out today (by probes):**

- Subscription edge down (HTTP 200, ~0.22s)
- xhttp `UnknownContentType` batch failure (xhttp=0, batch_risk=LOW)
- `burstObservatory` closed-pipe ping storm (**absent**)
- Content-Type wrong for Happ

**Not ruled out (needs user Happ logs + relay health):**

- Per-user cached old sub with historical `leastLoad` flapping (proxy-6/7/8 pattern, May logs)
- Relay#2 TCP/TLS instability from RU vantage
- DPI/TSPU on the only remaining path

**Recommendation:** **do not PATCH routing in panic.** Owner-approved Phase 2 should restore **multipath failover** (relay#1 + relay#2 + exit paths per policy) while keeping observatory off until staging proves no `closed pipe`. See §11 and §15.

---

## 2. Safety constraints used

| Constraint | Honored |
|------------|---------|
| No `ops/patch_*`, `restore_*`, `emergency_*` | Yes |
| No deploy / restart / service mutation | Yes |
| No mass sub refresh / broadcast | Yes |
| No Remna/Caddy/template writes | Yes |
| No Semgrep | Yes |
| Probes: read-only GET + panel read API only | Yes |
| Secrets redacted in this doc | Yes |

---

## 3. Script classification table

Inspected `ops/*` matching probe/verify/audit/check/diag/sub/happ/routing/failover/panel patterns plus all `patch_*` (forbidden). **Executed only category 1–3.**

| Script | Category | Read-only? | Safe to run? | Why / notes |
|--------|----------|------------|--------------|-------------|
| `probe_subscription.py` | 3 remote read-only probe | Yes | **Yes** | GET panel users + Happ sub URL; no writes |
| `diagnose_happ_import.py` | 3 remote read-only probe | Yes | **Yes** | Fetches sub; simulates Happ batch parse |
| `verify_vpn_balancer_profile.py` | 3 remote read-only probe | Yes | **Yes** | GET sub; validates balancer shape |
| `transport_mux_audit.py` | 3 remote read-only probe | Yes | **Yes** | Samples users' subs; read-only |
| `probe_users_sub_sample.py` | 3 remote read-only probe | Yes | **Yes** | Sample N users sub bytes/proxy count |
| `probe_injecthosts_sub_parity.py` | 3 remote read-only probe | Yes | **Yes** | Compares template injectHosts vs live sub |
| `probe_balancer_catchall.py` | 3 remote read-only probe | Yes | **Yes** | Public monitor sub URL GET |
| `happ_geosite_guard.py` | 2 local parser/audit | Yes | **Yes** | Scans template JSON in repo/snapshot |
| `diagnose_speed.py` | 3 remote read-only probe | Yes | **Yes** | Template + live sub analysis; no writes |
| `drift-check.py` | 3 remote read-only probe | Yes | **Caution** | SSH md5 compare only; not run (heavy SSH) |
| `relay_latency_probe.py` | 3 remote read-only probe | Yes | **Caution** | SSH to relays; not run (needs LV vantage) |
| `subscription_load_probe.py` | 4 load | No | **No** | Load test |
| `pg_stampede_load_probe.py` | 4 load | No | **No** | DB load |
| `panel_refresh_load_probe.py` | 4 load | No | **No** | Panel load |
| `broadcast_refresh_sub.py` | 5 mutation | No | **No** | Mass Telegram broadcast |
| `push_sub_config_generation_ams.py` | 5 mutation | No | **No** | Writes AMS SQLite |
| `patch_*` (51 files) | 5 patch/mutation | No | **No** | Template/panel PATCH |
| `patch_restore_14_relay_no_obs.py` | 5 patch/mutation | No | **No** | Applies template restore |
| `patch_burst_observatory.py` | 5 patch/mutation | No | **No** | Enables observatory |
| `patch_trim_injecthosts_relay_only.py` | 5 patch/mutation | No | **No** | Trims to relay-only hosts |
| `deploy-*.ps1/sh` | 6 deploy | No | **No** | Deploy/restart |
| `generate_xhttp_recovery_url.py` | 3 read + panel GET | Mostly | **Caution** | Panel read; no apply |
| `ru_bypass_routing.py` | 5 patch (with `--apply`) | Dry-run OK | **No apply** | Template mutation if `--apply` |
| `freeze_ams_node.py` | 5 patch | No | **No** | Node freeze |
| `check_balancer.py` | 3 remote read | Yes | **Yes** | Not run; optional |
| `probe_dns_leak.py` | 3 probe | Yes | **Caution** | May need live sub |
| `diagnose_throughput.py` | 3 probe | Yes | **Caution** | Heavier; not run |
| `vpn_verify_gate.sh` | 3 orchestration | Yes | **Yes** | Runs multiple probes |
| `setup_verify_service.py` | 6 service | No | **No** | Service-side |

---

## 4. Incident timeline

### Known confirmed incidents (docs)

| Date | Event | Symptom | Resolution / state |
|------|-------|---------|-------------------|
| **2026-05-25** | Template PATCH series gen 13→20 | `closed pipe`, IG/TG dead, «0 servers» | `patch_restore_14_relay_no_obs` — 14 hosts, no observatory |
| **2026-05-25** | xhttp in Happ sub | `batch_risk=HIGH`, Happ batch count=0 | Happ UA filter; xhttp stripped from Happ sub |
| **2026-05-25** | `burstObservatory` re-applied (Phase 3) | Risk of ping-on-connect | Interval 30s, gstatic probe — **conflicts with E1 lessons** |
| **2026-05-24** | Happ import regression (owner logs) | `UnknownContentType` → 0 servers → 1 custom profile | Documented in `CODERABBIT-AUDIT-PROMPT` |
| **2026-05-24** | access_log proxy-6/7/8 **flapping** | VPN «on» but slow/dead feeling | leastLoad/observatory era |
| **2026-05-29** | relay#2 live `46.173.28.252` | Second RU path | Q120 — 14 injectHosts at gen=44 per runbook |
| **2026-05-30+** | VPN-AUD stealth/relay-NL patches | 16-path profiles, trim relay-only for ping UX | `patch_trim_injecthosts_relay_only.py` |
| **2026-06-09** | **This audit** | User reconnect report | Live sub = **3× relay2 only**, mux FAIL |

### Recent repo changes (git, VPN-related)

```
73b1863 ops: close phase 17 — help_connect, P4-DNS, BBR, staging
91cc346 ops: close phase 16 — VPN-AUD-282/283/310
5ed74fa fix: VPN-AUD-281 relay-NL inject hidden for 16-path live sub
35b85af ops: VPN-AUD-279 — relay-NL :443 in inject (16-path stealth-safe)
daa8524 ops: phase 13 NL scale — health probe, relay-NL disable
```

### Areas with **no visibility** (gaps)

- Per-user Happ `error_log` / `access_log` for **current** report (not in repo)
- Relay#2 live CPU/mem/conntrack from RU vantage (relay probe not run)
- LV/NL node health right now (SSH timeout noted in May audits)
- Whether affected user refreshed sub after last `sub_config_generation` push
- Panel template **generation number** on prod (not fetched in this audit)

---

## 5. Architecture map

```
┌─────────────┐     subscription URL      ┌──────────────────────────────────┐
│ Happ client │ ─────────────────────────►│ Caddy edge (k9x2m1 / p4n7q)     │
│ BenderVPN   │   GET /api/sub/{shortUuid}  │ :8443 TLS                        │
│ Auto profile│   UA: Happ/1.9.4            └──────────────┬───────────────────┘
└─────────────┘                                            │
                                                           ▼
                              ┌────────────────────────────────────────────┐
                              │ subscription-page / sub HA (:3010/:3011)   │
                              │ Happ UA filter (strip xhttp for Happ)        │
                              └──────────────┬─────────────────────────────┘
                                             │
                                             ▼
                              ┌────────────────────────────────────────────┐
                              │ Remna panel (AMS) — template + injectHosts   │
                              │ REMNA_TEMPLATE_UUID, per-user shortUuid      │
                              └──────────────┬─────────────────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              ▼                              ▼                              ▼
     ┌────────────────┐           ┌────────────────┐            ┌────────────────┐
     │ RU relay#1     │           │ RU relay#2     │            │ LV / NL exit   │
     │ 72.56.0.145    │           │ 46.173.28.252  │            │ 176.126… / NL  │
     │ :443           │           │ :443           │            │ Direct + relay │
     └────────────────┘           └────────────────┘            └────────────────┘
              │                              │                              │
              └──────────────────────────────┴──────────────────────────────┘
                                             │
                                             ▼
                              ┌────────────────────────────────────────────┐
                              │ Xray routing + balancers in sub JSON       │
                              │ Intl_Direct / Intl_Stealth / Super_Balancer│
                              │ DNS split, RU bypass rules, Happ routing   │
                              └────────────────────────────────────────────┘
```

### Component reference

| Component | Role | Key files / functions | Reconnect risk |
|-----------|------|----------------------|----------------|
| Sub URL resolution | Bot → user link | `bot_src/subscription_resolve.py` | Low (URL stable) |
| Sub edge | TLS + route to sub backend | `ops/site_urls.py`, Caddy on LV | Low (200 OK today) |
| Sub generation | Template + injectHosts → JSON | Remna panel API, `REMNA_TEMPLATE_UUID` | **High** — profile collapsed |
| Happ UA filter | Strip xhttp for Happ | sub-page / HA layer | Low today (xhttp=0) |
| Balancer | Outbound selection | Template `routing.balancers` | **High** — random, no catch-all |
| Observatory | Health ping | `burstObservatory` in template | **Med historical** — absent today |
| injectHosts | Multi-outbound expansion | Panel hosts API, patch scripts | **High** — only 3 hosts |
| RU relay#2 | RU → exit path | `46.173.28.252`, `patch_add_relay2_vpn.py` | **High SPOF** — only path in live sub |
| RU relay#1 | Backup RU path | `72.56.0.145` (`RU_RELAY_HOST`) | **High** — missing from live sub |
| LV/NL exit | Direct + relay exits | `NODE-POLICY-LV-NL.md` | **High** — 0 outbounds in probe |
| DNS | DoH / split DNS | `dns_split_config.py`, AUD-230 patches | **Med** — DoH missing per verify |
| Sub refresh notify | Push user to reload sub | `bot_src/subscription_refresh.py` | **Med** — profile churn |
| Balance/expiry | Access entitlement | `bot_src/` billing, panel status | Low for tunnel flap (not toggling in probe) |

---

## 6. Hypotheses table

| # | Hypothesis | Evidence needed | Safe check | Scripts | Sev | Pre-probe confidence |
|---|------------|-----------------|------------|---------|-----|----------------------|
| H1 | Unstable **relay#2-only** node (SPOF) | relay TCP/TLS latency; node metrics | `relay_latency_probe.py` from LV | `relay_latency_probe.py` | P0 | **75%** |
| H2 | **Balancer flapping** (random, no health check) | access_log outbound switches | `diagnose_speed.py` | done | P1 | **70%** |
| H3 | **DNS** failures (no DoH) | dns query errors in Happ log | `verify_vpn_balancer_profile`, `probe_dns_leak` | partial | P1 | **55%** |
| H4 | Caddy/TLS timeout | 502/504 at edge | HTTP timing | curl/python GET | P2 | **15%** |
| H5 | Transport xhttp mismatch | batch_risk HIGH | `diagnose_happ_import.py` | done → LOW | P3 | **5%** |
| H6 | Direct/relay hybrid conflict | routing rules vs injectHosts | routing dump | probes | P1 | **40%** |
| H7 | Routing sends traffic wrong outbound | access_log per domain | user log | — | P1 | **45%** |
| H8 | TSPU/DPI on single relay path | works on Wi‑Fi not LTE | user report | — | P1 | **50%** |
| H9 | Expiry/balance toggling | panel status changes | panel API read | not run | P3 | **10%** |
| H10 | Sub refresh returns **inconsistent** profile | hash across fetches | repeat GET | probe | P2 | **10%** (size stable 5896) |
| H11 | IPv4/IPv6 mismatch | client log | user log | — | P3 | **20%** |
| H12 | MTU/fragmentation | blackhole on large packets | mtr user-side | — | P2 | **25%** |
| H13 | Server resource pressure | CPU/mem on relay2/AMS | SSH metrics | not run | P1 | **35%** |
| H14 | Remna/panel sync delay | template vs sub drift | generation id | panel read | P2 | **30%** |
| H15 | Happ **auto-refresh** + profile conflict | subscription_log timestamps | user Happ log | — | P1 | **40%** |
| H16 | **Old cached sub** (16-path + leastLoad flap) | user last refresh date | compare sub size | user | P1 | **50%** if not refreshed |
| H17 | **Over-trimmed relay-only** profile (3 hosts) | injectHosts count | `probe_injecthosts_sub_parity` | done → 3 | P0 | **80%** |
| H18 | Missing **catch-all** balancer rule | routing rules | `probe_balancer_catchall` | done → FAIL | P1 | **65%** |

---

## 7. Probes run

| Command | Target | Result | Interpretation | Hypotheses |
|---------|--------|--------|----------------|------------|
| `python ops/happ_geosite_guard.py` | template JSON | `HAPP_GEOSITE_GUARD_OK` | No forbidden geosite:ru in template scan | H7 ↓ |
| `python ops/probe_subscription.py` | panel + Happ sub | HTTP 200, **5896 B**, 3 tcp vless, **LV=0 NL=0**, all `46.173.28.252:443` | Profile collapsed to relay2-only | H1, H17 |
| `python ops/diagnose_happ_import.py` | Happ sub | `batch_risk=LOW`, xhttp=0, **observatory=NO**, leastLoad=NO | Not xhttp/observatory regression | H5 ↓, E1 ↓ |
| `python ops/verify_vpn_balancer_profile.py` | Happ sub | `VPN_BALANCER_PROFILE_OK`, mode **relay-only×3**, **dns=BROKEN** | Gate accepts trimmed profile; DNS issue | H3, H17 |
| `python ops/transport_mux_audit.py --sample 3` | 3 users | **FAIL** 0% primary+alt, all OTHER:9 | No mux failover paths | H1, H17 |
| `python ops/probe_users_sub_sample.py` | 5 users | all **5896 B**, **3 proxy** | Consistent collapsed profile | H10 ↓ |
| `python ops/probe_injecthosts_sub_parity.py` | template vs sub | `injectHosts: 3`, `INJECT_SUB_PARITY_OK` | Template intentionally 3 hosts | H17 ✓ |
| `python ops/probe_balancer_catchall.py` | public monitor sub | **FAIL**: Super_Balancer MISSING, catch-all 0, proxy=3 want 14 | Legacy smoke expects gen=20; prod diverged | H18 ✓ |
| `python ops/diagnose_speed.py` | template + sub | 2 issues: **no catch-all**, **dns DoH missing**; observatory absent OK | Random 6-path balancers but 3 injectHosts | H2, H3, H18 |
| Python GET timing | `p4n7q` sub monitor | HTTP **200**, **0.22s**, `application/json` | Edge healthy | H4 ↓ |
| Python GET timing | `k9x2m1/status`, `/start/` | HTTP **200**, ~0.12s | Portal/status up | H4 ↓ |

**Not run (classified caution / needs vantage):** `drift-check.py`, `relay_latency_probe.py`, `subscription_load_probe.py`, SSH log tail.

---

## 8. Logs reviewed

| Source | Window | Summary | Interpretation |
|--------|--------|---------|----------------|
| `docs/VPN-INCIDENT-LESSONS-2026-05-25.md` | May 2025 | E1 closed-pipe + observatory; E6/E7 random balancer slowness; proxy flap class | Historical mechanisms; observatory **off** today |
| `docs/CODERABBIT-AUDIT-PROMPT-2026-05-VPN-STABILITY.md` | May 24 logs | proxy-6/7/8 flap; 524× retry to Meta CDN IP; batch import count=0 | **User log pattern** for reconnect feel; may differ if sub refreshed |
| `docs/AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md` | May 25 | xhttp fixed; observatory re-tuned 30s | Profile since evolved to 3-host relay2 |
| Live docker/journal | — | **Not collected** — no SSH log tail in this pass | Gap: need owner-approved read-only tail on LV/relay |

---

## 9. User/config checks

| Check | Result |
|-------|--------|
| Sub stable across users | Yes — sample 5/5 → **5896 B**, 3 proxies |
| Same sub repeated fetch | Size stable; hash check not completed (body is bytes) — treat as stable |
| LV/NL/relay#1 in sub | **Absent** — only relay#2 |
| Observatory / leastLoad | **Absent** |
| xhttp | **0** |
| injectHosts parity | **3 = 3** (template matches live) |
| Multiple keys per user | Not enumerated (DB read avoided); policy allows multiple — support should ask |
| One link / multi device | Cannot confirm without telemetry |
| Deprecated domains in profile | Not observed; remarks `🚀 BenderVPN Auto` |
| Routing direct/relay conflict | **WARN**: no catch-all; Intl_Direct + Intl_Stealth random on 6 selector tags but 3 hosts |

**No subscription URLs, UUIDs, or tokens included in this report.**

---

## 10. Evidence summary

1. **Prod profile is not the documented 14-relay multipath** — it is **3× relay#2-only** (5896 B).
2. **`probe_balancer_catchall` fails** against gen=20 expectations — architectural drift.
3. **`transport_mux_audit` fails** — no primary/alt transport redundancy.
4. **DNS config flagged BROKEN** (missing DoH) on live sub.
5. **Edge HTTP healthy** — unlikely pure 502/504 at Caddy for monitor URL.
6. **Happ import healthy** — batch_risk LOW; not «0 servers» class from xhttp today.
7. **Historical flapping** documented with observatory+leastLoad; **different mechanism** if user still on old sub.

---

## 11. Ranked likely root causes

| Root cause | Sev | Conf. | Evidence | Missing evidence | Safe fix direction | Owner approval? | Rollback / no-go |
|------------|-----|-------|----------|------------------|-------------------|-----------------|------------------|
| **RC-1: Over-trimmed relay2-only profile (3 hosts, no LV/NL/relay#1)** | P0 | **82%** | All probes: only `46.173.28.252`, 3 proxies, mux FAIL | Relay#2 live health from RU | Restore multipath injectHosts per `VPN-INCIDENT-LESSONS` §3 or staged relay#1+#2 (6 host) — **dry-run + probe gate** | **Yes** | **No-go:** `patch_injecthosts_lv_direct_only`, remove relay, observatory without staging |
| **RC-2: Random balancer without catch-all / health check** | P1 | **68%** | `diagnose_speed` WARN; `Super_Balancer` missing; May flap logs | User access_log today | Add catch-all rule + direct-first relay fallback; observatory only on staging with gstatic/204 | **Yes** | **No-go:** leastLoad + hicloud probe (E1) |
| **RC-3: User on stale sub (16-path + leastLoad era)** | P1 | **50%** | May logs; sub gen notify exists | User sub byte size in Happ | Ask user refresh; compare 5896 vs ~10KB | No | Refresh only after fix deployed |
| **RC-4: DNS misconfig (no DoH)** | P1 | **55%** | verify dns=BROKEN | Happ DNS errors | Apply AUD-230 split DNS if not active — **audit first** | **Yes** | **No-go:** geosite:ru in dns.servers (G2) |
| **RC-5: TSPU/DPI on only remaining RU relay path** | P1 | **45%** | Single path; RU product | User network A/B Wi‑Fi/LTE | Second relay + exit diversity | Partial | More paths ≠ patch in panic |
| **RC-6: Relay#2 resource/conn pressure** | P1 | **38%** | SPOF design | SSH metrics | `relay_latency_probe`, node stats | Yes | — |
| **RC-7: Happ auto-refresh during sub gen pushes** | P2 | **35%** | `subscription_refresh.py` | subscription_log | Coordinate notify after stable profile | Yes | No mass broadcast without approval |
| **RC-8: Edge TLS/proxy instability** | P2 | **12%** | 200 OK 0.22s | Extended edge metrics | Monitor only | No | — |

### Monitoring gaps (P3)

- No automated alert on **injectHosts count drop** or **sub size regression** (11500→5896 would be P0 signal).
- `verify_vpn_balancer_profile` passes **relay-only×3** while `probe_balancer_catchall` expects 14 — **gate contradiction**.

---

## 12. What not to touch

- All `ops/patch_*` / `restore_*` / `emergency_*` without owner + rollback snapshot
- `burstObservatory` on prod without `RUNBOOK-OBSERVATORY-STAGING.md` + Happ `error_log` check
- Removing relay paths for «speed» without multipath replacement
- `broadcast_refresh_sub.py`, `push_sub_config_generation_ams.py`
- Mass subscription refresh
- Caddy / Remna panel writes
- geosite:ru / category-ru direct rules without geo guard

---

## 13. Immediate support checklist (send to user)

Ask the user for:

1. **Device** — model (e.g. iPhone 14, Samsung A54, Windows laptop)
2. **OS version** — iOS/Android/Windows/macOS + version
3. **Network** — Wi‑Fi or LTE; provider (Megafon/MTS/etc.)
4. **When** — time of disconnects; **every N minutes?** pattern
5. **Happ screenshot** — connected/disconnected state + selected profile name
6. **Happ logs** — `subscription_log` + `error_log` (redact URL/token)
7. **Telegram ID** — via `/id` in bot
8. **Other VPN/profile** — any other VPN or second Happ profile enabled?
9. **Traffic scope** — **Telegram only** drops or **all apps**?
10. **Last sub refresh** — when they tapped refresh in Happ (approx.)
11. **Sub size hint** — in Happ about screen if visible (~5.9 KB vs ~10 KB indicates profile generation)

**First-line user steps (no infra change):**

- Happ → refresh subscription once; reconnect BenderVPN Auto
- If loops continue → export logs and send to support
- Do **not** ask user to pick NL/LV manually (product policy)

---

## 14. Safe next diagnostic commands

Owner/ops — read-only:

```bash
python ops/probe_subscription.py
python ops/diagnose_happ_import.py
python ops/probe_balancer_catchall.py
python ops/transport_mux_audit.py --sample 5
python ops/diagnose_speed.py
python ops/relay_latency_probe.py          # needs LV→relay SSH
python ops/tspu_block_probe_ru.py          # RU path health
```

With user cooperation:

- Happ `access_log` 30 min slice — count outbound tag changes (flap rate)
- Compare user sub fetch size to **5896** bytes benchmark from this audit

---

## 15. Recommended next implementation prompt (do not run now)

> **AUDIT-002 + owner-approved VPN profile restoration (dry-run only first)**
>
> 1. Read `docs/AUDIT-2026-06-09-VPN-RELIABILITY.md` RC-1..RC-2.
> 2. Fetch current panel template generation + snapshot to `.secrets/snapshots/`.
> 3. **Dry-run only:** compare `patch_restore_14_relay_no_obs.py` vs `patch_trim_injecthosts_relay_only.py` vs staged **6-host relay#1+relay#2** — no `--apply`.
> 4. Document trade-off: ping UX vs failover (injectHosts count).
> 5. Run verify gate on **simulated** JSON only if possible; else stop at plan.
>
> **Hard stop:** no `--apply`, no deploy, no notify broadcast until owner picks profile target.

---

## References

- `docs/VPN-INCIDENT-LESSONS-2026-05-25.md`
- `docs/AUDIT-2026-05-VPN-STABILITY-RESOLUTION.md`
- `docs/CODERABBIT-AUDIT-PROMPT-2026-05-VPN-STABILITY.md`
- `docs/BENDERVPN-AUDIT-ROADMAP.md` AUDIT-001
- `docs/BENDERVPN-MASTER-BACKLOG.md` VPN-REL-001
- `ops/patch_trim_injecthosts_relay_only.py`
- `ops/patch_restore_14_relay_no_obs.py`

---

**AUDIT-001 status:** complete (read-only) · **Next:** owner review → AUDIT-002 architecture map + restoration dry-run
