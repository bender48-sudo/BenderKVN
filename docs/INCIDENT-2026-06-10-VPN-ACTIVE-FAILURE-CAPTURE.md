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
| **Failure reproduced in this ops pass?** | **NO** — owner correlated test not yet run |
| **Server/profile regression?** | **None observed** in baseline window |
| **Next required step** | Owner executes §3 protocol; ops runs §4 watch window at agreed UTC time |
| **Prod change this pass?** | **None** |

INCIDENT-001 proved infrastructure/profile health from read-only probes but did **not** capture an owner failure window. INCIDENT-002 adds **time-correlated evidence collection** and a **controlled stabilization decision tree** — still **no mutation** until evidence + explicit approval.

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
| 1 | Happ fresh import, owner device | **PENDING** | — | Owner §3 |
| 2 | Happ after failure, no refresh | **PENDING** | — | false-connected? |
| 3 | Happ after TUN off/on | **PENDING** | — | tunnel lifecycle? |
| 4 | Hiddify same URL (owner consent) | **PENDING** | — | A vs D |
| 5 | Server-side sub fetch same window | **BASELINE OK** | 7353 B stable ×20 | not F |
| 6 | Relay probes same window | **BASELINE OK** | 30/30 OK both relays | not E (baseline) |

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
| _pending_ | Owner announces test start | device, Happ version |
| _pending_ | Profile delete + reimport | screenshot optional |
| _pending_ | 10–15 min browsing test | failure log |
| _pending_ | Ops watch window | §6 updated row |
| _pending_ | Optional Hiddify A/B | comparison result |

---

## 8. Device / client evidence

| Field | Value |
|-------|-------|
| Device / OS | **NOT COLLECTED** |
| Happ version | **NOT COLLECTED** |
| Fresh import completed? | **NOT COLLECTED** |
| One Auto host visible? | **Expected if UX normal** |
| Failure reproduced? | **NOT YET** |
| `report.zip` | **NOT COLLECTED** |

---

## 9. Happ fresh import result

**NOT TESTED** — awaiting owner §3 run.

---

## 10. Hiddify A/B result

**NOT RUN** — optional; requires owner consent. Diagnostic only; public recommendation unchanged (**Happ primary**).

---

## 11. Server logs during failure window

**NOT CORRELATED** — no owner failure timestamp yet.

Baseline (§6): subscription edge healthy; no container restarts; Happ-class fetches return full JSON size.

---

## 12. Subscription edge behavior during failure

**Hypothesis test:** If owner fails while server fetch stays **7353 B / stable** → **not F** (edge serving wrong profile globally).

**Baseline:** stable. **Failure-window:** pending.

---

## 13. Relay probes during failure

**Baseline:** 30/30 TCP OK both relays. **Failure-window:** pending.

If failure correlates with RST on one relay IP in `report.zip` → prepare **E** mitigation proposal (bias/exclude relay path).

---

## 14. DNS / VLESS evidence

| Layer | Baseline | Failure window |
|-------|----------|----------------|
| DoH in live sub | Present (4 DNS servers) | pending |
| TCP relay probes | PASS | pending |
| VLESS handshake | **No automated prod probe** | `report.zip` or Hiddify A/B |

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
| **Overall** | **UNKNOWN** — owner failure not captured |
| **Server/profile** | **No regression** in baseline |
| **Leading hypothesis** | **A/B/D** pending owner window — stale client cache, Happ tunnel behavior, or VLESS-layer intermittent |

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
| **1** | Run §3 owner protocol at agreed time | **YES** | coordinate watch |
| **2** | Collect `report.zip` on failure | **YES** | analyze RST |
| **3** | Optional Hiddify A/B | **YES** (consent) | classify A vs D |
| **4** | Prod template change | **NO** until §15 rules + approval phrase | — |

**Prod fix justified now?** **NO** — insufficient correlated evidence.

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

**NO-GO** for P1/P2 features, cabinet journey, billing/device work until INCIDENT-002 classification is **client-confirmed** or **server fix deployed + owner soak PASS**.

---

## 22. References

- INCIDENT-001: [`INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md`](INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md)
- Candidate D apply: [`APPLY-2026-06-10-VPN-CANDIDATE-D.md`](APPLY-2026-06-10-VPN-CANDIDATE-D.md)
- Skill: `vpn-incident-tg-only-ru` — `report.zip` RST workflow
- Probes: `verify_vpn_balancer_profile.py`, `relay_latency_probe.py`, `probe_subscription.py`
