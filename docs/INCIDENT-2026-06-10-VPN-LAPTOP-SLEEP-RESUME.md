# INCIDENT-003 — Laptop Sleep/Resume VPN Failure (Happ + BenderVPN)

**Date opened:** 2026-06-10  
**Mode:** incident analysis + diagnostic tooling only · no prod mutation  
**Branch:** `product-referral-cabinet-ui-v1`  
**Prior:** [`INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md`](INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md) (INCIDENT-002), [`INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md`](INCIDENT-2026-06-10-VPN-STABILITY-PROD-AUDIT.md) (INCIDENT-001)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| **New signal** | Owner: **another VPN survives laptop idle/sleep**; **BenderVPN via Happ does not** |
| **Symptom after resume** | VPN breaks; internet may not recover; traffic in broken route/tunnel; Happ shows error; **reboot sometimes required** |
| **Server/profile regression** | **Still not confirmed** — Candidate D active; infra probes green |
| **Confidence shift** | **Higher** for **Happ/OS TUN-route-DNS sleep-resume failure (A)** and **profile×client interaction (8)** |
| **Diagnostic evidence** | **INCIDENT-DIAG-003-004** — Happ `report.zip` (2026-06-10): TUN crash loop + DNS failure before reboot; **CLIENT-STABILITY-001** — Happ UI confirms «Failed to start TUN process via daemon» + service stop (2026-06-10, Happ 2.16.2) — see [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md), [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) |
| **Track split (CLIENT-STABILITY-001)** | **Track A (this incident):** Happ TUN/daemon failure · **Track B (separate):** Bender Proxy mode fails while other VPN Proxy works — do **not** merge root causes |
| **Prod fix justified now?** | **NO** — need **AFTER-BROKEN** route/DNS snapshots (pre-reboot) + comparison matrix |
| **INCIDENT-002 interim stable** | Compatible — active browsing may work; **sleep/resume is separate failure mode** |
| **INCIDENT-004 (browser SaaS)** | **OPEN** — long-session SaaS drops may share TUN lifecycle; see [`INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md`](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md) |

---

## 2. Owner observation (verbatim pattern)

| VPN | Idle / sleep behavior |
|-----|----------------------|
| **Another VPN** (unspecified product) | Laptop can sleep/idle; internet **reconnects normally** on return |
| **BenderVPN via Happ** | After sleep/idle return: connection **breaks**; internet **does not recover**; broken route/tunnel; Happ **connection error**; **reboot** sometimes required |
| **Happ UI (2026-06-10, TUN mode)** | «Connection interrupted because Happ service stopped unexpectedly» · reason: «**Failed to start TUN process via daemon**» (Happ **2.16.2**, Windows) |
| **Bender Proxy (separate track)** | Owner reports Bender **Proxy mode does not work**; **another VPN Proxy works** — see Track B in [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) — **not** part of INCIDENT-003 root cause until smoke proves otherwise |

**Interpretation:** Not generic “bad Wi‑Fi”. Happ UI text **confirms TUN daemon start failure** — supports **client/OS TUN lifecycle (Track A)** on desktop, distinct from server TCP/Relay health. **Do not collapse** Track B (Bender Proxy failure) into this incident.

---

## 3. Why this changes confidence

| Before INCIDENT-003 | After INCIDENT-003 |
|---------------------|-------------------|
| Intermittent disconnects could be stale cache, relay, or edge | **Reproducible class:** sleep/resume on **laptop** |
| Server probes sufficient to rule out F/E/G | Server probes **still** rule out F/E/G; **cannot** explain stuck routes after resume |
| Happ “one Auto host” UX clarified | Focus shifts to **TUN teardown** after S3/S4 sleep |
| INCIDENT-002 interim PASS (active use) | **Sleep/resume still untested** — now **primary desktop gate** |

**Server-side regression:** still **not confirmed**.  
**Happ/OS client lifecycle:** **more likely** until route/DNS evidence collected.

---

## 4. Primary hypotheses

| # | Hypothesis | Code |
|---|------------|------|
| 1 | Happ fails to restore TUN after sleep/resume | A |
| 2 | Stale default route through dead TUN | A |
| 3 | DNS stuck on dead VPN interface | C |
| 4 | BenderVPN profile routing/DNS/balancer triggers Happ resume bug | 8 |
| 5 | VLESS/Reality reconnect fails after sleep (TCP probes OK) | D |
| 6 | OS power management kills Happ / network extension | A |
| 7 | Conflict with another VPN adapter/DNS/profile residue | A |
| 8 | Desktop Happ needs simplified profile canary | 8 |

---

## 5. Diagnostic protocol — Windows (primary)

**Helper script (optional):** `ops/diagnose_windows_vpn_resume.ps1`  
**Output:** `.secrets/diagnostics/vpn-resume-*.txt` — **gitignored; do not commit**

### When to capture

| Phase | When |
|-------|------|
| **BEFORE** | VPN connected, browsing OK, **before** lock/sleep |
| **AFTER-BROKEN** | Immediately after resume if internet broken — **before reboot** |
| **AFTER-RECOVERY** | After VPN off/on, Happ disconnect, or reboot restores internet |

### Manual commands (if not using script)

```powershell
# Timestamp
Get-Date -Format "yyyy-MM-dd HH:mm:ss K"

ipconfig /all
route print
Get-NetAdapter | Format-Table Name, InterfaceDescription, Status, LinkSpeed -Auto
Get-NetIPConfiguration | Format-List
Get-DnsClientServerAddress -AddressFamily IPv4 | Format-Table InterfaceAlias, ServerAddresses -Auto
Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Format-Table DestinationPrefix, NextHop, InterfaceAlias, RouteMetric -Auto
netsh interface show interface

Test-NetConnection 1.1.1.1 -Port 443 -WarningAction SilentlyContinue | Format-List
nslookup google.com
```

**Do not collect:** subscription URLs, tokens, full Happ config export, private keys.

### Owner notes per phase

- Happ status (connected / error text)
- Screenshot of Happ if error shown
- Whether **VPN off/on** fixes internet
- Whether **Happ disconnect** alone fixes internet
- Whether **only reboot** fixes internet

---

## 6. Diagnostic protocol — macOS (if applicable)

```bash
date
scutil --nwi
netstat -rn
networksetup -listallnetworkservices
networksetup -getdnsservers Wi-Fi   # or active service name
ifconfig
route -n get default
ping -c 3 1.1.1.1
nslookup google.com
```

Same three phases: BEFORE / AFTER-BROKEN / AFTER-RECOVERY. Redact secrets.

---

## 7. Owner test protocol

### A. BenderVPN / Happ (laptop)

1. Fresh import **BenderVPN Auto** in Happ (if not already done).
2. Connect; confirm browsing OK.
3. Run **BEFORE** snapshot (`-Phase Before`).
4. Lock laptop / sleep for **usual failure duration** (same as daily use).
5. Resume. If broken:
   - **Do not reboot first**
   - Run **AFTER-BROKEN** snapshot (`-Phase AfterBroken`)
   - Record Happ error text + time (local + UTC)
   - Test: **VPN off/on** — does internet return?
   - Test: **Happ disconnect** — does internet return?
   - Run **AFTER-RECOVERY** snapshot when fixed (or note “only reboot fixed”)

### B. Comparison VPN (same laptop)

1. **BEFORE** snapshot (other VPN connected).
2. Same sleep duration.
3. **AFTER** snapshot on resume.
4. Record: routes/DNS/default gateway recovered? internet OK?

### C. Optional Hiddify A/B (diagnostic only)

- Same BenderVPN subscription URL, same laptop, same Wi‑Fi, same sleep duration.
- **Do not** change public Happ recommendation.
- If Hiddify survives resume but Happ fails → **Happ-specific**.
- If both fail → server/profile/VLESS more likely.

---

## 8. Comparison matrix

| Test | Happ+BenderVPN | Other VPN | Hiddify+BenderVPN |
|------|----------------|-----------|-------------------|
| Active browsing | INCIDENT-002 interim OK | — | optional |
| Sleep/resume | **FAIL reported** | **PASS reported** | pending |
| Happ `report.zip` / happd TUN crash | **YES** — 2026-06-10 + prior 2026-06-08 pattern | — | — |
| Happ UI TUN daemon error | **YES** — «Failed to start TUN process via daemon» (2026-06-10) | — | — |
| Bender Proxy fallback | **FAIL reported** (Track B — separate) | other VPN Proxy **PASS** | pending CLIENT-SMOKE-002 |
| Route/DNS snapshots (AFTER-BROKEN) | **pending** — report is post-reboot | **pending** | pending |
| Reboot required? | **sometimes** (confirmed 2026-06-10) | no (owner) | pending |

---

## 9. Route / DNS interpretation guide

| Observation after broken resume | Likely cause |
|---------------------------------|--------------|
| Default route → Happ/TUN adapter; tunnel dead | Stale route / false-connected |
| DNS servers on VPN interface; nslookup fails | DNS stuck on dead tunnel |
| Gateway ping OK; 1.1.1.1 fails | Tunnel / default route broken |
| 1.1.1.1 OK; nslookup fails | DNS-only issue |
| Happ disconnect restores internet | Happ cleanup failure |
| Only reboot restores internet | Severe adapter/route/DNS stuck state |
| Other VPN OK; Happ+BenderVPN bad | Happ or profile×Happ |
| Happ other profile OK; BenderVPN bad | **Our profile structure (8)** |
| Happ + Hiddify both fail same sub | Server/profile/VLESS **(D/F)** |

---

## 10. Stabilization options (evaluate only — not applied)

### 10.1 Happ desktop mitigation (no prod approval)

| Option | Blast radius |
|--------|--------------|
| Disconnect Happ before sleep | User habit — **recommended** until Track A resolved |
| Full Happ restart as administrator | Try before reboot |
| Document off/on recovery | Docs only |
| **Proxy mode fallback** | **Not recommended yet** — Bender Proxy reported failing (Track B); see CLIENT-SMOKE-002 |
| Collect `report.zip` after broken resume | Diagnostic |
| Hiddify comparison on same laptop | Diagnostic only |
| Karing / alt client | CLIENT-SMOKE-003 — evaluation only |

### 10.2 Profile simplification canary (requires approval)

| Option | Approval phrase |
|--------|-----------------|
| Simplified Happ profile for one smoke user (no global template) | `approve INCIDENT-003 desktop profile canary` |
| Remove random balancer / simpler DNS / fixed primary relay | same |

**Not available today** without architecture check — global template affects all users.

### 10.3 Relay bias

Only if `report.zip` RST correlates with one relay after resume — `approve INCIDENT-002 relay bias relay#1` or `relay#2`.

### 10.4 Client split (diagnostic / policy — not public rollout)

| Idea | Status |
|------|--------|
| Happ primary mobile if stable | Current policy |
| Different desktop client if Happ sleep fails consistently | **Owner decision** after evidence |
| Karing migration | **Not recommended** — not Auto-equivalent |

### 10.5 Emergency prod change

Only with correlated evidence + §11 approval phrase. **Not justified now.**

---

## 11. Approval phrases

| Scenario | Phrase |
|----------|--------|
| Desktop profile canary (non-global if possible) | `approve INCIDENT-003 desktop profile canary` |
| Simplified balancer/DNS test | `approve INCIDENT-003 simplified balancer test` |
| Relay bias (from RST evidence) | `approve INCIDENT-002 relay bias relay#1` or `relay#2` |
| Rollback Candidate D | `approve rollback Candidate D template` — **only if D proven harmful** |

---

## 12. What remains unknown

- **AFTER-BROKEN** route/DNS snapshots **before reboot** (report captured post-recovery only)
- Exact sleep/resume timestamp correlated to TUN crash loop
- Whether VPN off/on or disconnect alone recovers internet **without reboot**
- Whether Hiddify with same sub survives sleep/resume
- Whether other VPN uses TUN or different driver model
- Whether profile simplification would fix Happ resume without harming mobile

**Now known (INCIDENT-DIAG-003-004 + CLIENT-STABILITY-001):** Windows 11 **10.0.26200**, Happ **2.16.2**, sing-box tun **1.12.12**, Xray **26.3.27**; `happd.log` shows `sing-box-tun` exit 1 + `happ-tun` not UP + DNS failure (~13:00–13:01); Happ UI confirms **TUN daemon start failure** + service stop; system reboot ~13:01:56; recovery ~13:04. **Track B open:** Bender Proxy fails, other VPN Proxy works. Details: [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md), [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md).

---

## 13. Prod fix justified?

**NO** — until owner supplies:

1. **AFTER-BROKEN** route + DNS snapshot (Windows script output)
2. Comparison **AFTER** snapshot from other VPN (same sleep duration)
3. Optional Hiddify A/B result
4. Happ `report.zip` if available after broken resume

---

## 14. References

- **INCIDENT-DIAG-003-004:** [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md) — Happ `report.zip` analysis (2026-06-10)
- **CLIENT-STABILITY-001:** [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) — Track A/B split, runbook, CLIENT-SMOKE-001..003
- INCIDENT-002: [`INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md`](INCIDENT-2026-06-10-VPN-ACTIVE-FAILURE-CAPTURE.md)
- INCIDENT-004: [`INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md`](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md)
- Script: [`ops/diagnose_windows_vpn_resume.ps1`](../ops/diagnose_windows_vpn_resume.ps1)
- Skill: `vpn-incident-tg-only-ru` — RST / routing analysis
