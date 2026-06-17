# CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-001 — Windows Happ Dropout Diagnosis

**Task:** CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-001
**Date:** 2026-06-17
**Mode:** Focused desktop client-stability investigation (read-only report analysis; no prod mutation)
**Input:** `report(10).zip` → analyzed at `.secrets/diagnostics/report-10-desktop-happ.zip` (ignored; **not committed**)
**Analyzer:** [`ops/analyze_happ_report_tun.py`](../ops/analyze_happ_report_tun.py) (extended this task)
**Parent / related:** [`CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md`](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md) ·
[`INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md`](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md)

> Read-only analysis. No prod/Remna/Caddy/template/subscription/routing mutation.
> Endpoints redacted to non-identifying tokens (`ep_<hash>:port`) — no raw IPs/UUIDs/URLs.

---

## 1. Report inventory

| File | Parseable | Signal |
|------|-----------|--------|
| versions.txt | yes | Happ 2.16.2 (546), core 26.3.27, tun (sing-box) 1.12.12, AntiFilter 17 |
| settings.json | yes | TUN=true, systemProxy=false, routing=BenderVPN RU, useRouting=true |
| selected_server.json | yes | "BenderVPN Auto", VLESS/TCP/REALITY, 6 proxy outbounds, balancers Intl_Direct + Intl_Stealth |
| routing.json | yes | activeProfile BenderVPN RU; directIp = private CIDRs only (no geoip:ru) |
| tun_log.txt | yes | 47,777 lines; 14:35–22:53; ~3.5k reset errors |
| application_log.txt | yes | 4 TUN startups (all fast); daemon IPC disconnect 18:08; sleep/wake recovery |
| happd.log | yes | historical crashes (exit codes); current sessions healthy |
| route print.txt / ipconfig all.txt | yes | Check Point + Npcap adapters present; happ-tun up |
| tasklist.txt | yes | happ/core/sing-box present; 4 VPN-class processes |
| systeminfo.txt | yes | Windows 11 |

**Secrets risk:** report contains real IPs/sub URLs → kept under `.secrets/` only; all tool output redacted.

---

## 2. Current session summary

- **Active profile:** BenderVPN Auto (clean Bender final state — usable as evidence).
- **Routing:** BenderVPN RU, `useRouting=true`, TUN on / system proxy off.
- **TUN startup:** **fast and healthy** — 4 startups at 996 / 1106 / 1371 / 1509 ms, incl. the 22:32 session. `current_session_fast=true`.
- **Time range:** 2026-06-17 14:35 → 22:53.
- **Errors:** 3,543 error-like lines (download_closed 3,518; forcibly_closed 3,299; upload_closed 353; io_timeout 13).

---

## 3. Error analysis

- **Dominant error class:** `connection download closed … forcibly closed by the remote host` on **long-lived** connections (durations 19s, 1m37s — established streams torn down mid-flight, not dial failures).
- **Dominant endpoint:** **a single relay/exit endpoint `ep_20e413bd:443` carries 80.3% of all reset errors** (2,829 / 3,525) and is the most-used path (9,537 hits).
- **Second relay `ep_d1a601f6:443` is healthy** — 7 errors / 2,008 hits. The other delivery path is fine.
- **Local SOCKS `ep_…:10808`** — 115 resets (normal teardown of long client connections).
- **Errors by category:** relay_or_web_tls 2,845; tun_gateway_or_private 565; local_socks 115.
- **Errors by hour:** 14h≈1026, 15h≈1107, 16h≈554, 22h≈1365 — cluster in active-browsing windows.
- **Telegram** endpoints present and **not** in the error top → Telegram path working.

---

## 4. Routing / config analysis

| Check | Result |
|-------|--------|
| Profile integrity | OK — 6 proxy outbounds, candidate-D shape, import_ok |
| Balancers | Intl_Direct + Intl_Stealth (stealth split intact) |
| geoip:ru in Happ directIp | **NO** (regression not present) |
| relay server IP in Happ directIp | **NO** (overlap 0) — no Happ DirectIp relay leak |
| In-core relay→direct rules | present (2 rules / 10 IPs) — **expected** xray anti-loop self-bypass |
| FallbackTag=direct | not detected |
| proxy-N / registry | candidate-D relay×6 shape consistent with current live Auto profile; registry generator is dry-run/synthetic so no positional mismatch surfaced |

**Conclusion:** no routing/config regression. The earlier `geoip:ru` DirectIp leak fix is **still holding**.

---

## 5. Windows / local environment

- **Check Point VPN adapter present** (Track F secondary) + **Npcap** — possible interference, but does not explain single-endpoint dominance (a local-stack fault would not spare the second relay).
- happ-tun interface up; DNS set; no Wi-Fi default-route conflict observed.
- Daemon IPC disconnect at 18:08 (`QLocalSocket` / sleep-wake) — transient, reconnected.

---

## 6. Root-cause classification

| # | Track | Verdict | Evidence | Counter-evidence | Confidence |
|---|-------|---------|----------|------------------|------------|
| 1 | TUN startup failure (current) | NOT SUPPORTED | 4 fast startups incl. 22:32 | — | High |
| 2 | TUN daemon crash (current) | NOT SUPPORTED | crashes are historical only; clean stop=exit 0 | 91 historical crash entries | High |
| 3 | Client heartbeat/session timeout | POSSIBLE | one daemon IPC disconnect 18:08 (sleep/wake) | recovered; single event | Low |
| 4 | **Relay endpoint remote resets** | **LIKELY (primary)** | one relay `ep_20e413bd:443` = 80.3% of resets; long-lived "forcibly closed by remote" | could be upstream/TSPU on that path | Med-High |
| 5 | DirectIp / direct relay leak regression | NOT SUPPORTED | overlap 0; geoip:ru absent | — | High |
| 6 | Xray self-loop captured by TUN | NOT SUPPORTED | outbound_direct_to_relay 0; in-core direct rules expected | docker_local hits are private-range noise | Med |
| 7 | Route profile misconfiguration | NOT SUPPORTED | stealth split intact; no FallbackTag=direct | — | High |
| 8 | Server-side relay instability | LIKELY (primary, same as #4) | single most-loaded relay resets; second relay clean | needs read-only relay-side confirmation | Med-High |
| 9 | Local Windows/Check Point conflict | POSSIBLE (secondary) | Check Point + Npcap adapters present | would not spare second relay | Low-Med |
| 10 | Happ provider/app noise | POSSIBLE (noise only) | PremiumFallback happ.su fetch fail = app update check, not VPN drop | — | Med |
| 11 | Insufficient evidence | NOT — evidence sufficient | clear single-endpoint dominance | — | — |

**Primary finding:** one relay/exit endpoint (the most-loaded path) is resetting long-lived TCP connections while the second relay path stays healthy → **relay-path instability on a single endpoint**, not a client-wide, TUN, or routing failure.

---

## 7. Primary next fix / action

**`CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001`** (proposed) — controlled, owner-gated:

1. **Read-only** server-side check of the dominant relay endpoint (xray/relay logs, conntrack, CPU/mem, upstream resets) — no mutation.
2. Owner/staging **canary profile** that de-weights or excludes the resetting relay from the Auto selector, keeping the healthy second relay — validate stability client-side.
3. If confirmed relay-side: drain/replace that relay via the registry onboarding path (separate owner-approved prompt).

**This does NOT require production apply now.** Any selector/subscription/template change is a separate **APPROVE PROD APPLY** step (see §9).

---

## 8. What this blocks / does not change

- Does **not** mark desktop PASS (single report; one relay path degraded).
- Does **not** change production profile, routing, or any node.
- Blocks claiming desktop client stability GO until the relay-path fix is validated.
- Does **not** affect mobile / billing / cabinet / NL-canary scope.

---

## 9. Owner approval prompt (if a server-side fix is chosen)

> **APPROVE DESKTOP RELAY-PATH READ-ONLY CHECK** — authorize a read-only SSH inspection of the
> dominant relay endpoint to confirm server-side resets; OR
> **APPROVE OWNER RELAY-PATH CANARY** — generate an owner/staging profile that de-weights the
> resetting relay (no broad apply) to validate the healthy second path.

No production subscription/template/routing mutation is performed without this.

---

## 10. Safety statement

| Item | Value |
|------|-------|
| Prod mutation | **NO** |
| Deploy | **NO** |
| Remna/Caddy/template/subscription changes | **NO** |
| VPN routing changes (live) | **NO** (local read-only analysis only) |
| Raw report committed | **NO** (`.secrets/` only) |
| Secrets / raw IPs printed | **NO** (redacted to `ep_<hash>:port`) |
| Desktop PASS claimed | **NO** |
| 300/30k GO claimed | **NO** |
