# CHECKPOINT — Client / Nodes / Monitoring (2026-06-12)

**Task:** CHECKPOINT-2026-06-12-CLIENT-NODES-MONITORING  
**Branch:** `product-referral-cabinet-ui-v1`  
**Mode:** read-only status audit · no deploy · no prod mutation  
**Captured:** 2026-06-12 (local repo state)

**Owner runtime note:** Owner currently has a **stable VPN session**. Do **not** ask them to restart Happ, reconnect, change routing, import deeplinks, or run prod patches until they choose a maintenance window.

**Canonical backlog:** [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) · [`BACKLOG-QUEUE.md`](BACKLOG-QUEUE.md) · [`COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md`](COMMERCIAL-LAUNCH-READINESS-AUDIT-2026-06-10.md)

---

## 1. Git state (snapshot)

| Item | Value |
|------|-------|
| **Branch** | `product-referral-cabinet-ui-v1` |
| **HEAD** | `0258d00` |
| **Remote tracking** | `origin/product-referral-cabinet-ui-v1` @ `a32d817` |
| **Ahead of remote** | **20 commits** (not pushed at checkpoint time) |
| **Staged** | none |
| **Modified (tracked)** | `.cursor/skills/bendervpn-journey-qa/SKILL.md` only |
| **Untracked (do not commit)** | `.playwright-review/`, live `*.png`, `data/`, `legacy.zip`, ad-hoc `ops/smoke_p1_*`, `ops/patch_restore_6relay_stealth.py`, `.cursor/rules/bendervpn-guardrails.mdc` |

---

## 2. Accepted commit inventory (recent work)

Commits from **`68e327d` → `0258d00`** (user-accepted scope). Earlier commits on branch (QA sandbox, portal acquisition, etc.) also ahead of remote but not listed here.

| Hash | Message | Category | Deployed? | Owner retest? |
|------|---------|----------|-----------|---------------|
| `68e327d` | docs(backlog): add node capacity readiness requirements | docs-only | No | No |
| `0a79614` | fix(portal): improve Mini App cabinet contrast | frontend | **No** | Portal visual — optional |
| `50a6ac4` | fix(monitoring): reduce selfsteal and cert alert noise | monitoring | **Yes LV** — `selfsteal-monitor.py`, `ru-monitor.py` | **24h soak pending** until **2026-06-12 15:11 UTC** |
| `b567f39` | docs(vpn): record NL auto host proof | docs-only | No | No |
| `187b654` | docs(vpn): record NL quality proof and smoke gates | docs-only | No | No |
| `34f73b4` | docs(client): add proxy mode diagnostic capture runbook | client stability (docs) + tests/scripts | No | CLIENT-SMOKE-002 capture when practical |
| `bccdbaf` | docs(incident): analyze active Happ TUN desktop failure | client stability (docs) + analyzer | No | **Pending** — owner TUN report analysis done; fix follows in `0258d00` |
| `0258d00` | fix(client): prevent relay endpoints from Happ direct routing | client stability (scripts/tests) | **No** | **Pending** — routing profile refresh + TUN retest |

**Read-only / no commit:** SAFEVPN-CONFIG-COMPARE-001.

---

## 3. Deployed vs not deployed

### Deployed (confirmed in task context)

| Change | Commit | Surface | Notes |
|--------|--------|---------|-------|
| Selfsteal anti-flap + cert digest | `50a6ac4` | LV `/opt/scripts/selfsteal-monitor.py`, `ru-monitor.py` | Soak closeout **blocked until after 2026-06-12 15:11 UTC** |

### Not deployed (repo-only at checkpoint)

| Change | Commit | Surface |
|--------|--------|---------|
| Mini App cabinet contrast | `0a79614` | `web/portal/` |
| Happ routing DirectIp fix (`geoip:ru` removed) | `0258d00` | `ops/happ_routing_profile_ru.json`, guard, generator |
| Prod `happRouting` deeplink | — | `patch_happ_routing.py --apply` **not approved, not run** |
| NL A2/A4 routing inclusion | — | blocked on MONITOR-FLAP soak + owner approval |
| Remna / Caddy / subscription template | — | no changes in accepted range |
| Bot / billing / YooKassa | — | no prod mutation |

---

## 4. Current blockers

| Blocker | Status | Unblocks |
|---------|--------|----------|
| **MONITOR-FLAP-001** 24h soak | Open until **after 2026-06-12 15:11 UTC** | MONITOR-FLAP-SOAK-CLOSEOUT rerun |
| **NL A2/A4** controlled smoke | Blocked | Soak PASS + owner explicit approval |
| **CLIENT-STABILITY DirectIp fix** | Repo done (`0258d00`); prod routing not updated | Owner 10–15 min TUN retest with refreshed profile |
| **Prod Happ routing update** | Not approved | Owner retest PASS → then consider `patch_happ_routing.py --apply` |
| **Proxy Track B** (CLIENT-SMOKE-002) | Open | Separate capture — Bender Proxy vs control Proxy |
| **Desktop Windows commercial gate (G1)** | Open | TUN retest + Track A sleep/resume smokes |

---

## 5. Safety scan (checkpoint)

| Check | Result |
|-------|--------|
| `report.zip` in git | **None** |
| Screenshots (`.png`) in git | **None** (untracked live shots only) |
| `.secrets/*` in git | **Examples only** — `vault.env.example`, `yookassa.env.example` |
| `.cursor/*` in git | **Rules + one skill** (repo policy); guardrails.mdc **untracked** |
| Secrets in commits `68e327d..0258d00` | **Pass** — only redaction regexes, test fixtures, env var *names* in log strings |
| Prod `.env` / vault committed | **None** in range |
| Unexpected Remna/billing mutation | **None** in accepted commits |

---

## 6. Next-step decision map

### A. After **2026-06-12 15:11 UTC**

- Rerun **MONITOR-FLAP-001-SOAK-CLOSEOUT** (LV logs + TG noise check).
- If PASS → mark **MONITOR-FLAP-001** / **OPS-ALERT-HYGIENE-001** deployed+soaked DONE in backlog (docs-only).

### B. When owner has **10–15 min** (stable session ends first)

- **Do not** run `patch_happ_routing.py --apply`.
- Owner-only local refresh:
  ```powershell
  cd D:\Va\projects\VPN
  python ops/generate_happ_routing_link.py --write-json
  python ops/generate_happ_routing_link.py --open
  ```
- Re-enable **BenderVPN RU** routing → TUN → 5–10 min site matrix (see [`INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md`](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) §11).
- Verify: `python ops/happ_routing_directip_guard.py` · optional `python ops/analyze_happ_report_tun.py report.zip`.

### C. If DirectIp retest **PASS**

- Owner explicitly approves → **`patch_happ_routing.py --apply`** to prod subscription settings (separate deploy task).

### D. If MONITOR-FLAP soak **PASS** + owner approval

- Design/apply controlled **NL A2/A4** smoke per [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) VPN-ARCH-001.

### E. Proxy Track B (parallel, when practical)

- [`CLIENT-SMOKE-002-PROXY-CAPTURE.md`](CLIENT-SMOKE-002-PROXY-CAPTURE.md) — not while owner relies on TUN-only.

### F. Safe next Cursor prompts (copy-paste)

1. `MONITOR-FLAP-001-SOAK-CLOSEOUT — read-only LV log review after 2026-06-12 15:11 UTC`
2. `CLIENT-STABILITY-ROUTING-DIRECTIP-RETEST-001 — owner Happ TUN retest after stable session ends` (owner action required)
3. `Push product-referral-cabinet-ui-v1 — 20 commits ahead of origin` (only if owner asks)

---

## 7. What NOT to do now

- Do **not** deploy portal contrast, NL routing, or Happ prod routing.
- Do **not** restart Happ / reconnect / routing-OFF test while owner session is stable.
- Do **not** commit `.playwright-review/`, live screenshots, `data/`, or raw diagnostics.
- Do **not** push branch unless owner explicitly requests.

---

## 8. Key doc links

| Topic | Doc |
|-------|-----|
| TUN active failure + DirectIp fix | [`INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md`](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) |
| TUN daemon + Proxy Track B | [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) |
| Proxy capture runbook | [`CLIENT-SMOKE-002-PROXY-CAPTURE.md`](CLIENT-SMOKE-002-PROXY-CAPTURE.md) |
| NL proofs | backlog § VPN-ARCH-001-NL-* in [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) |
| Monitoring deploy map | [`DEPLOY.md`](DEPLOY.md) · [`MONITORING.md`](MONITORING.md) |
| DirectIp guard | `ops/happ_routing_directip_guard.py` |

---

## 9. Repo hygiene reminder

Working tree is **clean for product code** except one `.cursor/skills/` edit. Large untracked QA/review artifacts are local-only; keep out of commits.
