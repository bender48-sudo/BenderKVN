# CLIENT-STABILITY-HAPP-RELAY2-LAB-001 — Owner relay #2 lab (Happ TUN)

**Task:** CLIENT-STABILITY-HAPP-RELAY2-LAB-001  
**Date:** 2026-06-13  
**Mode:** owner-only lab · **no prod mutation** · **no deploy** unless explicitly approved  
**Parent:** [CLIENT-STABILITY-HAPP-RECOVERY-Capture](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md) · [INCIDENT-DIAG-2026-06-12](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md)

**Hypothesis:** report(6) Bender segment shows ~336 ERROR / 5 min — mostly **established connection reset** on long-lived flows (Cursor Agent WebSocket, Google Docs). Errors are **strongly relay #1 biased** (`72.56.0.145:443`); relay #2 (`46.173.28.252`) barely appears. TUN startup is fast; DirectIp leak is fixed — do **not** rollback `happRouting`.

**Goal:** Force Happ traffic through **relay #2 only** (or one deterministic relay #2 outbound) to see whether relay #1 / random 6-way selector causes the resets.

---

## Selected lab method — **Option A (local JSON variant)**

| Option | Verdict |
|--------|---------|
| **A — local Happ/Xray JSON, relay #2 only** | **Selected.** Generator strips relay #1 (+ NL) outbounds; pins `Intl_Direct` + `Intl_Stealth` to `proxy-4/5/6`. Owner imports manually. |
| B — Happ routing-only tweak | **Not sufficient** — relay selection lives in **subscription core JSON**, not Happ routing profile. |
| C — Remna support config on prod | **Fallback only** if Happ cannot import local JSON; requires **explicit owner approval** before any panel user/template change. |

**Prod mutation required for this lab:** **No** (default path).

---

## Safety (must hold)

| Rule | Lab profile |
|------|-------------|
| TG / IG / Meta proxied | **Yes** — `Intl_Stealth` rules unchanged; selector = relay #2 pool only |
| No `fallbackTag=direct` | Validated by generator |
| No `geoip:ru` in Happ DirectIp | Use existing **BenderVPN RU** routing profile (unchanged) |
| DirectIp private-only | Do **not** edit routing profile for this test |
| In-core relay `/32` → direct | Relay #1 rule removed; relay #2 kept (anti-loop) |
| Global users / prod template | **Untouched** |

---

## Owner steps

### 0. Prerequisites

- Clean Bender-only evidence already captured (report(6) qualifies if final state was Bender).
- Happ: TUN ON, system proxy OFF, routing **BenderVPN RU** ON (fixed DirectIp).

### 1. Export or fetch current subscription JSON

**From Happ (preferred if no panel token locally):**

1. Fully quit Happ → reopen.
2. Refresh subscription on **BenderVPN Auto** (prod profile — note baseline).
3. Export/copy full subscription JSON to a local file, e.g. `%USERPROFILE%\Downloads\bender_sub.json`  
   (Happ: subscription detail → copy/export if available; or use bot subscription URL in browser with Happ User-Agent only on a trusted machine).

**From repo (if `.secrets/panel-token.txt` or `PANEL_TOKEN` available):**

```powershell
cd D:\Va\projects\VPN
python ops/generate_happ_relay2_lab_profile.py --short YOUR_SHORT_UUID --write-json .local\lab_relay2.json
```

Use a path **outside git** (`.local\` is not committed).

### 2. Generate lab profile

**Relay #2 pool (3 paths, random among relay #2 SNIs):**

```powershell
python ops/generate_happ_relay2_lab_profile.py --from-json path\to\bender_sub.json --write-json .local\lab_relay2.json
```

**Single deterministic outbound (`proxy-4` only):**

```powershell
python ops/generate_happ_relay2_lab_profile.py --from-json path\to\bender_sub.json --single --write-json .local\lab_relay2_one.json
```

Expect stdout: `HAPP_RELAY2_LAB_PROFILE_OK` and remarks containing `[LAB relay2`.

Validate only:

```powershell
python ops/generate_happ_relay2_lab_profile.py --from-json .local\lab_relay2.json --validate-only
```

### 3. Import into Happ (manual)

1. **Add new profile** from `.local\lab_relay2.json` (do not overwrite prod subscription row if possible).
   - Happ desktop: import from file / clipboard (same flow as other manual JSON imports).
   - Profile name will show lab remarks: `BenderVPN Auto [LAB relay2-only — do NOT refresh sub]`.
2. **Do NOT press Refresh subscription** on the lab profile — that pulls prod 6-way relay pool again.
3. Confirm routing profile **BenderVPN RU** still active (`useRouting=true`).
4. Connect **lab profile** in **TUN** mode (system proxy OFF).

### 4. Test matrix — **15–20 minutes**

| Check | Action |
|-------|--------|
| **Cursor Agent** | Open Agent panel; watch for “Reconnecting…” loops |
| **Google Docs / Gmail** | Long-lived tab, edit or scroll |
| **Telegram** | Web or desktop |
| **IP check** | `https://ipinfo.io` or `https://ifconfig.me` (not check.ru — RU direct by design) |
| **RU direct** | `https://ya.ru`, `https://vk.com` — should stay direct (routing profile) |

### 5. PASS / FAIL

| **PASS** | **FAIL** |
|----------|----------|
| Cursor stops constant reconnecting | Same reconnect / reset symptoms |
| Google Docs / Gmail stable | Connection reset storm returns |
| No ERROR storm in Happ logs | — |
| TUN stays connected | — |
| TG / IG still work via proxy | — |

**On FAIL:** export **clean Bender-only** `report.zip` **before** switching to SafeVPN (see [recovery capture](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md)). Then try **`--single`** variant or escalate to Option C (owner-approved support config).

**On PASS:** relay #1 or random 6-way selector is likely culprit — discuss prod mitigation (latency trim / relay health) **separately**; do not auto-apply from this lab.

### 6. Rollback

1. Disconnect lab profile.
2. Delete lab profile from Happ.
3. Reconnect normal **BenderVPN Auto** (refresh sub if needed).

No server-side rollback required for Option A.

---

## Tooling

```powershell
python -m py_compile ops/generate_happ_relay2_lab_profile.py
python -m pytest tests/test_generate_happ_relay2_lab_profile.py -q
python ops/happ_routing_directip_guard.py
python ops/analyze_happ_report_tun.py path\to\report.zip
```

---

## Option C fallback (explicit approval only)

If Happ cannot import local JSON:

1. Owner approves **one** support user or short-lived template variant with `RELAY2_SELECTOR` only (same logic as `ops/latency_selector_autotrim.py` mode `relay2_only`).
2. Apply via existing patch tooling **only after approval** — not part of default lab path.
3. Revoke/restore prod template when test ends.

---

## Related variants

See [CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md §4](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md) — Variant **C** (relay #2-only) and **D** (single-relay). This doc implements **C/D** locally without prod mutation.

---

## report(7) — owner evidence (2026-06-14)

**Task:** CLIENT-STABILITY-HAPP-RELAY2-LAB-EVIDENCE-001
**Local artifact:** `.secrets/diagnostics/report-7-relay2-lab.zip` (not committed)
**Analyzer:** `python ops/analyze_happ_report_tun.py .secrets/diagnostics/report-7-relay2-lab.zip`

### Session context

| Field | Value |
|-------|-------|
| Happ | 2.16.2 (546) · core 26.3.27 · tun 1.12.12 |
| Profile | **BenderVPN Auto [LAB relay2-only — do NOT refresh sub]** |
| TUN | **ON** |
| System proxy | **OFF** |
| Routing | **BenderVPN RU** ON (`useRouting=true`) |
| Session span | ~43 min (14.06 23:15–23:58 local) |
| Final state | Clean Bender lab profile — usable as evidence |

### Profile integrity (confirmed)

| Check | report(7) |
|-------|-----------|
| Relay #1 outbounds (`proxy`…`proxy-3`) | **Absent** |
| Relay #2 outbounds | **Present** — `proxy-4`, `proxy-5`, `proxy-6` |
| `Intl_Direct` / `Intl_Stealth` selector | Pinned to `proxy-4/5/6` |
| `fallbackTag=direct` | **None** |
| Happ DirectIp | 6 private/system CIDRs; **no `geoip:ru`**; **no relay IP overlap** |
| In-core relay `/32` → direct | Expected anti-loop (1 relay IP) |

### Error characterization

| Class | report(7) | report(6) baseline |
|-------|-----------|-------------------|
| `i/o timeout` | **0** | Dominant pre-fix; reduced post-fix |
| `open outbound connection` / dial | **0** | Part of pre-fix DirectIp storm |
| `connection forcibly closed` | 207 | Long-lived reset class |
| `connection download closed` | 194 | Primary report(6) failure class |
| `connection upload closed` | 85 | Secondary reset class |
| `aborted by host machine` | **0** | — |
| Error-like lines (total) | **283** (~6.6/min) | **~336 / 5 min** (~67/min) |
| Relay #1 log bias | **None** | **Strong** (`72.56.0.145:443`) |
| DirectIp leak signal | **No** | Fixed before report(6) |
| Old timeout storm | **Not reproduced** | Yes (report(6) era) |

TUN startup: **~1.2 s** first connect; **~1.7 s** after wake reconnect.

### Sleep/wake (separate track)

| Signal | report(7) |
|--------|-----------|
| Sleep/wake detected | **Yes** — timer gaps at 23:51 and 23:58 |
| Daemon IPC disconnect on wake | **Yes** |
| Wake recovery subscription refresh | **Yes** — risky on lab row (may pull prod 6-way pool) |

Sleep/wake recovery **not proven stable** on relay2 lab; do not fold into active-session PASS.

### Verdict

| Track | Verdict | Rationale |
|-------|---------|-----------|
| **Active session (relay2 lab)** | **SOFT PASS** | relay2-only profile used; relay #1 excluded; TUN fast; DirectIp leak absent; no open/i/o timeout storm; error rate ~10× lower than report(6); remaining errors are connection close/reset class |
| **Sleep/wake** | **FAIL / OPEN** | Daemon IPC disconnect + wake recovery path; subscription refresh on wake |
| **Happ desktop launch gate** | **OPEN** | One owner capture ≠ 30–60 min controlled soak; sleep/wake unresolved |

**Interpretation:** relay2 lab **materially improves active-session evidence** vs report(6). **Relay #1 remains a strong suspect** on the normal 6-way profile — **not enough to change prod default**. Needs repeat active-session confirmation or controlled selector strategy before production decision. **Sleep/wake remains open.**

### Caveats

- Do **not** rollback fixed `happRouting`.
- Do **not** make relay2 prod default from one test.
- Do **not** mark Happ desktop fully launch-ready.
- Wake recovery forced subscription update on lab profile — owner should **disable auto-refresh on lab row** or re-import after sleep tests.

### Next steps

| Step | Action |
|------|--------|
| **A** | Repeat owner active-session test on relay2 lab **30–60 min** without sleep (see recovery doc §9) |
| **B** | If repeat SOFT PASS → design controlled prod strategy: reduce/exclude relay #1 from selector; preserve rollback; **owner approval required** |
| **C** | Keep desktop fallback v2rayN path ready ([CLIENT-STABILITY-DESKTOP-FALLBACK.md](CLIENT-STABILITY-DESKTOP-FALLBACK.md)) |
| **D** | Sleep/wake remains separate track — CLIENT-SMOKE-001 |

---

## CLIENT-STABILITY-HAPP-RELAY2-REPEAT-SOAK-001 — repeat active soak (decision gate)

**Task:** CLIENT-STABILITY-HAPP-RELAY2-REPEAT-SOAK-001
**Status:** **PASS** — repeat relay2 active soak (report(8) · 2026-06-15)
**Prior evidence:** report(7) · commit `2e2bca9` — active **SOFT PASS**; sleep/wake contaminated
**Mode:** owner-run · **no prod mutation** · **no deploy**

### Why repeat

report(7) improved active-session evidence (~6.6/min vs report(6) ~67/min) but included **sleep/wake** and was a single capture. One more **sleep-free** 30–60 min soak is required before any controlled prod selector change.

### Profile (existing lab — do not regenerate)

**BenderVPN Auto [LAB relay2-only — do NOT refresh sub]**

Local JSON (not in git): `.local/lab_relay2.json` · `.local/lab_relay2_one.json`

### Rules (mandatory)

| Rule | Required |
|------|----------|
| TUN | **ON** |
| System proxy | **OFF** |
| Routing | **BenderVPN RU** ON |
| Refresh subscription on lab row | **NO** |
| Sleep / lock laptop | **NO** during test |
| Switch to SafeVPN before export on FAIL | **NO** |
| Reimport / routing toggle mid-soak | **NO** |

### Duration and activities

**30–60 minutes** continuous active work:

1. **Cursor Agent** — active use; count visible “Reconnecting…”
2. **Google Docs** — edit and scroll throughout
3. **Gmail** — load and use at least once
4. **Telegram** — web or desktop active
5. **ipinfo.io / ifconfig.me** — once at start and near end
6. **ya.ru / vk.com** — once (RU direct expected)

### Verdict criteria

| Verdict | Criteria |
|---------|----------|
| **PASS** | 30–60 min; Cursor not repeatedly reconnecting; Docs/Gmail/TG usable; no connected-but-dead; no Happ crash; no SafeVPN needed |
| **SOFT PASS** | Isolated lag/reconnect; work remains usable — record caveats |
| **FAIL** | Repeated Cursor reconnect; Docs/Gmail/TG unusable; connected-but-no-traffic; Happ crash; SafeVPN required |

### If FAIL

1. Export **`report.zip`** while still on the **lab profile**.
2. Store locally: `.secrets/diagnostics/report-8-relay2-repeat-soak.zip` (not committed).
3. Analyze:

```powershell
python ops/analyze_happ_report_tun.py path\to\report.zip
```

4. Then disconnect / switch if needed for work.

### Owner result record

| Field | Value |
|-------|-------|
| Date | 2026-06-15 (export ~00:57 local) |
| Duration | **~59 min** post-wake active segment (23:59 → 00:57); full export ~102 min from 14.06 23:15 |
| Verdict | **PASS** — repeat relay2 active soak |
| Cursor | Stable; no visible degradation / reconnect loops |
| Docs / Gmail / TG | Usable; **no site incidents** observed |
| Symptoms | None requiring SafeVPN |
| report.zip exported? | **Yes** — while on lab profile |
| Local artifact | `.secrets/diagnostics/report-8-relay2-repeat-soak.zip` (not committed) |

### Decision gate (after owner result)

| Repeat verdict | Gate outcome | Next step |
|----------------|--------------|-----------|
| **PASS** ✓ | Eligible to **design controlled prod selector strategy** | **CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001** — **not automatically approved**; explicit owner approval required |
| **FAIL** | **No prod selector change** | Analyze report; consider `lab_relay2_one.json` or escalate; keep v2rayN fallback |

**Relay2 lab now has two positive active-session evidences:** report(7) **SOFT PASS** + report(8) repeat **PASS**. **Relay #1 remains a strong suspect** on the normal 6-way profile. **Eligible to design controlled selector strategy** — **not automatically approved for prod change**. **Sleep/wake remains open** under CLIENT-SMOKE-001.

**Do not:** make relay2 prod default · rollback `happRouting` · mark Happ desktop fully launch-ready · treat this export as sleep/wake PASS.

---

## report(8) — repeat active soak evidence (2026-06-15)

**Task:** CLIENT-STABILITY-HAPP-RELAY2-REPEAT-SOAK-001
**Local artifact:** `.secrets/diagnostics/report-8-relay2-repeat-soak.zip` (not committed)
**Analyzer:** `python ops/analyze_happ_report_tun.py .secrets/diagnostics/report-8-relay2-repeat-soak.zip`

### Session context

| Field | Value |
|-------|-------|
| Happ | 2.16.2 (546) · core 26.3.27 · tun 1.12.12 |
| Profile | **BenderVPN Auto [LAB relay2-only — do NOT refresh sub]** |
| TUN | **ON** |
| System proxy | **OFF** |
| Routing | **BenderVPN RU** ON |
| Export span | 14.06 23:15 → 15.06 00:57 local (~102 min total) |
| **Repeat active segment** | Post-wake **~59 min** (14.06 23:59 → 15.06 00:57) — grades repeat soak |
| Final state | Clean Bender lab profile — usable as evidence |

### Profile integrity (confirmed)

| Check | report(8) |
|-------|-----------|
| Relay #1 outbounds (`proxy`…`proxy-3`) | **Absent** |
| Relay #2 outbounds | **Present** — `proxy-4`, `proxy-5`, `proxy-6` |
| `lab_relay2_only` | **true** |
| Happ DirectIp | 6 private/system CIDRs; **no `geoip:ru`**; **no relay IP overlap** |
| `dial_open_errors` | **0** |
| `outbound_direct_to_relay` | **0** |
| `happ_directip_leak_signal` | **false** |
| Relay #1 log bias | **0** |

### Error characterization (full export + repeat segment)

| Class | Full export | Repeat segment (~59 min post-wake) | report(6) baseline |
|-------|-------------|-------------------------------------|-------------------|
| `i/o timeout` | **3** | **3** | Dominant pre-fix storm |
| `dial_open` / open outbound | **0** | **0** | Part of DirectIp storm |
| `download_closed` / `upload_closed` / `forcibly_closed` | Present (long-lived reset class) | ~523 error-like lines (~8.9/min) | Primary report(6) failure class |
| Error storm (i/o + dial) | **No** | **No** | Yes (report(6) era) |
| Happ crash during repeat segment | **No** (owner + log) | — | — |

Remaining log noise is **connection close/reset class** — does **not** correlate with owner-visible failure (no incidents; Cursor stable; no SafeVPN).

### Sleep/wake (separate track — do not fold into active PASS)

| Signal | report(8) |
|--------|-----------|
| Sleep/wake in export | **Yes** — timer gap 23:51; wake recovery 23:57–23:58 (same session as report(7) start) |
| Used as sleep/wake evidence | **No** — repeat soak grades **post-wake active segment only** |
| Sleep/wake verdict | **OPEN** — CLIENT-SMOKE-001 |

### Verdict

| Track | Verdict | Rationale |
|-------|---------|-----------|
| **Repeat relay2 active soak** | **PASS** | ~59 min post-wake; owner: no site incidents; Cursor stable; no SafeVPN; profile integrity OK; no i/o timeout / dial-open storm; no active-session crash |
| **Sleep/wake** | **OPEN** | Wake events present in export; not proven stable |
| **Happ desktop launch gate** | **OPEN** | Normal Bender row soak still pending; sleep/wake unresolved; not commercial launch GO |

**Interpretation:** **Repeat relay2 active soak PASS** confirms report(7) direction. **Relay #1 remains a strong suspect** on prod 6-way selector — **eligible to design controlled selector strategy**, **not automatically approved for prod change**.

---

## CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001 — recommended if repeat PASS/SOFT PASS

**Status:** **ELIGIBLE — NOT STARTED** — REPEAT-SOAK-001 **PASS** recorded; requires **explicit owner approval** before any prod change
**Mode:** controlled prod change · rollback mandatory · **no broad launch** until owner smoke passes

| Requirement | Detail |
|-------------|--------|
| Snapshot | Current prod subscription / template / panel settings before change |
| Dry-run | Selector diff — show relay #1 exclusion impact on `Intl_Direct` / `Intl_Stealth` |
| Change | Controlled reduce/exclude relay #1 from normal **BenderVPN Auto** selector |
| Constraints | No `fallbackTag=direct`; preserve TG/IG/Meta stealth rules; DirectIp guard unchanged |
| Verify | Owner smoke on prod profile post-change |
| Rollback | Documented revert command / template restore |
| Launch | Desktop launch gate stays **OPEN** until smoke result + sleep track separate |

**Not authorized from repeat soak alone** — owner must explicitly approve this task.
