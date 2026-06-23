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
| `0258d00` | fix(client): prevent relay endpoints from Happ direct routing | client stability (scripts/tests) | **No** | **PASS local 2026-06-12** — prod apply pending |

**Read-only / no commit:** SAFEVPN-CONFIG-COMPARE-001.

---

## 3. Deployed vs not deployed

### Deployed (confirmed in task context)

| Change | Commit | Surface | Notes |
|--------|--------|---------|-------|
| Selfsteal anti-flap + cert digest | `50a6ac4` | LV `/opt/scripts/selfsteal-monitor.py`, `ru-monitor.py` | Soak closeout **PARTIAL** 2026-06-13 — see §8 |

### Not deployed (repo-only at checkpoint)

| Change | Commit | Surface |
|--------|--------|---------|
| Mini App cabinet contrast | `0a79614` | `web/portal/` |
| Happ routing DirectIp fix (`geoip:ru` removed) | `0258d00` | `ops/happ_routing_profile_ru.json`, guard, generator |
| Prod `happRouting` deeplink | — | `patch_happ_routing.py --apply` **not approved, not run** |
| NL A2/A4 routing inclusion | — | blocked on owner explicit approval (soak PASS 2026-06-24) |
| Remna / Caddy / subscription template | — | no changes in accepted range |
| Bot / billing / YooKassa | — | no prod mutation |

---

## 4. Current blockers

| Blocker | Status | Unblocks |
|---------|--------|----------|
| **MONITOR-FLAP-001** + **TUNE-001** soak | **PASS** (closeout 2026-06-24, §10) | — |
| **NL A2/A4** controlled smoke | Blocked on **owner explicit approval** only | Soak gate cleared 2026-06-24 |
| **CLIENT-STABILITY DirectIp fix** | **Owner local retest PASS (2026-06-12)** | Prod `patch_happ_routing.py --apply` after explicit approval |
| **Prod Happ routing update** | Prepared — see INCIDENT-DIAG-2026-06-12 §11 | Explicit `OWNER APPROVES PROD HAPP ROUTING APPLY NOW` |
| **Proxy Track B** (CLIENT-SMOKE-002) | Open | Separate capture — Bender Proxy vs control Proxy |
| **Desktop Windows commercial gate (G1)** | **Downgraded** — DirectIp leak mitigated locally; Track A/B + prod deploy still open | Track A sleep/resume; prod routing apply |

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

### A. ~~MONITOR-FLAP soak~~ — **CLOSED PASS 2026-06-24**

- §8 — pre-tune PARTIAL (2026-06-13); §9 — TUNE deploy; §10 — extended soak evidence.
- **MONITOR-FLAP-001** + **MONITOR-FLAP-TUNE-001:** soak **PASS** (`quorum_fail_cdn=0`; owner accepts microsoft sustained ~6/10d).
- **OPS-ALERT-HYGIENE-001:** soak **PASS** (cert digest).
- **NL A2/A4:** monitoring soak gate **cleared** — still needs **owner explicit approval** for controlled smoke (not automatic).

### B. Prod Happ routing apply (when owner approves)

- Explicit approval line required: **`OWNER APPROVES PROD HAPP ROUTING APPLY NOW`**
- Commands: `happ_routing_directip_guard.py` → `patch_happ_routing.py` dry-run → `--apply`
- See [`INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md`](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) §11 rollback + post-apply smoke

### C. ~~Owner DirectIp retest~~ — **DONE PASS 2026-06-12**

Local deeplink validated; prod deploy still pending.

### D. NL A2/A4 (after soak PASS + owner approval)

- Controlled smoke per [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) VPN-ARCH-001 — **not** automatic on soak closeout.

### E. Proxy Track B (parallel, when practical)

- [`CLIENT-SMOKE-002-PROXY-CAPTURE.md`](CLIENT-SMOKE-002-PROXY-CAPTURE.md) — not while owner relies on TUN-only.

### F. Safe next Cursor prompts (copy-paste)

1. ~~`MONITOR-FLAP-001-SOAK-CLOSEOUT`~~ — **DONE PASS 2026-06-24** (§10)
2. ~~`MONITOR-FLAP-TUNE-001`~~ — **DONE PASS 2026-06-24** (§10)
3. `CLIENT-STABILITY-ROUTING-DIRECTIP-RETEST-001 — owner Happ TUN retest after stable session ends` (owner action required)
4. `Push product-referral-cabinet-ui-v1 — 20 commits ahead of origin` (only if owner asks)

---

## 7. What NOT to do now

- Do **not** deploy portal contrast, NL routing, or Happ prod routing.
- Do **not** restart Happ / reconnect / routing-OFF test while owner session is stable.
- Do **not** commit `.playwright-review/`, live screenshots, `data/`, or raw diagnostics.
- Do **not** push branch unless owner explicitly requests.

---

## 8. MONITOR-FLAP-001 soak closeout (2026-06-13)

**Task:** MONITOR-FLAP-001-SOAK-CLOSEOUT · read-only LV log review · no prod mutation
**Deploy:** `50a6ac4` on LV ~2026-06-11 14:46 UTC · soak start ~15:11 UTC
**Window reviewed:** 2026-06-11 15:11 UTC → 2026-06-12 15:11 UTC (+ extended to 2026-06-13 16:25 UTC)

### Deploy verification

| Check | Result |
|-------|--------|
| `selfsteal-monitor.py` MD5 | `364cac90f5a5c7af0787953d56a6074b` — **match** repo/deploy report |
| `ru-monitor.py` MD5 | `2046068c4193027cd90ad0cef35e61bb` — **match** |
| Cron | `*/5` → `/opt/scripts/{selfsteal-monitor,ru-monitor}.py` — **unchanged** |
| Anti-flap markers on LV | `fail_streak`, `ok_streak`, `cooldown`, `quorum`, cert digest — **present** |

### selfsteal-monitor (soak 24h)

| Metric | Pre-deploy (2026-06-11 before 15:11) | Soak window | Extended (+25h) |
|--------|----------------------------------------|-------------|-----------------|
| Legacy `ALERT CRITICAL` | **28** | **0** | **0** |
| Legacy `ALERT RECOVERED:` | **28** | **0** | — |
| `ALERT DOWN queued` | — | **17** (all `microsoft.com` quorum) | **+19** |
| `ALERT RECOVERED queued` | — | **17** | **+19** |
| Suppressed (cooldown/streak) | — | **81** | — |
| `api.github.com` warnings (log) | — | **288** | **+302** |
| Tracebacks | — | **0** | **0** |
| Non-microsoft DOWN/RECOVERED | — | **0** | — |

**Assessment:** Legacy 5-min CRITICAL/RECOVERED spam **stopped**. Rapid flap loops **gone** (microsoft DOWN gaps ~28–64 min). Residual TG noise: **`latvia:www.microsoft.com`** via `paging: quorum fail` (HTTP 000 when ≥2 SNIs bad). Log-only noise: **`api.github.com retried N times`** every */5 cron (~12/h). No evidence of hidden real outage (12/13 SNIs OK at soak end; baseline RU SNIs never paged).

### ru-monitor (soak 24h)

| Metric | Soak | Extended |
|--------|------|----------|
| `ALERT DOWN` / `RECOVERED` | **0** / **0** | **0** |
| `ALERT CERT DIGEST` | **6** | **+7** |
| Old per-target `certificate changed` (non-digest) | **0** | **0** |
| Cert digest cooldown suppressions | **3** | — |
| Tracebacks / FATAL | **0** | **0** |

**Assessment:** Cert rotation **batched/digested**; per-target cert paging **eliminated**. **PASS.**

### Decision

| ID | Verdict |
|----|---------|
| **OPS-ALERT-HYGIENE-001** | **PASS** — deployed + soaked OK |
| **MONITOR-FLAP-001** | **PARTIAL** — keep deployed; tune **MONITOR-FLAP-TUNE-001** (microsoft CDN quorum + github log throttle) |
| **NL A2/A4** | **Blocked** — owner risk acceptance on PARTIAL soak required before controlled smoke |

---

## 9. MONITOR-FLAP-TUNE-001 LV deploy (2026-06-13)

**Task:** MONITOR-FLAP-TUNE-001-LV-DEPLOY · owner approval received · **selfsteal-monitor.py only**

| Item | Value |
|------|-------|
| Repo commit | `21f5a97` |
| Deploy UTC | **2026-06-13 16:41:22** |
| Backup | `/opt/scripts/selfsteal-monitor.py.before-monitor-flap-tune-20260613-164122` |
| Previous MD5 | `364cac90f5a5c7af0787953d56a6074b` (`50a6ac4`) |
| New MD5 | `7af796f345bb0a0a3867ce132dbfd930` — **match local + remote** |
| Cron | `*/5` → `/opt/scripts/selfsteal-monitor.py` — **unchanged** |
| `ru-monitor.py` | **Not deployed** — MD5 `2046068c4193027cd90ad0cef35e61bb` unchanged |

### Short soak

| Milestone | UTC |
|-----------|-----|
| Install complete | 2026-06-13 **16:41:22** |
| Stale pre-tune DOWN (race) | 16:41:53 — `paging: quorum fail` from run started before swap |
| **First tuned cron (soak start)** | **16:46:40** — no new CDN quorum DOWN; `transitions=0` |
| 30m review | ~**17:16** |
| 6h review | ~**22:46** |
| Optional 24h gate | before NL A2/A4 if owner wants clean monitoring SoT |

Post-deploy health (through 16:46:40): **0 tracebacks**; github retried throttle state field active (first post-deploy warn expected; ≤1/h thereafter).

---

## 10. MONITOR-FLAP extended soak closeout (2026-06-24)

**Task:** MONITOR-FLAP-001 + MONITOR-FLAP-TUNE-001 extended soak · read-only LV log review · no prod mutation  
**Review UTC:** 2026-06-23 21:30 · owner acceptance 2026-06-24 (microsoft sustained TG = design, no tune-002)

### Deploy verification

| Check | Result |
|-------|--------|
| `selfsteal-monitor.py` MD5 | `7af796f345bb0a0a3867ce132dbfd930` — **match** TUNE-001 (`21f5a97`) |
| Soak window | **2026-06-13 16:46:40 UTC** → **2026-06-23 21:30 UTC** (~**10.2 days**) |
| Review script | `.playwright-review/monitor_tune_30min_review.sh` on LV (`/tmp/monitor_tune_review.sh`) |

### Evidence (post-tune window)

| Metric | Count | Notes |
|--------|------:|-------|
| `quorum_fail_cdn` (microsoft/apple/bing → TG) | **0** | Primary TUNE-001 goal — **met** |
| `cdn_quorum_blip` (log-only, suppressed) | **419** | CDN blips do not page |
| `sustained fail (CDN)` → TG | **6** | All `latvia:www.microsoft.com`, HTTP 000, ~10–18 min; **owner accepted** |
| `ALERT DOWN queued` (total) | **11** | 6 microsoft sustained + 4 `ir-3.ozone.ru` + 1 `sun6-21.userapi.com` |
| `ALERT RECOVERED queued` | **12** | Includes stale pre-tune recover line |
| `paging: quorum fail` (non-CDN) | **5** | Legitimate baseline RU SNIs |
| `api.github.com retried` (log WARNING) | **236** | ~1/h; **not TG** |
| Traceback / FATAL / ERROR | **0** / **0** / **0** | |
| Log lines in window | **3651** | |
| End state | `ok=12 critical=1` | Chronic `api.github.com` — log-only |

### Comparison to pre-TUNE blocker (§8)

| Before TUNE-001 | After TUNE-001 (10d window) |
|-----------------|----------------------------|
| `paging: quorum fail` on `www.microsoft.com` | **0** CDN quorum pages |
| ~36 microsoft DOWN/RECOVERED pairs / 49h | **6** microsoft sustained DOWN (~0.6/day) |
| Rapid flap loops | Gaps ~hours–1 day between sustained events |

### Decision

| ID | Verdict |
|----|---------|
| **MONITOR-FLAP-TUNE-001** | **PASS** — CDN quorum log-only; `quorum_fail_cdn=0` |
| **MONITOR-FLAP-001** | **PASS** — anti-flap deployed; legacy spam eliminated; residual TG = real sustained CDN + baseline RU only |
| **NL A2/A4** | Monitoring gate **cleared**; controlled smoke still requires **owner explicit approval** |

---

## 11. Key doc links

| Topic | Doc |
|-------|-----|
| TUN active failure + DirectIp fix | [`INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md`](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) |
| TUN daemon + Proxy Track B | [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) |
| Proxy capture runbook | [`CLIENT-SMOKE-002-PROXY-CAPTURE.md`](CLIENT-SMOKE-002-PROXY-CAPTURE.md) |
| NL proofs | backlog § VPN-ARCH-001-NL-* in [`BENDERVPN-MASTER-BACKLOG.md`](BENDERVPN-MASTER-BACKLOG.md) |
| Monitoring deploy map | [`DEPLOY.md`](DEPLOY.md) · [`MONITORING.md`](MONITORING.md) |
| DirectIp guard | `ops/happ_routing_directip_guard.py` |

---

## 12. Repo hygiene reminder

Working tree is **clean for product code** except one `.cursor/skills/` edit. Large untracked QA/review artifacts are local-only; keep out of commits.
