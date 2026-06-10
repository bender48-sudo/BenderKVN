# INCIDENT-DIAG — Happ TUN Daemon Failure + Bender Proxy Fallback (Windows)

**Task:** CLIENT-STABILITY-001
**Date:** 2026-06-10
**Mode:** documentation + diagnostic planning only · no prod mutation · no deploy
**Client:** Happ desktop **2.16.2** (Windows 11 **10.0.26200**)
**Related:** [INCIDENT-003](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md) · [INCIDENT-004](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md) · [INCIDENT-DIAG-003-004](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md)

---

## 1. Executive summary — two independent tracks

This incident **must not** be collapsed into a single root cause. Owner evidence on Windows (Happ 2.16.2) supports **two parallel investigations**:

| Track | Code | Symptom class | Primary hypothesis | Candidate D server regression? |
|-------|------|---------------|-------------------|------------------------------|
| **A — Happ TUN / daemon** | **A** | TUN mode fails; Happ service stops; reboot often required after sleep/resume | Happ desktop fails to start `sing-box-tun` / `happ-tun` after disruptive OS event (sleep/resume, stale interface) | **Not confirmed** — log pattern is client-side TUN lifecycle |
| **B — Bender Proxy connectivity** | **B** | BenderVPN Auto in **Proxy mode** does not work; **another VPN profile in Proxy mode works** on same machine/network | Bender profile / subscription path / routing emit issue — **separate from Happ TUN daemon** | **Not confirmed** — needs Proxy-mode smoke vs comparison VPN |

**Both tracks remain OPEN** until CLIENT-SMOKE-001/002/003 evidence is collected.

---

## 2. Owner evidence (2026-06-10, redacted)

### 2.1 Track A — Happ TUN / daemon failure

| Field | Value |
|-------|-------|
| **Profile** | BenderVPN Auto · TUN mode |
| **Happ UI (verbatim pattern)** | «Connection interrupted because Happ service stopped unexpectedly» |
| **Happ UI reason (verbatim pattern)** | «Reason: Failed to start TUN process via daemon» |
| **Recovery** | Computer **often requires reboot** to recover after this failure |
| **Context** | Consistent with sleep/resume or stale TUN state (INCIDENT-003) |
| **Screenshot** | Owner provided — **not committed** (may contain sensitive network/profile data) |

**Interpretation:** Happ UI explicitly confirms **TUN process start failure via daemon** — aligns with `happd.log` crash loop in INCIDENT-DIAG-003-004 (`sing-box-tun` exit 1, `happ-tun` not UP, DNS set failure). **Strengthens Track A** (Happ/OS TUN lifecycle), not server-wide outage.

### 2.2 Track B — Bender Proxy mode failure

| Field | Value |
|-------|-------|
| **Profile** | BenderVPN Auto · **Proxy mode** (TUN disabled) |
| **Symptom** | Bender profile in Proxy mode **does not work** |
| **Control** | **Another VPN profile in Proxy mode works** on same Windows machine and network |
| **Implication** | Failure is **not** generic “Proxy mode broken on this PC” — points to **Bender profile/connectivity**, not Happ TUN daemon alone |

**Interpretation:** Track B is **independent evidence**. Do **not** attribute to “Happ issue” only. Do **not** attribute to “server issue” only without Bender Proxy smoke. Proxy fallback is **not validated** as a workaround until CLIENT-SMOKE-002 passes.

---

## 3. What each track does and does not prove

| Claim | Track A (TUN) | Track B (Proxy) |
|-------|---------------|-----------------|
| Happ TUN daemon fails to start after sleep/disruption | **Supported** (UI + prior `happd.log`) | N/A |
| Stale `happ-tun` / route / DNS after resume | **Likely** — needs AFTER-BROKEN snapshots | N/A |
| Candidate D template regression | **Unconfirmed** | **Unconfirmed** |
| Bender subscription/profile path broken in Proxy mode | N/A | **Suspected** — needs smoke |
| Happ client universally broken on Windows | **Partial** — TUN path; Proxy untested for Bender | **No** — other VPN Proxy works |
| Reboot required for recovery | **Reported** | Unknown |

---

## 4. Windows client stability — diagnostic runbook

**Helper script:** [`ops/diagnose_windows_vpn_resume.ps1`](../ops/diagnose_windows_vpn_resume.ps1)
**Output:** `.secrets/diagnostics/vpn-resume-*.txt` — **gitignored; do not commit**

### 4.1 When to capture (all tracks)

| Phase | When |
|-------|------|
| **BEFORE** | VPN connected, browsing OK, before sleep or before Proxy test |
| **AFTER-BROKEN** | Immediately on failure — **before reboot** |
| **AFTER-RECOVERY** | After reconnect, Happ restart, or reboot |

### 4.2 Track A — TUN failure bundle (pre-reboot priority)

Run **before reboot** when Happ shows TUN/daemon error:

| # | Artifact / command |
|---|-------------------|
| 1 | Happ → export **`report.zip`** |
| 2 | Screenshot of Happ error text (store privately; redact if sharing) |
| 3 | `ipconfig /all` |
| 4 | `route print` |
| 5 | `Get-NetAdapter \| Format-Table Name, InterfaceDescription, Status, LinkSpeed -Auto` |
| 6 | `Get-DnsClientServerAddress -AddressFamily IPv4` |
| 7 | `netsh interface show interface` |
| 8 | `nslookup mail.google.com` |
| 9 | `ping 1.1.1.1` |
| 10 | Browser test: mail.google.com, google.com |
| 11 | Optional: `pwsh -File ops/diagnose_windows_vpn_resume.ps1 -Phase AfterBroken` |

**Functional recovery tests (record Y/N):**

| Test | Record |
|------|--------|
| Happ full restart as **administrator** fixes TUN? | |
| VPN off/on fixes without reboot? | |
| Happ disconnect alone restores internet? | |
| **Only reboot** fixes? | |

### 4.3 Track B — Proxy mode bundle

With **TUN disabled**, BenderVPN Auto in **Proxy mode**:

| # | Test |
|---|------|
| 1 | Happ built-in connectivity test (if available) |
| 2 | Browser: generic site, Google, YouTube |
| 3 | `mail.google.com` |
| 4 | Public IP check through proxy (compare with proxy off) |
| 5 | Basic SaaS (Google Docs, Telegram web) |
| 6 | **Same tests** with comparison VPN Proxy on same machine/network |
| 7 | Happ `report.zip` + application log export |

**Classification rule:** If comparison VPN Proxy **PASS** and Bender Proxy **FAIL** → classify as **Track B — Bender profile/connectivity** (keep server regression unconfirmed until sub/probe correlation).

### 4.4 Do not collect

Subscription URLs, tokens, full Happ config export, private keys, unredacted screenshots with endpoints or credentials.

---

## 5. Immediate workaround guidance (user-safe)

| Situation | Guidance |
|-----------|----------|
| **After sleep/resume on Windows** | Prefer **disconnecting Happ before sleep** until Track A resolved |
| **Happ TUN daemon error** | Try **full Happ restart as administrator**; if error repeats, **reboot may be required** |
| **Avoid TUN after known failure** | Do **not** promise TUN stability on Windows desktop until CLIENT-SMOKE-001 passes |
| **Proxy as fallback** | Use Proxy mode **only if** CLIENT-SMOKE-002 proves Bender Proxy works — **currently unverified / reported failing** |
| **Bender Proxy fails** | Route to support with **diagnostic bundle** (§4.3); do not blame user network if comparison VPN Proxy works |
| **Mobile** | INCIDENT-002 interim stable — sleep/resume risk is **desktop-weighted** |

**Support intake minimum:** device model, OS build, Happ version, mode (TUN vs Proxy), error text verbatim, whether comparison VPN works, `/id` or support token — **no secrets in tickets**.

---

## 6. Smoke / proof tasks (required before commercial desktop promise)

### CLIENT-SMOKE-001 — Happ Windows TUN sleep/resume repro

| Step | Action |
|------|--------|
| 1 | Fresh import Bender profile |
| 2 | Connect Bender **TUN** |
| 3 | Confirm mail/google/browser works |
| 4 | Sleep laptop **10–30 min** |
| 5 | Resume |
| 6 | **Before reboot**, collect §4.2 bundle |
| 7 | Record: reconnect fixes vs reboot required |

**Pass criteria:** Sleep/resume with TUN connected; internet + mail work without reboot.
**Owner:** required · **Blocks:** desktop commercial SLA, G1 CLIENT-STABILITY

### CLIENT-SMOKE-002 — Bender Proxy mode connectivity

| Step | Action |
|------|--------|
| 1 | Disable TUN |
| 2 | Select BenderVPN Auto |
| 3 | Enable **Proxy mode** |
| 4 | Run §4.3 tests |
| 5 | Compare with SafeVPN/other VPN Proxy on same machine/network |
| 6 | Capture logs |

**Pass criteria:** Bender Proxy reaches mail/google/public IP check; parity with comparison VPN Proxy.
**Expected if owner report holds:** Bender Proxy FAIL + other VPN Proxy PASS → **Track B confirmed**

### CLIENT-SMOKE-003 — Alternative client fallback evaluation

Evaluate **Karing** or another supported client with **same Bender subscription URL**:

| Step | Action |
|------|--------|
| 1 | Import same Bender config |
| 2 | Test proxy/TUN/equivalent mode |
| 3 | Test sleep/resume (desktop) |
| 4 | Compare stability vs Happ |

**Outcome decision:**

| Result | Windows onboarding recommendation |
|--------|-----------------------------------|
| Karing stable; Bender path works | **Happ primary + Karing fallback** (with Auto-equivalence caveats per client audit) |
| Karing stable but LV-direct only | **Experimental fallback only** — not Auto-equivalent |
| Only Happ works (when healthy) | **Happ only** + sleep/TUN caveats |
| Neither works in Proxy | **Track B** escalation — profile/server smoke, not client-only |

See [`AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md`](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md) — Karing today is **not Auto-equivalent**; generator parity (G5-G) required before primary recommendation.

---

## 7. Fallback client strategy (evaluation only)

| Client | TUN/sleep | Bender Auto parity | Current product stance |
|--------|-----------|-------------------|------------------------|
| **Happ** | Track A **OPEN** | **Full** Xray JSON + routing profile | **Primary** |
| **Hiddify** | Unknown — diagnostic | **Full** JSON (same as Happ) | Diagnostic A/B only |
| **Karing** | Unknown | **Partial** — LV-direct strip, no relay pool | **Not primary** until G5-G |
| **v2rayN** | Different stack | Single VLESS link | Qualified fallback doc only |

**Decision gate:** CLIENT-SMOKE-003 outcome + owner approval — **no public copy change** until smokes complete.

---

## 8. Commercial launch impact — CLIENT-STABILITY gate

| Launch type | Impact |
|-------------|--------|
| **F&F / internal** | **GO** with disclosed Windows TUN + unverified Proxy fallback |
| **Soft launch** | **SOFT-LAUNCH ONLY** — Happ mobile-first; desktop sleep + Proxy caveats in support |
| **Paid / open launch** | **BLOCKER** if: (1) Bender Proxy fallback not working, (2) no validated alternative client, (3) no support runbook, (4) setup copy offers single fragile TUN-only path |

**CLIENT-STABILITY gate (G1 extension):**

| Check | Status |
|-------|--------|
| Track A TUN sleep/resume repro + AFTER-BROKEN capture | **OPEN** |
| Track B Bender Proxy smoke vs comparison VPN | **OPEN** |
| Workaround documented for support | **This doc** |
| Alternative client evaluated | **OPEN** (CLIENT-SMOKE-003) |
| Candidate D server regression | **Not confirmed** |

---

## 9. Approval phrases (unchanged)

| Scenario | Phrase |
|----------|--------|
| Desktop profile canary | `approve INCIDENT-003 desktop profile canary` |
| Rollback Candidate D | `approve rollback Candidate D template` — **only if D proven harmful** |
| Karing primary / generator | **Blocked** until G1 + G5-G + owner scope |

---

## 10. References

- INCIDENT-003: [`INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md`](INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md)
- INCIDENT-004: [`INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md`](INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md)
- INCIDENT-DIAG-003-004: [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md)
- Client matrix: [`AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md`](AUDIT-2026-06-10-VPN-CLIENT-APP-COMPATIBILITY.md)
- Gates: [`AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md`](AUDIT-2026-06-10-DEVELOPMENT-READINESS-GATES.md)
- Launch audit: [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md)
- Backlog: [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) — CLIENT-STABILITY-001, CLIENT-SMOKE-001..003
- Script: [`ops/diagnose_windows_vpn_resume.ps1`](../ops/diagnose_windows_vpn_resume.ps1)
