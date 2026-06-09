# INCIDENT-001 — Production VPN Stability & Deployment Drift Audit

**Date:** 2026-06-10 ~20:07–20:25 UTC  
**Mode:** read-only incident audit · no prod mutation · no deploy  
**Branch:** `product-referral-cabinet-ui-v1` @ `7fd8c12` (local, 1 commit ahead of origin)  
**Trigger:** Owner reports VPN connection **still breaks constantly** across platforms/networks  
**Prior context:** Candidate D applied 2026-06-09 ([`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md)); P1-DEV-001 cabinet deploy 2026-06-09 ([`POSTDEPLOY-2026-06-10-P1-DEV-001.md`](POSTDEPLOY-2026-06-10-P1-DEV-001.md))

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **Is Candidate D active in production?** | **YES** — live sub **7353 B**, **6** VLESS proxies, relay#1×3 + relay#2×3, DoH present, selector parity OK |
| **Did Candidate D regress?** | **NO** — all automated gates PASS; injectHosts=6; no 6-selector/3-outbound skew |
| **Is infra healthy?** | **YES** — AMS/LV containers up; relays TCP-reachable; subscription edge stable (15/15 HTTP 200, size constant) |
| **Did recent P1-CAB/P1-DEV deploy break VPN?** | **NO evidence** — cabinet API + portal static only; no Remna/template/Caddy/subscription generator change |
| **Why does owner still see disconnects?** | **Not reproduced by server probes.** Most likely: **Happ client stale profile cache** and/or **Happ platform sleep/resume / false-connected behavior**. Secondary: intermittent **VLESS-layer** degradation (TCP probes OK ≠ VLESS OK). |

**Incident status:** Server/profile **not confirmed broken**. User-impact **ongoing per owner report** but **not reproducible from read-only infrastructure probes**. **No emergency prod mutation recommended** without owner device evidence.

**Go/no-go:** **STOP product development** (already frozen). **Do not rollback Candidate D.** **Do not apply template/Caddy/Remna changes** until owner completes Happ diagnostic matrix (§15).

---

## 2. Timeline

| When | Event |
|------|-------|
| 2026-06-09 ~15:01 UTC | Candidate D global template apply (`patch_restore_6relay_stealth.py --apply`) |
| 2026-06-09 ~16:26 UTC | P1-CAB-001 cabinet billing_profile deploy (AMS + LV portal) |
| 2026-06-09 ~20:10 UTC | P1-DEV-001 active config summary deploy (AMS `portal_cabinet.py` + LV portal `v=28`) |
| 2026-06-10 ~20:16 UTC | INCIDENT-001 read-only audit started |

**Note:** `remna-shop-bot` restarted at P1-DEV-001 deploy (~20:10 UTC). Does **not** affect subscription generation path.

---

## 3. Repo / deployment drift (Phase 1)

| Check | Value |
|-------|-------|
| Branch | `product-referral-cabinet-ui-v1` |
| Local HEAD | `7fd8c12` — docs(deploy): record P1 active config summary rollout |
| Origin HEAD | `2be02f0` — feat(cabinet): expose active config summary |
| Ahead of origin | **1** (docs-only postdeploy) |
| Behind origin | **0** |
| Dirty tree | `.cursor/skills/…` modified; untracked screenshots/ops smoke scripts |
| Staged | None |
| Deploy in progress | **No** (P1-DEV-001 completed SUCCESS earlier) |

### Production should contain (per docs)

| Surface | Expected |
|---------|----------|
| Remna global template | Candidate D — injectHosts **6**, RELAY6 selectors, split DoH |
| Live Happ subscription | **7353 B**, **6** proxies |
| AMS `portal_cabinet.py` | P1-CAB-001 + P1-DEV-001 (`build_configuration_fields`) |
| LV portal static | `portal.js?v=28`, config list UI |

---

## 4. Deployed version audit (Phase 2)

| Component | Host | Expected | Deployed / observed | Drift | VPN impact |
|-----------|------|----------|---------------------|-------|------------|
| Global subscription template | AMS Remna panel | Candidate D gen **102** | injectHosts=**6**, VPN_BALANCER_PROFILE_OK | **No** | **None** — correct |
| Live subscription edge | AMS `remnawave-subscription-page` | Serve 7353 B JSON | Logs show HTTP **200** 7353 B for Happ UA | **No** | **None** |
| `portal_cabinet.py` | AMS `remna-shop-bot` | P1-DEV-001 | `build_configuration_fields` present; md5 `a4f6744d…` (LF-normalized) | **No** (content matches repo) | **None** — cabinet API only |
| Portal static | LV `/var/www/bvpn-portal/` | `v=28` | `portal.js?v=28` live | **No** | **None** — UI only |
| Caddy selfsteal | AMS | Unchanged | Up 4 weeks; cert renewals only | **No** | **None** |
| remnanode | LV | Up | Up **6 days**, restart count **0** | **No** | Exit path (not in injectHosts for D) |
| Latency autotrim | LV cron | 6-path selectors | `[autotrim] no selector change`; 6 paths | **No** | **None** |

---

## 5. Candidate D integrity (Phase 3)

| Check | Expected | Actual | Pass | Impact |
|-------|----------|--------|------|--------|
| Sub size (Happ UA) | ~7353 B | **7353 B** | ✅ | — |
| VLESS proxy count | 6 | **6** | ✅ | — |
| relay#1 `72.56.0.145` | ×3 | **3** (`proxy`…`proxy-3`) | ✅ | — |
| relay#2 `46.173.28.252` | ×3 | **3** (`proxy-4`…`proxy-6`) | ✅ | — |
| Selector parity | 6 tags, all exist | Intl_Direct **6**, Intl_Stealth **6** | ✅ | Pre-D skew **resolved** |
| DoH / split DNS | Present | **4** DNS servers | ✅ | Pre-D BROKEN DNS **fixed** |
| Observatory | OFF | **OFF** | ✅ | — |
| injectHosts parity | 6 = live 6 | **INJECT_SUB_PARITY_OK** | ✅ | — |
| Super_Balancer | Absent | Absent | ✅ | — |
| LV/NL direct in inject | 0 | **0** | ✅ | By design |
| geosite:ru | Unchanged | **HAPP_GEOSITE_GUARD_OK** | ✅ | — |
| Catch-all → Intl_Direct | Present | R6 `network=tcp,udp → Intl_Direct` | ✅ | — |
| `VPN_BALANCER_PROFILE_OK` | PASS | **PASS** | ✅ | — |
| `VPN_VERIFY_GATE_OK` | PASS | **PASS** (local; RU probes on LV separately) | ✅ | — |

**Hard-stop conditions:** **None triggered.** Candidate D is **active**, not regressed.

---

## 6. Multi-user subscription samples (Phase 4)

`probe_users_sub_sample.py --sample 5` → **SUB_SAMPLE_VERIFY_OK**

| Sample (redacted) | Bytes | Proxies | Relays | DNS | Parity | Issue |
|-------------------|-------|---------|--------|-----|--------|-------|
| trial user 1 | 7353 | 6 | r1×3+r2×3 | split 4 | OK | none |
| web trial 2 | 7353 | 6 | r1×3+r2×3 | split 4 | OK | none |
| web trial 3 | 7353 | 6 | r1×3+r2×3 | split 4 | OK | none |
| trial user 4 | 7353 | 6 | r1×3+r2×3 | split 4 | OK | none |
| web trial 5 | 7353 | 6 | r1×3+r2×3 | split 4 | OK | none |

**Subscription edge stability:** 15 consecutive Happ fetches → **0 fails**, size **7353–7353** stable.

---

## 7. Relay / edge probes (Phase 5)

| Probe | Target | Iterations | Fails | Latency | Interpretation | Candidate D impact |
|-------|--------|------------|-------|---------|----------------|-------------------|
| `relay_latency_probe.py` (LV) | relay#1 `72.56.0.145:443` | 1 | 0 | **8.9 ms** tcp | Healthy | Safe path in profile |
| `relay_latency_probe.py` (LV) | relay#2 `46.173.28.252:443` | 1 | 0 | **8.3 ms** tcp | Healthy | Safe path in profile |
| `tspu_block_probe_ru.py` (LV) | edge via relay#1 | 3 checks | 0 | 17–31 ms | Reachable | No TSPU hard-block |
| `tspu_block_probe_ru.py` (LV) | edge via relay#2 | 3 checks | 0 | 76–121 ms | Reachable (slower) | relay#2 usable |
| Sub edge stability | `GET /api/sub/{short}` Happ | 15 | 0 | stable 7353 B | No cache drift | — |

**Note:** TCP/TLS probes do **not** prove VLESS Reality handshake success under TSPU.

---

## 8. Server / container health (Phase 6)

| Host | Service | Status | Red flags | Impact |
|------|---------|--------|-----------|--------|
| **AMS** | `remnawave` | Up 6d healthy | None | — |
| **AMS** | `remnawave-subscription-page` | Up 12d | Serving 7353 B subs | — |
| **AMS** | `remna-shop-bot` | Up (restarted P1-DEV) | Clean startup; scheduler OK | Cabinet only |
| **AMS** | `caddy-selfsteal` | Up 4w | Cert renewals only | — |
| **AMS** | Disk/mem | 34% disk; mem ~1.0Gi used | No OOM | — |
| **LV** | `remnanode` | Up 6d | Restart count **0** | — |
| **LV** | Disk/mem | 68% disk; 523Mi used | Disk watch (not full) | — |
| **LV** | autotrim cron | Running | No injectHosts shrink | — |

No crash loops, 5xx spikes, or secret leakage in sampled logs.

---

## 9. Client UA / profile matrix (Phase 7)

| Client UA | HTTP | Size | Proxies | Rules | Auto-equivalent? | Issue |
|-----------|------|------|---------|-------|-----------------|-------|
| **Happ** | 200 | 7353 | 6 | 7 | **Yes** | None server-side |
| **Hiddify** | 200 | 7353 | 6 | 7 | **Yes** | — |
| **Streisand** | 200 | 7353 | 6 | 7 | **Yes** | — |
| **Karing** | 200 | 2036 | 0 (LV strip) | 0 | **No** | Not Auto path |
| **ClashMeta** | 200 | 1583 | 0 | 0 | **No** | LV direct YAML |
| **sing-box** | 200 | 344 | 0 | 0 | **No** | Single VLESS link |
| **v2rayN** | 200 | 344 | 0 | 0 | **No** | Single VLESS link |

**Happ import risk:** `diagnose_happ_import.py` → **batch_risk=LOW**, 6 parseable proxies, no xhttp, no observatory.

---

## 10. Happ client behavior audit (Phase 7A)

Server emits correct Candidate D profile. Owner symptoms (~1/min failures, connected-but-refresh-needed, sleep/resume) **match historical pre-D server bugs** but **server probes no longer show those bugs**.

| Hypothesis | Evidence for | Evidence against | Likelihood |
|------------|--------------|------------------|------------|
| **Stale cached profile despite server-side Candidate D** | Owner refreshes often; pre-D required refresh; Happ known to cache | Live server always returns 7353 B / 6-proxy now | **High** if client did not fully refresh/reimport |
| **Happ false-connected / DNS cache** | Owner: pages fail until refresh while tunnel shows connected | Server DNS split OK; DoH in profile | **High** |
| **Happ sleep/resume / Wi-Fi↔LTE** | Owner reports all platforms; desktop sleep worst | Server paths stable; multipath should help | **Medium** |
| **Server profile still broken** | Owner symptom severity | All automated gates PASS; 5/5 user samples identical | **Low** |
| **VLESS handshake intermittent** | TG-only RU incidents historically VLESS-layer | TCP probes green; needs report.zip / alternate client A/B | **Medium** |

**Happ remains primary recommendation** while incident open — but owner **must confirm the profile was refreshed/reimported after Candidate D**. Happ may display **one Auto host/profile**; this is expected if the app abstracts internal relay paths.

**Happ UX note:** The **6 relay paths** are verified **server-side** in subscription JSON / profile parser (`verify_vpn_balancer_profile.py`, `probe_subscription.py`). They **may not appear as six selectable nodes** in Happ. The user does **not** manually choose relay nodes.

**Alternate-client comparison recommended** (diagnostic only): same URL in **Hiddify** on same network — if stable in Hiddify but not Happ → client issue; if both fail → server/path issue.

---

## 11. Recent deploy impact (Phase 8)

| Recent change | Deployed? | Touches VPN path? | Evidence | Impact |
|---------------|-----------|-------------------|----------|--------|
| Candidate D template apply | Yes (2026-06-09) | **Yes** — fixes profile | 7353 B / 6 proxy live | **Positive** |
| P1-CAB-001 `portal_cabinet.py` | Yes | **No** | billing_profile API only | None |
| P1-DEV-001 portal + cabinet | Yes | **No** | config list UI/API | None |
| P1-REF bot handlers | Yes (prior) | **No** | referral attribution | None |
| Remna/Caddy/generator change today | **No** | — | No mutation in audit window | None |
| broadcast / mass-refresh | **No** | — | Not run | None |

---

## 12. Root cause decision matrix (Phase 9)

| Hypothesis | Evidence for | Evidence against | Confidence | Severity | Fix path | Approval |
|------------|--------------|------------------|------------|----------|----------|----------|
| Candidate D regressed | Owner pain | All probes PASS | **Low** | — | None | — |
| Live sub stale/cache serving old profile | Happ cache behavior | Edge returns 7353 B consistently | **Medium** (device) | High UX | Owner full refresh + reimport | None |
| Happ not refreshed post-D | Owner refreshes often but may be partial | Server correct | **Medium** | High | Delete profile → reimport | None |
| relay#1/#2 TCP instability | — | Probes OK 8–9 ms | **Low** | — | Monitor | — |
| VLESS-layer intermittent fail | Historical RU pattern | TCP OK; no report.zip | **Medium** | High | report.zip + Hiddify A/B | None |
| DNS/DoH failure | Pre-D issue | DoH present now (4 servers) | **Low** (server) | — | Happ DNS cache test | None |
| Selector/outbound mismatch | Pre-D cause | **Resolved** in D | **Very low** | — | — | — |
| Caddy/sub route issue | — | 200 stable ×15 | **Low** | — | — | — |
| Remna/template drift | — | inject parity OK | **Low** | — | — | — |
| Server resource exhaustion | — | AMS/LV healthy | **Low** | — | — | — |
| Recent cabinet deploy drift | Bot restart | No VPN code touched | **Very low** | — | — | — |
| Owner device/network specific | Multi-network report | Server global profile OK | **Medium** | — | Device diagnostics §15 | None |

### Top 3 likely causes

1. **Stale cached profile despite server-side Candidate D** — client did not fully refresh/reimport current subscription — **Medium–High confidence**
2. **Happ false-connected + DNS/routing cache** (connected UI, sites need refresh) — **Medium confidence**
3. **VLESS-layer intermittent failure** not visible in TCP probes — **Medium confidence**, needs owner report.zip or Hiddify A/B

### Happ diagnostic decision rules

- **Do not** classify **one visible Happ Auto host** as regression — Happ abstracts internal 6 relay paths into one Auto profile.
- **Regression** only if server-side subscription for that user returns old **5896 B / 3-proxy** profile, or if a local exported/imported profile proves old structure.
- If Happ shows **one Auto host** but server-side sub is **7353 B / 6 proxies**, classify UI as **expected** and continue client-behavior diagnostics (refresh/reimport, false-connected, sleep/resume, `report.zip`).

---

## 13. Confirmed issues

| ID | Issue | Severity | Server-side? |
|----|-------|----------|--------------|
| **I-001** | Owner reports ongoing disconnects | **P0 user impact** | **Not reproduced** by probes |
| **I-002** | 48h post-D soak log incomplete | Medium | Documentation gap |
| **I-003** | Non-Happ clients still LV-direct strip | High (product) | Known; not cause if owner uses Happ |
| **I-004** | `transport_mux_audit` fails on relay-only profile | Low | Expected for Candidate D; not regression |
| **I-005** | `diagnose_speed` catch-all WARN | Low | False positive — `probe_routing` confirms R6 catch-all |

**No confirmed server/profile regression requiring emergency rollback.**

---

## 14. Fix plan (Phase 10) — do not apply without approval

| Class | Action | Risk | Approval phrase | Rollback |
|-------|--------|------|-----------------|----------|
| **A** | Owner Happ diagnostic matrix (§15) | None | None | — |
| **A** | Continue 24–48h monitoring; log disconnect times | None | None | — |
| **B** | Hiddify A/B on owner device (diagnostic) | Low | Owner consent | — |
| **C** | Re-apply Candidate D if template drift found later | Medium | `approve emergency restore Candidate D profile` | `.secrets/snapshots/template-pre-candidate-d-apply-*.json` |
| **C** | `patch_routing_client_refresh.py` for Karing parity | Medium | Explicit owner approval | Template snapshot |
| **D** | Rollback Candidate D to pre-D 5896 B | **High** | `approve rollback Candidate D template` | Snapshot §8 APPLY doc |
| **E** | Server "fix" without device evidence | — | **Do not proceed** | — |

---

## 15. Owner manual test instructions

### Happ refresh verification (all devices)

1. Open Happ → **🚀 BenderVPN Auto**
2. **Refresh subscription** (pull-to-refresh or refresh button)
3. Confirm the profile was **refreshed/reimported after Candidate D**. Happ may show **one Auto host/profile** — this is **expected**; internal relay paths are not necessarily visible as selectable nodes.
4. If instability remains:
   - **Delete** the BenderVPN profile completely
   - **Reimport** from bot or cabinet setup link
   - Confirm the app shows the expected **single Auto profile/host**
5. TUN **off → on**
6. Test **Google + Instagram + Telegram** (not Telegram alone)
7. Record **exact failure time** and whether Happ still shows **connected**

**Server-side check (ops, not owner):** 6 relay paths are verified in subscription JSON via `probe_subscription.py` / `verify_vpn_balancer_profile.py` — not by counting nodes in Happ UI.

### Evidence to collect

| Item | Why |
|------|-----|
| Happ version + OS version | Platform-specific bugs |
| Screenshot of **profile screen** after refresh | Confirm single Auto profile UX; not a node-count check |
| Whether Happ shows "connected" during failure | False-connected detection |
| Failure mode (DNS / all traffic / TG-only / after sleep) | Root cause branch |
| `report.zip` from Happ (if available) | VLESS RST analysis per `vpn-incident-tg-only-ru` skill |
| Hiddify test same URL same network | Client vs server classification (diagnostic only) |

### Optional comparison test

- Import same subscription URL into **Hiddify** (diagnostic only — do not change public recommendation)
- Same Wi‑Fi, same time window
- If Hiddify stable + Happ unstable → **Happ/client issue**
- If both unstable → **server/path issue** → escalate with report.zip

---

## 16. Rollback plan

**Not recommended.** Candidate D is healthy on all automated gates.

If **server-side** subscription for the owner account returns **5896 B / 3-proxy** after Candidate D, or a **local exported/imported profile** proves old structure → investigate cache/import first, not template rollback. **One visible Auto host in Happ is not evidence of regression.**

Emergency template rollback path: [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md) §8.

---

## 17. Go / no-go recommendation

| Decision | Verdict |
|----------|---------|
| Rollback Candidate D | **NO** — probes show active correct profile |
| Emergency template patch | **NO** — no drift detected |
| Continue product development (P1/P2) | **NO** — freeze until owner device evidence |
| Owner Happ diagnostics | **YES** — required next step |
| Monitoring | **YES** — 24–48h disconnect log |

**Next step if fix needed:** Owner completes §15 → share profile-screen screenshot + failure mode + `report.zip` if available → ops can verify server-side sub size for that account → request targeted approval only if server/profile regression is proven.

---

## 18. Skills / tools used

**Skills:** `vpn-incident-tg-only-ru`, `bendervpn-vpn-architecture-audit`, `bendervpn-release-guard`  
**Rules:** `bendervpn-guardrails.mdc`, `bendervpn-repo-workflow.mdc`  
**Probes:** `verify_vpn_balancer_profile.py`, `probe_subscription.py`, `probe_injecthosts_sub_parity.py`, `probe_users_sub_sample.py`, `probe_routing.py`, `diagnose_happ_import.py`, `diagnose_speed.py`, `happ_geosite_guard.py`, `vpn_verify_gate.py`, `relay_latency_probe.py` (LV), `tspu_block_probe_ru.py` (LV), UA matrix probe, SSH health (AMS/LV)
