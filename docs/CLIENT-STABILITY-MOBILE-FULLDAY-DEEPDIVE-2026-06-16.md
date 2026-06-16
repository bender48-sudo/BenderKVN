# CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16

**Task:** CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-001  
**Date:** 2026-06-16  
**Mode:** passive read-only · **no prod mutation**  
**Parent:** [CLIENT-STABILITY-MOBILE-LOGS-2026-06-16.md](CLIENT-STABILITY-MOBILE-LOGS-2026-06-16.md)

---

## 1. Log inventory

| Source | Type | Date range | Coverage | Safe parse | Raw committed |
|--------|------|------------|----------|------------|---------------|
| `.secrets/diagnostics/access_log_mobile.txt` | Mobile access (Xray/Happ) | 2026-06-16 **19:19–19:40** | **~21 min / 1440 min (1.4%)** | Yes | **NO** |
| `.secrets/diagnostics/subscription_log_mobile.txt` | Happ subscription updater | May 25 – Jun 16 | **Full Jun 16 01:23–22:20** | Yes | **NO** |
| `.local/mobile_fullday_analysis.md` | Analyzer output | Generated | Derived | Yes | **NO** |
| `.local/happ_report6/` | Desktop Windows report | 2026-06-13 | Not mobile; not Jun 16 | N/A | **NO** |
| AMS/server logs | — | — | **Not checked** — no safe automated path this session | — | — |

**Timezone assumption:** access log timestamps treated as local wall time; subscription log **GMT+03:00** aligned to same local day.

---

## 2. Coverage statement

| Question | Answer |
|----------|--------|
| Full-day **access** log available? | **NO** — only evening ~21 min export |
| Full-day **subscription** log available? | **YES** — 92 events on Jun 16 |
| Missing windows | 00:00–19:19 and 19:40–24:00 for traffic proof |
| Conclusion limit | Cannot prove all-day tunnel up/down; can prove **active routing 19:19–19:40** and **import pattern all day** |

### Owner export checklist (CLIENT-MOBILE-OBSERVABILITY-001)

1. Happ → enable logging → export **full-day** `access_log.txt` for days with instability.
2. Export `subscription_log.txt` same day (already have multi-week file).
3. Note phone model, Happ version, **BenderVPN RU** routing Y/N.
4. Optional: lock/unlock times as `--owner-event` notes.
5. Store under `.secrets/diagnostics/` only — never commit.

---

## 3. Access analysis (available window)

| Metric | Value |
|--------|------:|
| Flows | 766 |
| Duration | 20.9 min |
| Flows/min (avg) | ~37 |
| TCP / UDP | 247 / 519 |
| Direct share | 2.2% |
| Error keywords | **0** |

**5-minute buckets:** steady 132–165 flows/bucket — no bucket collapse.

**Route distribution:** even across proxy…proxy-6 (117–139 each) — **not relay2-only**, no single-route dominance.

**Gaps:** ≥5s ×69 · ≥15s ×11 · ≥30s ×2 · ≥60s ×0 · ≥120s ×0  
**Longest gap:** 34.7s at 19:27:28 — traffic resumes on proxy-6; post-gap flows within 30s.

**Interpretation:** During the only available access window the tunnel was **actively routing**, not hard-down. Gaps ≤35s with recovery argue against prolonged outage; they **may** include idle/sleep but are **not proven** sleep/wake without owner timestamps.

---

## 4. Subscription/import analysis (full Jun 16)

| Metric | Value |
|--------|------:|
| Day events | 92 |
| Bender auto-updates | 08:18, 20:18 |
| SafeVPN auto-updates | 01:23, 06:24, 11:27, 16:49, 21:57 |
| UnknownContentType (day) | Every update cycle (batch count=0) |
| Append custom Bender count=1 | After each Bender update |
| Geofile failure bursts | 01:38, 11:55, 13:02, 16:49, 20:03, 20:18, 22:20 |

**Repeating sequence (Bender):** HTTP 200 → ImportResult count=0 (UnknownContentType×2) → **Append custom count=1** OK.

**«0 servers»:** 19 total in full log file — transient UI states; Bender recovers via append custom.

**SafeVPN comparison (control only):** count=5 append path; same UnknownContentType batch noise — suggests **Happ client behavior**, not Bender-only server outage. Do not copy SafeVPN config.

---

## 5. Cross-correlation

**Access window 19:19–19:40 vs subscription events:**

| Finding | Result |
|---------|--------|
| Subscription events during access window | **0** |
| Gaps ≥30s correlated with sub failure (±15 min) | **0 of 2** |
| Import failure bursts during access window | **None** |

**Strongest causal hint:** Import/geofile failures occur at **01:38, 11:55, 13:02, 16:49, 20:03, 20:18** — **outside** the evening traffic window. Traffic was healthy **without** concurrent import activity.

**Counter-evidence to «import caused evening slowness»:** 766 accepted flows, zero errors, no sub events 19:19–19:40.

---

## 6. Server/AMS read-only correlation

**Checked:** NO  
**Reason:** No documented safe read-only AMS log pull in this session; SSH prod grep not executed per guardrails.  
**Verdict:** Server-side outage **NOT SUPPORTED** from client logs alone.

---

## 7. Answers to primary questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Tunnel down vs slow apps? | **Active routing** in 19:19–19:40 window; slowness not proven as hard-down |
| 2 | Sleep gaps in traffic? | Gaps ≤35s exist; **NOT PROVEN** as sleep without lock times |
| 3 | Import failures ↔ gaps? | **NOT SUPPORTED** in access window (zero correlation) |
| 4 | Happ import behavior? | **LIKELY** noisy (UnknownContentType + geofile) but recovers |
| 5 | Multi-proxy related? | **NOT PROVEN** — even distribution, no bad route |
| 6 | Specific proxy group bad? | **NOT SUPPORTED** |
| 7 | Server-side? | **NOT SUPPORTED** (client logs); AMS not checked |
| 8 | Next surface? | **CLIENT-MOBILE-OBSERVABILITY-001** (primary) |

---

## 8. Root-cause classification

| Track | Verdict | Confidence | Next surface |
|-------|---------|------------|--------------|
| A Active traffic health | PARTIAL | medium | CLIENT-MOBILE-OBSERVABILITY-001 |
| B Hard server failure | NOT SUPPORTED | low | — |
| C Multi-proxy instability | NOT PROVEN | low | PROFILE-COMPARISON if needed later |
| D Subscription/import instability | LIKELY (noise) | high noise / low UX causality | CLIENT-SUBSCRIPTION-IMPORT-HAPP-001 |
| E Sleep/wake | NOT PROVEN | low | SLEEPWAKE-001 |
| F OS/background | POSSIBLE | medium | OBSERVABILITY-001 |
| G Happ provider bug | LIKELY | medium | SUBSCRIPTION-IMPORT-HAPP-001 |
| H Bender config fragility | LIKELY | medium | SUBSCRIPTION-IMPORT read-only/staging |
| I Insufficient observability | **CONFIRMED** | high | OBSERVABILITY-001 |

---

## 9. Primary next surface

**CLIENT-MOBILE-OBSERVABILITY-001** — owner must export **full-day mobile access_log**; passive analysis cannot answer constant-use instability with 1.4% day coverage.

**Parallel (not blocking observability):** **CLIENT-SUBSCRIPTION-IMPORT-HAPP-001** — read-only investigation of UnknownContentType / geofile path; **no prod template change**.

---

## 10. Tooling

```powershell
python ops/analyze_mobile_logs.py --fullday --day 2026-06-16 `
  --access .secrets/diagnostics/access_log_mobile.txt `
  --subscription .secrets/diagnostics/subscription_log_mobile.txt `
  --correlate --out .local/mobile_fullday_analysis.md
```

```powershell
python -m pytest tests/test_analyze_mobile_smoke_logs.py tests/test_mobile_log_fullday.py -q
```

---

## 11. Gates (unchanged)

| Gate | Status |
|------|--------|
| Mobile smoke PASS | **OPEN / PENDING** |
| Mobile sleep/wake | **OPEN / NOT PROVEN** |
| Commercial launch | **NO-GO** |
| Selector apply | **NOT ALLOWED** |
