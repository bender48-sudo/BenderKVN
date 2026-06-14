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
