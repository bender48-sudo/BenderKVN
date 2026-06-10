# INCIDENT-DIAG-003-004 — Windows Sleep/Resume + Mail Access (Happ report analysis)

**Task:** INCIDENT-DIAG-003-004  
**Date:** 2026-06-10  
**Mode:** documentation / diagnostic analysis only · no prod mutation · no deploy  
**Source:** Happ `report.zip` (2026-06-10, owner-provided) — **not committed to repo**  
**Related incidents:** [INCIDENT-003](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md) · [INCIDENT-004](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md)

---

## 1. Executive summary

| Item | Finding |
|------|---------|
| **User report** | After laptop sleep with VPN on, Wi‑Fi/internet did not recover; reboot required. Later, mail/Google failed temporarily with VPN on; VPN reconnect restored mail. |
| **Log evidence (13:00–13:01)** | `sing-box-tun` crashed (exit code 1); `happ-tun` never reached UP; DNS could not be set; cleanup/restart loop; `happd` service stopped. |
| **Recovery (13:04)** | After system reboot (~13:01:56), Happ daemon connected; TUN created; DNS set on `happ-tun`; normal startup. |
| **Manual reconnect (13:10–13:11)** | Burst of connection-closed errors consistent with user stop/reconnect; second TUN session at 13:11 also healthy. |
| **Mail/Google** | `mail.google.com` DNS took **~3m40s** before reconnect vs **~25ms** after; Chrome→Google proxy traffic visible after recovery; user confirmed mail worked post-reconnect. |
| **INCIDENT-003** | **Stronger evidence** for Happ TUN sleep/resume stale-interface recovery failure (hypothesis A). |
| **INCIDENT-004** | **Partial evidence** — degraded long-lived / SaaS-style flows may recover after TUN refresh; not a dedicated SaaS soak. |
| **Candidate D (server regression)** | **Not confirmed** — recovery after reboot/reconnect argues against general server outage. |
| **Root cause** | **Not fully proven** — report captured **after** reboot/recovery, not the original broken Wi‑Fi state before reboot. |

---

## 2. User report (redacted)

| Field | Value |
|-------|-------|
| **Platform** | Windows 11 laptop (ASUS ZenBook class) |
| **Client** | Happ desktop **2.16.2** · sing-box tun **1.12.12** · Xray core **26.3.27** |
| **Profile** | BenderVPN Auto · routing profile `BenderVPN RU` |
| **Symptom 1** | Sleep with VPN enabled → Wi‑Fi/internet broken on resume → **reboot required** |
| **Symptom 2** | Later session: mail/Google access failed while VPN showed connected → **VPN reconnect fixed mail** |
| **Recovery actions** | System reboot; manual VPN stop/reconnect |

**Redacted from this doc:** subscription URLs, PAC secrets, HWID, personal email, full public IPs, relay hostnames.

---

## 3. Report artifact inventory

Happ `report.zip` contained (analyzed locally, not in git):

| File | Role in analysis |
|------|------------------|
| `happd.log` | Daemon TUN lifecycle, DNS setup, `sing-box-tun` crashes, service stop |
| `tun_log.txt` | sing-box traffic, DNS timing, connection-closed errors, Chrome/Google flows |
| `application_log.txt` | Happ UI connect/disconnect, TUN start (secrets redacted from doc) |
| `ipconfig all.txt` | Post-recovery adapter/DNS state |
| `route print.txt` | Post-recovery routing (no BEFORE-BROKEN snapshot) |
| `systeminfo.txt` | OS build, **system boot time** |
| `versions.txt` | Happ/core/tun versions |
| `settings.json`, `routing.json`, `selected_server.json` | Profile context — **not quoted** (may contain sensitive endpoints) |

---

## 4. Timeline (local UTC+3, 2026-06-10)

### 4.1 Failure window — TUN crash loop (~13:00–13:01)

| Time | Event | Source |
|------|-------|--------|
| 13:00:17 | Happ client connected to `happd` (v2.16.2) | `happd.log` |
| 13:00:28 | TUN interface cleanup (stale GUID removed) | `happd.log` |
| 13:00:29 | DNS configure attempted for `happ-tun` → wait for UP | `happd.log` |
| 13:00:30 | **`sing-box-tun` crashed, exit code 1** — restart scheduled | `happd.log` |
| 13:00:39 | **`happ-tun` not UP** after 10s timeout | `happd.log` |
| 13:00:39 | **Cannot set DNS — interface `happ-tun` not found** | `happd.log` |
| 13:00:54 – 13:01:27 | Repeated stale-process cleanup, crash, DNS failure cycle | `happd.log` |
| 13:01:36 | Service stop requested | `happd.log` |
| 13:01:37 | `happd` daemon stopped; all managed processes stopped | `happd.log` |

**Pattern match:** Same signature as **2026-06-08 13:04** in the same `happd.log` (TUN removed → interface not UP → DNS failure → service stop). Suggests **recurring** Happ TUN recovery failure, not a one-off.

### 4.2 System reboot (~13:01:56)

| Time | Event | Source |
|------|-------|--------|
| 13:01:56 | **System boot** (report `systeminfo`: last boot) | `systeminfo.txt` |

Report does **not** contain route/DNS snapshots from the broken pre-reboot state.

### 4.3 Post-reboot recovery (~13:04)

| Time | Event | Source |
|------|-------|--------|
| 13:04:02 | Happ daemon connected successfully | `happd.log`, `application_log.txt` |
| 13:04:13 | Connected to **BenderVPN Auto** | `application_log.txt` |
| 13:04:14 | TUN start; DNS detour `direct` | `application_log.txt` |
| 13:04:14–15 | `happ-tun` UP (~929ms); DNS **1.1.1.1** set successfully | `happd.log` |
| 13:04:14–16 | sing-box started; Wi‑Fi default interface updated; connectivity probes | `tun_log.txt` |

### 4.4 Degraded session + manual reconnect (~13:05–13:11)

| Time | Event | Source |
|------|-------|--------|
| 13:04:40 – 13:09+ | Frequent `connection closed` errors on VLESS path to relay (**72.56.x.x:443**) and local xray/socks paths | `tun_log.txt` |
| 13:07:57 | `mail.google.com` DNS resolved after **~3m40s** (same query tracker) | `tun_log.txt` |
| 13:08:02 | Chrome initiated multiple Google/mail-related connections via TUN/proxy | `tun_log.txt` |
| 13:10:00 – 13:10:03 | **Burst** of connection-closed errors; `wsasend: connection aborted by host` — consistent with **manual VPN stop** | `tun_log.txt` |
| 13:10:19 | `mail.google.com` DNS still slow (**~22s**) | `tun_log.txt` |
| 13:11:08–09 | Second TUN session: `happ-tun` UP; DNS set; sing-box started (~1.2s) | `happd.log`, `tun_log.txt` |
| 13:11:10 | `mail.google.com` DNS **~25ms** | `tun_log.txt` |

---

## 5. Technical findings

### 5.1 Happ TUN lifecycle (INCIDENT-003 / hypothesis A)

Evidence supports **Happ desktop failing to recreate a healthy `happ-tun` after a disruptive event** (consistent with sleep/resume or stale interface):

1. TUN GUID cleanup precedes crash loop.
2. `sing-box-tun` exits with code **1** repeatedly.
3. Windows never reports `happ-tun` as UP within 10s.
4. DNS assignment fails because the interface is missing.
5. Daemon gives up and stops.
6. **Reboot + clean start** restores normal TUN/DNS.

This aligns with INCIDENT-003 owner narrative: *another VPN survives sleep; BenderVPN/Happ breaks until reboot sometimes.*

### 5.2 Mail / Google degradation (INCIDENT-004 partial)

| Metric | Before reconnect (~13:07–13:10) | After reconnect (~13:11) |
|--------|--------------------------------|--------------------------|
| `mail.google.com` DNS latency | **~220s** then **~22s** | **~25ms** |
| Chrome → Google HTTPS | Present but amid connection-closed noise | Resumed with fast DNS |
| User-visible mail | Failed (user report) | Worked (user report) |

**Interpretation (cautious):**

- Degradation is consistent with **unhealthy TUN / tunnel state** affecting DNS and long-lived browser flows — overlaps INCIDENT-004 hypothesis A/C (false-connected / stale TUN).
- This is **not** a controlled 20–30 min SaaS soak; mail failure may be downstream of the same TUN incident or a separate transient tunnel issue.
- **VPN reconnect as fix** supports client-side tunnel lifecycle over server-wide outage.

### 5.3 What this does **not** prove

| Claim | Status |
|-------|--------|
| Candidate D server-side template regression | **Unconfirmed** — reconnect restored service |
| General BenderVPN server outage | **Unconfirmed** — post-reboot path worked |
| Sleep event timestamp | **Missing** — inferred from symptom + boot time + TUN crash |
| Wi‑Fi adapter state during failure | **Missing** — no BEFORE-BROKEN `ipconfig` / `route print` |
| Happ vs Hiddify on same sleep test | **Missing** |
| SaaS-only scope (Claude banner class) | **Missing** — mail/Google evidence only |

### 5.4 Post-recovery network snapshot (report capture time)

From `ipconfig` (redacted summary):

- **`happ-tun` present** with DNS **1.1.1.1** (expected Happ TUN DNS).
- **Wi‑Fi adapter connected** with ISP/Yandex DNS (**77.88.8.8**) on physical interface — dual DNS context normal when TUN routes DNS.
- Captured in **AFTER-RECOVERY** state only.

---

## 6. Hypothesis confidence update

| Hypothesis | Code | Before this report | After this report |
|------------|------|--------------------|-------------------|
| Happ TUN fails after sleep/resume | A | Medium (owner report) | **Higher** (log-correlated crash loop + prior 2026-06-08 repeat) |
| Stale route / dead TUN | A | Medium | **Higher** (interface not found / not UP) |
| DNS stuck on dead tunnel | C | Medium | **Higher** (DNS set failures during crash loop) |
| VLESS/server regression (Candidate D) | D | Low–medium | **Unchanged / not supported** |
| Profile×Happ interaction | 8 | Low | Low (no A/B profile test) |
| Long-session SaaS drops | INCIDENT-004 | Open | **Partial** (mail DNS latency + reconnect fix) |

---

## 7. Recommended next diagnostics (owner runbook)

**Goal:** Capture **AFTER-BROKEN** state **before reboot** on the next sleep/resume failure.

### 7.1 Repro steps

1. Connect **BenderVPN Auto** in Happ; confirm internet + mail work.
2. Note time (local + UTC).
3. Put laptop to **sleep 10–30 minutes** (usual failure duration).
4. Resume — **do not reboot yet** if broken.

### 7.2 Collect before reboot (broken state)

| Artifact | Command / action |
|----------|------------------|
| Happ report | Happ → export **`report.zip`** |
| IP config | `ipconfig /all` |
| Routes | `route print` |
| Interfaces | `netsh interface show interface` |
| Adapters | `Get-NetAdapter \| Format-Table Name, Status, LinkSpeed -Auto` |
| DNS | `Get-DnsClientServerAddress -AddressFamily IPv4` |
| WLAN events | Event Viewer → Windows Logs → System (WLAN/network around resume time) |
| Optional script | `ops/diagnose_windows_vpn_resume.ps1 -Phase AfterBroken` |

### 7.3 Functional tests (record yes/no)

| Test | Pass? |
|------|-------|
| Wi‑Fi shows connected? | |
| `ping 1.1.1.1` works? | |
| `nslookup mail.google.com` works? | |
| Browser opens mail.google.com? | |
| Happ status (connected / error text)? | |
| VPN off/on fixes without reboot? | |
| Happ disconnect alone fixes? | |
| Only reboot fixes? | |

### 7.4 After recovery

Run `ops/diagnose_windows_vpn_resume.ps1 -Phase AfterRecovery` (or same manual commands).  
Optional: same sleep test with **comparison VPN** on same laptop.

**Do not collect:** subscription URLs, tokens, full Happ config export, private keys.

---

## 8. Stabilization (evaluate only — not applied)

| Option | Notes |
|--------|-------|
| Disconnect Happ before sleep | User habit; reduces exposure |
| VPN off/on runbook for mail/SaaS | Document when reconnect may help |
| Profile canary | Requires `approve INCIDENT-003 desktop profile canary` |
| Prod / relay / Candidate D change | **Not justified** from this report alone |

---

## 9. Acceptance checklist (INCIDENT-DIAG-003-004)

| Criterion | Met |
|-----------|-----|
| Raw `report.zip` not committed | Yes |
| Sensitive values redacted in doc | Yes |
| Conclusion cautious | Yes |
| Candidate D remains unconfirmed | Yes |
| INCIDENT-003 stronger evidence | Yes |
| INCIDENT-004 partial evidence | Yes |
| Next diagnostics actionable | Yes (§7) |

---

## 10. References

- INCIDENT-003: [`INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md`](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md)
- INCIDENT-004: [`INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md`](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md)
- INCIDENT-002: [`INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md`](INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md)
- Script: [`ops/diagnose_windows_vpn_resume.ps1`](../ops/diagnose_windows_vpn_resume.ps1)
- Launch gate: [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md) (G1)
- Closeout: [`AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md`](AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md)
