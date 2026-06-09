# INCIDENT-002 — Active VPN Failure Capture & Controlled Stabilization Plan

**Date opened:** 2026-06-10  
**Mode:** incident work only · freeze product development · no prod mutation in this pass  
**Branch:** `product-referral-cabinet-ui-v1` @ `68a6abb`  
**Prior:** [`INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md`](INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md) (INCIDENT-001)  
**Candidate D:** active — 7353 B / 6 internal VLESS paths / DoH OK / selector parity OK

---

## 1. Executive summary

| Item | Status |
|------|--------|
| **Failure reproduced?** | **NO** — ops watch #1 green; **owner reports no disconnects after fresh import** (interim) |
| **Owner test window #1** | **INTERIM PASS** — fresh delete/reimport; ops watch **2026-06-09 20:49–20:52 UTC** |
| **Server/profile regression?** | **Not confirmed** |
| **Leading interim explanation** | **B** stale Happ import/cache may have cleared; **A** local network / client lifecycle still plausible |
| **Prod change?** | **None** |
| **Prod fix justified?** | **NO** — failure not reproduced; continue longer soak before closing |
| **Incident closed?** | **NO** — extended soak + **sleep/resume** observation pending |
| **INCIDENT-003 (sleep/resume)** | **OPEN** — owner: another VPN survives laptop sleep; BenderVPN/Happ breaks routes until reboot sometimes. See [`INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md`](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md) |
| **INCIDENT-004 (browser SaaS long-session)** | **OPEN** — browser SaaS (e.g. Claude) shows connection banner while page loaded; intermittent sends; typical during document work. See [`INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md`](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md) |

INCIDENT-001 proved infrastructure/profile health from read-only probes but did **not** capture an owner failure window. INCIDENT-002 adds **time-correlated evidence collection** and a **controlled stabilization decision tree** — still **no mutation** until evidence + explicit approval. **INCIDENT-003** narrows desktop **sleep/resume**; **INCIDENT-004** narrows **long-lived browser/SaaS sessions** — both may share Happ TUN lifecycle root cause; short TCP/sub probes **cannot disprove** either.

---

## 2. Classification targets

| Code | Hypothesis |
|------|------------|
| **A** | Happ / client / OS issue |
| **B** | Stale or partially imported client profile |
| **C** | DNS / DoH handling inside client |
| **D** | VLESS / Reality layer issue (TCP probes insufficient) |
| **E** | Relay-specific instability (relay#1 vs relay#2) |
| **F** | Subscription edge / profile generation issue |
| **G** | Server infrastructure (containers, disk, crash loops) |

---

## 3. Owner test protocol (mandatory sequence)

**Before starting:** tell ops the planned **local start time** and **device/OS** so server watch window can align.

### Steps

1. In Happ, **delete BenderVPN profile completely**.
2. **Reimport** fresh profile from bot or cabinet setup link.
3. **Do not expect 6 selectable nodes** — **one Auto profile/host is expected** UX.
4. Turn **TUN/VPN off → on**.
5. Test **10–15 minutes**:
   - Google
   - Instagram
   - Telegram
   - 2–3 normal browser sites
6. On failure, record:

| Field | Record |
|-------|--------|
| Local time + UTC if possible | |
| Device / OS | |
| Happ version | |
| Network (Wi‑Fi / LTE) | |
| Happ still shows connected? | yes / no |
| Failure scope | all traffic / DNS only / TG only / websites only / after sleep / after network switch |
| VPN off/on fixes? | yes / no |
| Page refresh fixes? | yes / no |
| Screenshot / screen recording | attach if possible |
| `report.zip` from Happ | attach if available |

### Optional A/B (diagnostic only)

- Import **same subscription URL** into **Hiddify** on **same device + network**.
- **Do not** change public Happ recommendation.
- **Hiddify stable, Happ fails** → classify **A** (Happ/client).
- **Both fail** → classify **D/E/F** (server/path/VLESS).

---

## 4. Ops watch window (read-only)

Run when owner announces test start (target: ±15 min around owner window).

### Commands (safe, redacted)

```bash
# Baseline / during window — from workstation
python ops/verify_vpn_balancer_profile.py
python ops/probe_subscription.py
python ops/probe_users_sub_sample.py --sample 3

# Relay soak — on bvpn-lv (30–60 iterations max, light interval)
for i in $(seq 1 30); do python3 /opt/scripts/relay_latency_probe.py || echo FAIL; sleep 0.5; done

# Subscription edge logs — AMS (redact shortUuid in output)
docker logs --since 30m remnawave-subscription-page 2>&1 | grep 'GET /api/sub/' | tail -50
# Manually redact: sed -E 's#/api/sub/[A-Za-z0-9_-]+#/api/sub/[REDACTED]#g'

# Container health — AMS
docker inspect -f '{{.Name}} {{.State.Status}} restarts={{.RestartCount}}' \
  remnawave remnawave-subscription-page caddy-selfsteal remna-shop-bot
```

### VLESS / Reality note

Repo tooling (`relay_latency_probe.py`, `tspu_block_probe_ru.py`) uses **TCP connect only**. Reality inbounds **reject generic TLS** — **TCP OK ≠ VLESS OK**.

**Safe VLESS evidence paths:**

- Owner **`report.zip`** → `selected_server.json`, `tun_log.txt` RST analysis (see `vpn-incident-tg-only-ru` skill)
- Happ vs Hiddify A/B on same network
- Time-correlate RST targets with relay#1 `72.56.0.145` vs relay#2 `46.173.28.252`

**Do not** build or run invasive VLESS brute probes against prod without owner approval.

---

## 5. Test matrix

| # | Test | Status | Result | Classification hint |
|---|------|--------|--------|---------------------|
| 1 | Happ fresh import, owner device | **INTERIM PASS** | no disconnects after fresh import so far | **B** cache cleared? |
| 2 | Happ after failure, no refresh | **N/A** | no failure observed | — |
| 3 | Happ after TUN off/on | **PENDING** | longer soak | tunnel lifecycle? |
| 4 | Hiddify same URL (owner consent) | **NOT RUN** | — | A vs D |
| 5 | Server-side sub fetch watch #1 | **PASS** | 7353 B stable ×25, 0 HTTP fails | **not F** |
| 6 | Relay probes watch #1 | **PASS** | relay#1 **40/40**, relay#2 **40/40** TCP OK | **not E** (watch window) |

---

## 6. Baseline ops snapshot (2026-06-10, pre-owner-window)

Captured before owner correlated test. **Not a failure window.**

| Probe | Result |
|-------|--------|
| `VPN_BALANCER_PROFILE_OK` | PASS — 7353 B, 6 proxy, dns=yes |
| Subscription stability ×20 | **0 fails**, size **7353–7353** |
| Relay soak ×30 (bvpn-lv) | relay#1 **30/30 OK**, relay#2 **30/30 OK** |
| AMS `remnawave-subscription-page` | **running**, restarts=**0** |
| AMS Happ UA sub fetches (log sample) | HTTP **200**, **7353 B** for Happ iOS UA |
| AMS non-Happ UA fetches | **344 B** sing-box strip (expected) |

**Subscription edge logs (redacted sample):** Happ Android/iOS clients receiving HTTP 200; no 5xx spike in tail. Internal `Go-http-client` probes return 344 B (non-Happ UA).

---

## 7. Owner test timeline

| UTC / local | Event | Evidence |
|-------------|-------|----------|
| ~20:49 UTC | Owner begins fresh Happ test (per prompt) | ops watch started |
| watch #1 | Profile delete + reimport | owner completed fresh import |
| post-watch #1 | Initial browsing after fresh import | **owner: no disconnects observed so far** |
| 20:49–20:52 UTC | Ops watch window #1 | §22 |
| _pending_ | Extended soak 30–60 min | §24 |
| _pending_ | Sleep/resume + Wi‑Fi↔LTE | §24 |
| _pending_ | Optional Hiddify A/B | comparison result |

**During watch #1:** subscription edge log shows **Happ iOS 4.11.0** client fetch **HTTP 200** from external IP (shortUuid **redacted** in logs). Correlates with owner fresh import window.

---

## 8. Device / client evidence

| Field | Value |
|-------|-------|
| Device / OS | **NOT SPECIFIED** by owner (iOS inferred from edge log only) |
| Happ version | **4.11.0 iOS** inferred from edge log — owner verbal not specifying version |
| Network | **NOT SPECIFIED** by owner |
| Soak duration so far | **≥ initial post-import window** (exact minutes not logged) |
| Fresh import completed? | **YES** (owner report) |
| One Auto host visible? | **Expected UX** |
| Failure reproduced? | **NO** (owner interim report) |
| `report.zip` | **NOT COLLECTED** (not needed while stable) |

---

## 9. Happ fresh import result

**INTERIM STABLE** — owner reports **no VPN disconnects after fresh delete/reimport** so far.

| Signal | Result |
|--------|--------|
| Fresh import | **Completed** |
| Initial browsing | **No disconnects observed** (owner verbal) |
| One Auto profile | **Expected** — not a regression signal |
| Prior constant disconnects | **Not reproduced** in this soak window |

**Caveat:** prior symptoms may have been **stale cached profile (B)** or **intermittent client/network (A)**. Interim stability does **not** close the incident without longer soak.

---

## 10. Hiddify A/B result

**NOT RUN** — optional; requires owner consent. Diagnostic only; public recommendation unchanged (**Happ primary**).

---

## 11. Server logs during failure window (watch #1)

**Window:** 2026-06-09 20:49–20:52 UTC · **no 5xx** in tail · all sampled Happ probe fetches **200 / 7353 B**

| Signal | Result |
|--------|--------|
| `remnawave-subscription-page` | **running**, restarts=0 |
| Happ UA fetches (ops + edge) | HTTP **200**; probe-sized responses **7353 B** |
| Happ iOS client during window | HTTP **200** (external IP; uuid redacted in repo doc) |
| Internal non-Happ probes | **344 B** strip (expected) |
| Caddy/Remna errors | **None** in sampled tail |

**Correlation:** No owner failure timestamp to align. If owner reports failure after watch, compare local time to this UTC window.

---

## 12. Subscription edge behavior during failure

**Hypothesis test:** If owner fails while server fetch stays **7353 B / stable** → **not F** (edge serving wrong profile globally).

**Watch #1:** **7353 B stable ×25**, `VPN_BALANCER_PROFILE_OK`, dns=4 servers. **Classification if owner fails:** likely **not F** unless per-account server fetch differs (ops can verify owner account server-side on report — redacted).

---

## 13. Relay probes during failure

**Watch #1 (20:49:59–20:51:44 UTC):** relay#1 **40/40 OK**, relay#2 **40/40 OK** TCP; `TSPU_BLOCK_PROBE_RU_OK` after soak.

If owner failure correlates with RST on one relay IP in `report.zip` → prepare **E** (`approve INCIDENT-002 relay bias relay#1` or `relay#2`). **No relay bias justified from watch #1 alone.**

---

## 14. DNS / VLESS evidence

| Layer | Baseline | Watch #1 |
|-------|----------|----------|
| DoH in live sub | Present (4 DNS servers) | **confirmed** (dns_servers=4) |
| TCP relay probes | PASS | **PASS** 40/40 each |
| TSPU edge from relays | — | **PASS** |
| VLESS handshake | **No safe automated prod probe** | needs `report.zip` or Hiddify A/B if owner fails |

---

## 15. Decision rules

| Observation | Classification |
|-------------|----------------|
| Fresh Happ import still fails; Hiddify stable | **A** Happ-specific stabilization |
| Happ + Hiddify both fail same time | **D/E/F** server/path/VLESS |
| Server sub 7353 B stable during failure | **not F** (global edge OK) |
| RST/log implicates one relay IP only | **E** — relay exclusion/weight proposal |
| Failure only after sleep/resume | **A** OS/client lifecycle |
| DNS-only failure | **C** client DNS/DoH handling |
| All traffic dead; Happ shows connected | **A** false-connected / tunnel lifecycle |
| One visible Auto host in Happ | **Expected UX** — not regression |

---

## 16. Classification (current)

| Verdict | Detail |
|---------|--------|
| **Overall** | **INTERIM STABLE** — failure **not reproduced** after fresh import; incident **open** pending longer soak |
| **Server/profile regression** | **Not confirmed** — watch #1 green; Candidate D active |
| **Most plausible interim cause of prior pain** | **B** stale/partial Happ import; **A** client/network lifecycle still possible |
| **Less likely now** | **F** subscription edge (7353 B stable); **E** relay TCP failure (40/40); **G** infra crash |
| **If failure recurs** | Start **Watch Window #2** at exact timestamp; collect `report.zip`; optional Hiddify A/B |
| **Prod fix justified?** | **NO** |
| **Approval phrase needed now?** | **None** |

---

## 17. Stabilization options (evaluate only — not applied)

### 17.1 Client-side (no prod approval)

| Option | When | Risk |
|--------|------|------|
| Full delete + reimport | Always first | None |
| `report.zip` analysis | After failure | None |
| Disable battery optimization / Private Relay / conflicting VPN | If OS conflict suspected | None |
| Hiddify diagnostic A/B | Owner consent | None (not public rec change) |

### 17.2 Server-side (require explicit approval)

| Option | When | Approval phrase | Rollback |
|--------|------|-----------------|----------|
| Bias/exclude suspect relay in template | **E** proven by report.zip | `approve INCIDENT-002 relay bias <relay#>` | Candidate D snapshot |
| Re-apply Candidate D | Drift detected | `approve emergency restore Candidate D profile` | Pre-D template snapshot |
| Simplified profile (no random balancer) | Happ selector evidence | `approve INCIDENT-002 simplified balancer test` | Template snapshot |
| Single-relay canary | Architecture allows non-global test | `approve INCIDENT-002 single-relay canary` | Template snapshot |
| Rollback Candidate D | **Only if D proven harmful** | `approve rollback Candidate D template` | `.secrets/snapshots/template-pre-candidate-d-apply-*.json` |

**Do not rollback Candidate D** on Happ UX alone or without failure-window evidence.

---

## 18. Stabilization recommendation (current)

| Priority | Action | Owner? | Ops? |
|----------|--------|--------|------|
| **1** | Continue §24 extended soak | **YES** | — |
| **2** | On recurrence: exact timestamp + `report.zip` | **YES** | Watch Window #2 |
| **3** | Optional Hiddify A/B if failure returns | **YES** (consent) | classify A vs D |
| **4** | Prod template change | **NO** — failure not reproduced | — |

**Prod fix justified now?** **NO**.

### Decision (interim)

| Action | Verdict |
|--------|---------|
| Rollback Candidate D | **NO** |
| Re-apply Candidate D | **NO** — no drift |
| Template / Caddy / Remna mutation | **NO** |
| Prod fix | **NO** until failure reproduced with evidence |

---

## 19. Approval phrases (if evidence warrants prod change)

| Scenario | Exact phrase |
|----------|--------------|
| Restore Candidate D after drift | `approve emergency restore Candidate D profile` |
| Relay path bias/exclusion | `approve INCIDENT-002 relay bias relay#1` or `relay#2` |
| Simplified balancer experiment | `approve INCIDENT-002 simplified balancer test` |
| Single-relay canary | `approve INCIDENT-002 single-relay canary` |
| Rollback Candidate D | `approve rollback Candidate D template` |

---

## 20. Rollback plan (any proposed server change)

1. Snapshot template before change → `.secrets/snapshots/template-pre-incident002-*`
2. Apply only with approval phrase from §19
3. Verify: `python ops/vpn_verify_gate.py` (+ LV RU probes)
4. Rollback: restore snapshot PATCH; **no broadcast** unless owner orders
5. Owner: fresh Happ reimport after any template change

---

## 21. Product development freeze

**NO-GO** for P1/P2 features, cabinet journey, billing/device work until INCIDENT-002 reaches **extended soak PASS** or root cause is proven and fixed.

**Interim:** fresh-import stability is encouraging but **insufficient to resume development** without 30–60 min + sleep/resume + network-switch checks.

---

## 22. Watch window #1 — ops record (read-only)

**UTC:** 2026-06-09 20:49:30 – 20:52:00 (approx)

| Probe | Result |
|-------|--------|
| `VPN_BALANCER_PROFILE_OK` | PASS |
| Subscription fetch ×25 | **0 fails**, **7353–7353 B**, dns=4 |
| Relay soak ×40 | r1 **40/40**, r2 **40/40** |
| `TSPU_BLOCK_PROBE_RU_OK` | PASS |
| AMS containers | remnawave, subscription-page, caddy, shop-bot — **running**, 0 restarts |
| LV remnanode | **running**, 0 restarts |
| Subscription edge logs | Happ iOS **4.11.0** external fetch **HTTP 200** during window; ops Happ probes **7353 B**; **no 5xx** |
| VLESS functional probe | **Not available** — TCP-only tooling |

**Owner failure during window:** **not reported to ops.**

---

## 24. Owner interim outcome & next observation plan

### Interim outcome (owner report)

| Field | Value |
|-------|-------|
| Fresh import | **Completed** (delete + reimport from bot/cabinet) |
| Disconnects after import | **None observed so far** |
| Exact soak duration | **Not specified** — at least initial post-import window |
| Device / OS | **Not specified** (iOS likely from edge logs) |
| Network | **Not specified** |

### Current read

- **Server/profile regression:** **not confirmed**
- **Fresh import may have cleared stale Happ profile/cache (B)** — aligns with prior INCIDENT-001 hypothesis
- **Local network / client lifecycle (A)** remains plausible until longer soak
- **No server-side fix justified** while stable

### Next observation (owner)

1. **30–60 minutes** normal browsing (Google, Instagram, Telegram, regular sites)
2. **Browser SaaS long-session** — **INCIDENT-004**: Claude/ChatGPT + GDocs 20–30 min active work; record scope (SaaS-only vs all tabs), DevTools error names (no secrets), comparison VPN
3. **Sleep / resume** test — **INCIDENT-003** (laptop): run `ops/diagnose_windows_vpn_resume.ps1` BEFORE / AFTER-BROKEN / AFTER-RECOVERY; compare with other VPN same sleep duration
4. **Wi‑Fi ↔ LTE** switch while VPN connected (mobile)
5. If failure **recurs**:
   - record **exact local time + UTC**
   - note failure mode and whether Happ shows connected
   - collect **`report.zip`** if possible
   - notify ops → start **Watch Window #2** correlated to timestamp

### Ops if failure recurs

- Re-run §4 read-only watch at failure time
- Verify owner account server-side sub still **7353 B** (redacted)
- No prod mutation without §19 approval phrase

---

## 25. References

- INCIDENT-001: [`INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md`](INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md)
- INCIDENT-003: [`INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md`](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md)
- INCIDENT-004: [`INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md`](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md)
- Candidate D apply: [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md)
- Skill: `vpn-incident-tg-only-ru` — `report.zip` RST workflow
- Probes: `verify_vpn_balancer_profile.py`, `relay_latency_probe.py`, `probe_subscription.py`
- Diagnostics: `ops/diagnose_windows_vpn_resume.ps1`
