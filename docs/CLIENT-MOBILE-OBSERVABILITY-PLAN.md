# CLIENT-MOBILE-OBSERVABILITY-001 — Mobile log export plan

**Task:** CLIENT-MOBILE-OBSERVABILITY-001  
**Status:** **DONE** (checklist + tooling) — owner export still **PENDING**  
**Parent:** [CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16.md](CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16.md)

---

## 1. Why 21 minutes is insufficient

| Limit | Impact |
|-------|--------|
| Owner uses VPN **all day** | 1.4% coverage cannot prove morning/afternoon instability |
| Sleep/wake | Without full-day access, gaps cannot be mapped to lock/unlock |
| Multi-hour slowness | Subscription log shows import noise, but **traffic proof** missing outside export window |
| Server vs client | Cannot distinguish idle phone vs tunnel down for 22+ hours/day |

**Rule:** Passive mobile stability verdict requires **≥12 h access coverage** OR owner notes + multiple exports same day.

---

## 2. Happ log types (mobile)

| Log | Contains | Full-day? | Notes |
|-----|----------|-----------|-------|
| **access_log** | Accepted Xray flows (route, dest port, timestamp) | **Session/window only** — export what Happ retained | Primary for tunnel up/down |
| **subscription_log** | Auto-update, import, HTTP 200, UnknownContentType, Append custom | **Multi-week** typical | Import noise; not traffic |
| **core_log** | Xray core start/stop, config read | Session fragments | Useful on reconnect |
| **application_log** | Happ app events, TUN, routing profile | Session/day varies | Desktop more complete than mobile |
| **Provider/geofile fetch** | Inside subscription_log | N/A | Google/Happ file failed lines |

**Unknown (document honestly):** Happ mobile may **rotate/truncate** access_log on reconnect or app restart. Treat each export as **“everything Happ still had at export time”**, not guaranteed calendar-day archive. Export **immediately after** bad periods.

---

## 3. When unstable — export within 15 minutes

1. **Do not** disconnect VPN or force-stop Happ before export (if safe).
2. Happ → Settings / Logs / Export (path varies by version) → save:
   - `access_log.txt`
   - `subscription_log.txt`
   - any **core** or **app** log offered
3. Copy to PC: `D:\Va\projects\VPN\.secrets\diagnostics\`
4. Rename:

   ```
   access_log_YYYY-MM-DD_HHMM.txt
   subscription_log_YYYY-MM-DD.txt
   ```

5. Write a **plain text note** (no secrets):

   ```
   2026-06-16 14:05 — Instagram slow, VPN icon on
   2026-06-16 14:07 — locked phone
   2026-06-16 14:12 — unlocked, Telegram OK after ~30s
   2026-06-16 14:12 — Wi-Fi, LTE not tested
   ```

6. **Do not** screenshot subscription QR/URL. Crop sub link from screenshots.

---

## 4. Full-day passive logging (preferred)

**Goal:** One export at end of day covering maximum retained access history.

| Step | Action |
|------|--------|
| 1 | Enable Happ logging (if off). |
| 2 | Use VPN normally all day. |
| 3 | Before midnight (or before app kill): export **access_log** + **subscription_log**. |
| 4 | Record device: model, OS, Happ version, **BenderVPN RU** routing Y/N. |
| 5 | Run validator (PC): |

```powershell
cd D:\Va\projects\VPN
python ops/analyze_mobile_logs.py --validate-coverage --day 2026-06-16 `
  --access .secrets/diagnostics/access_log_mobile.txt `
  --subscription .secrets/diagnostics/subscription_log_mobile.txt `
  --owner-note "2026-06-16 14:05 Instagram slow" `
  --out .local/mobile_observability_report.md
```

```powershell
python ops/analyze_mobile_logs.py --fullday --validate-coverage --day 2026-06-16 `
  --access .secrets/diagnostics/access_log_mobile.txt `
  --subscription .secrets/diagnostics/subscription_log_mobile.txt `
  --correlate --out .local/mobile_fullday_analysis.md
```

---

## 5. Mark events without controlled test

Use `--owner-note` (repeatable):

| Event | Example note |
|-------|----------------|
| Unstable apps | `2026-06-16 14:05 unstable — Instagram slow` |
| Lock | `2026-06-16 14:07 phone locked` |
| Unlock | `2026-06-16 14:12 unlocked` |
| Network | `2026-06-16 18:00 Wi-Fi to LTE` |
| Reconnect feel | `2026-06-16 14:12 internet OK after ~30s` |
| Happ UI | `2026-06-16 14:12 showed connected` |

No UUIDs, URLs, or phone numbers in notes.

---

## 6. Secret hygiene

| Do | Don't |
|----|-------|
| Store under `.secrets/diagnostics/` | Commit logs to git |
| Run analyzer secret scan (patterns only) | Paste sub URL in chat |
| Redact before sharing outside repo | Export screenshots with QR |

Validator reports pattern **names** only: `vless_uri`, `sub_url`, `uuid`, etc.

---

## 7. Success criteria (observability task)

| Criterion | Status |
|-----------|--------|
| Owner checklist documented | **DONE** |
| `--validate-coverage` tooling | **DONE** |
| `--owner-note` ingestion | **DONE** |
| Owner full-day export received | **PENDING** |
| Full-day access ≥12 h or multi-export same day | **PENDING** |

---

## 8. Next after export

1. Run `--validate-coverage` → confirm `access_percent_day`.
2. If still partial → export again after next unstable day; consider exporting **mid-day + evening**.
3. Re-run [FULLDAY deep-dive](CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16.md) analyzer.
4. Only if full-day shows gap↔import correlation → [import readonly follow-up](CLIENT-SUBSCRIPTION-IMPORT-HAPP-READONLY.md).

**Mobile PASS:** still **not** claimable from logs alone.
