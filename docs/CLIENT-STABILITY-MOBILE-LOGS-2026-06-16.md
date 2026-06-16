# CLIENT-STABILITY-MOBILE-LOGS-001 — Mobile log analysis (2026-06-16)

**Task:** CLIENT-STABILITY-MOBILE-LOGS-001  
**Date:** 2026-06-16  
**Mode:** read-only analysis · **no prod mutation**  
**Parent:** [CLIENT-STABILITY-MOBILE-SMOKE-001](CLIENT-STABILITY-MOBILE-SMOKE.md)

---

## 1. Owner report

- Connection was **unstable in places** on mobile.
- After phone **sleep**, tunnel may take a **long time** to reconnect.
- Sleep/wake failure is **not proven** from logs alone — needs timed owner test with lock/unlock notes.

---

## 2. Files analyzed

| File | Role | Committed? |
|------|------|------------|
| `access_log (2).txt` (owner Telegram export) | Xray/Happ accepted flows | **NO** — copied locally to `.secrets/diagnostics/` (gitignored) |
| `subscription_log.txt` (owner Telegram export) | Happ subscription updater | **NO** — same |

**Tool:** `python ops/analyze_mobile_smoke_logs.py --access-log … --subscription-log … --out .local/mobile_smoke_log_summary.md`

---

## 3. Access log findings

| Metric | Value |
|--------|------:|
| Time range | 2026/06/16 **19:19:27** → **19:40:18** (~21 min) |
| Accepted flows | **766** |
| TCP / UDP | 247 / 519 |
| Proxy total | 749 |
| Direct | 17 (**2.2%**) |
| Error keywords | **0** (error/failed/timeout/reset/closed/disconnect/refused/rejected) |
| Sleep/wake markers | **0** |

**Route distribution (not relay2-only):**

| Route | Count |
|-------|------:|
| proxy-4 | 139 |
| proxy-3 | 130 |
| proxy-2 | 124 |
| proxy | 121 |
| proxy-5 | 118 |
| proxy-6 | 117 |
| direct | 17 |

**Coarse destination hints (proxy path):** meta_hint=434, google_hint=33, telegram_hint=23, dns_resolver via port 53=174.

**Top ports:** 443 (563), 53 (174), 5222 (10 — Telegram-class), 5228 (4).

**Inter-flow gaps:** ≥5s ×69 · ≥15s ×11 · ≥30s ×2 · ≥60s ×0.

**Interpretation:** Active routing during the window; traffic spread evenly across **all six** proxy tags. Gaps may be idle or sleep but **cannot be classified** without owner lock/unlock timestamps overlapping 19:19–19:40.

---

## 4. Subscription log findings

| Metric | Value |
|--------|------:|
| Total lines | 2463 |
| Date span | Mon May 25 → Tue Jun 16 |
| HTTP 200 | 193 |
| UnknownContentType | 384 |
| ImportResult count=0 | 384 |
| Append custom count=1 (total) | 140 |
| Append custom **BenderVPN** | 108 |
| Append custom **SafeVPN** (count=5 path) | 52 events with count=5; 1 Bender-context Safe tag |
| Sub BenderVPN successfully updated | 107 |
| «1 servers» UI | 107 (expected for Auto) |
| «0 servers» UI | 19 |
| Google file failed | 146 |
| Happ file failed | 145 |
| Required value was null | 134 |

**Jun 16 timeline (selected):**

- **01:23** — SafeVPN auto-update: HTTP 200 → batch count=0 (UnknownContentType×2) → **Append custom count=5** OK.
- **01:38–01:39** — Google file failed, Happ file failed, `Required value was null` (provider/geofile fetch).
- **06:24** — SafeVPN repeat: same 200 → UnknownContentType → Append count=5.
- **08:18** — BenderVPN auto-update starts (access log window is **evening** 19:19+ — separate session).

**Interpretation:** Known Happ pattern — batch import skips some outbounds (`UnknownContentType`), then **Append custom** succeeds for BenderVPN Auto. Provider/geofile errors (`Google`/`Happ` failed, `Required value was null`) are **client-side import noise** unless correlated with owner-visible reconnect failure at the same time. **Not** evidence of server-down.

---

## 5. Root-cause classification

| Track | Verdict | Evidence | Next test | Prod change? |
|-------|---------|----------|-----------|--------------|
| **A** Active traffic path OK | **CONFIRMED** | 766 accepted; multi-proxy; no access errors | Timed sleep/wake test | NO |
| **B** Mobile sleep/wake reconnect | **NOT PROVEN** | Owner report; no wake markers in logs | Lock/unlock matrix §6 | NO |
| **C** Subscription/provider import | **LIKELY** (noise + occasional 0 servers) | UnknownContentType + geofile failures; Append custom still OK | CLIENT-SUBSCRIPTION-IMPORT-HAPP-001 | NO |
| **D** Multi-proxy selector | **POSSIBLE** | Even spread proxy…proxy-6 | Profile comparison if instability persists | NO |
| **E** Server outage | **NOT SUPPORTED** | No failed dials in access log | — | NO |
| **F** App/OS background network | **POSSIBLE** | Sleep/wake report | Battery optimization off; repeat test | NO |
| **G** Insufficient evidence | **CONFIRMED** | Logs alone cannot prove post-sleep failure | Owner timestamps on next export | NO |

---

## 6. What is proven / not proven

**Proven:**

- VPN routed live traffic on **2026-06-16 ~19:19–19:40**.
- Multi-relay pool in use (not relay2-only).
- BenderVPN subscription import **eventually succeeds** via Append custom despite batch parse noise.

**Not proven:**

- Mobile smoke **PASS** (speed, apps, lock/LTE).
- Sleep/wake reconnect time or failure.
- That subscription import errors **caused** tunnel instability.

---

## 7. Owner-controlled sleep/wake test (next)

Run on **Happ + BenderVPN RU**; record **exact times** (no secrets in notes).

| Step | Action | Pass band |
|------|--------|-----------|
| 1 | Fresh connect on Wi‑Fi | Connect ≤ ~10 s |
| 2 | Open Telegram, Google, Instagram, Gmail, ya.ru | Y/N each |
| 3 | Lock phone **2 min** | Note lock time |
| 4 | Unlock → immediately Telegram + browser | Note unlock + time until usable |
| 5 | Reconnect time | **<10 s PASS** · 10–30 s SOFT · 30–120 s WARN · **>120 s FAIL** |
| 6–8 | Repeat on LTE; Wi‑Fi↔LTE switches | Same bands |
| 9 | Optional: compare SafeVPN profile | Diagnostic only |
| 10 | On FAIL: export Happ logs immediately | Local only |

**Required owner notes:** lock time, unlock time, time internet worked, Happ connected/disconnected UI, manual reconnect Y/N, network switch effect.

Re-run analyzer with correlation:

```powershell
python ops/analyze_mobile_smoke_logs.py `
  --access-log .secrets/diagnostics/access_log_mobile.txt `
  --subscription-log .secrets/diagnostics/subscription_log_mobile.txt `
  --owner-event "2026-06-16 19:32:00 phone locked" `
  --owner-event "2026-06-16 19:35:00 unlocked"
```

---

## 8. Backlog status after this analysis

| ID | Status |
|----|--------|
| **CLIENT-STABILITY-MOBILE-LOGS-001** | **DONE** |
| **CLIENT-STABILITY-MOBILE-SLEEPWAKE-001** | **OPEN / P0** |
| **CLIENT-STABILITY-MOBILE-SMOKE-001** | **OPEN / P0** — PASS not recorded |
| **CLIENT-SUBSCRIPTION-IMPORT-HAPP-001** | **OPEN / P1** |
| **CLIENT-STABILITY-MOBILE-PROFILE-COMPARISON-001** | **OPEN / P2** — only if instability persists after sleep/wake test |

**Launch gates unchanged:** mobile smoke **PENDING**; commercial launch **NO-GO**; selector apply **not allowed**.
