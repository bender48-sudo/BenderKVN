# ARCH — AI Support Triage Bot

**ID:** SUPPORT-AI-ARCH-001
**Date:** 2026-06-10
**Mode:** architecture + backlog design only · no implementation · no AI runtime · no credentials
**Branch:** `product-referral-cabinet-ui-v1`
**Parent:** [`AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md`](AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md), [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) §9

**Owner intent:** Technical AI support bot receives user requests, handles common cases, asks for missing diagnostics, checks **safe read-only** technical status, drafts human replies, and hands off a **structured Cursor/operator prompt** when engineering investigation is needed.

**Evidence method:** docs + existing admin/ops patterns only. Status: **CONFIRMED** / **PARTIAL** / **BLOCKED** / **UNKNOWN**.

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **Purpose** | Reduce support load; improve diagnostic quality; accelerate operator/Cursor investigations |
| **MVP recommendation** | **Option D + parts of B** — internal AI copilot first; human approves replies/actions |
| **User-facing automation** | **Deferred** — SUPPORT-AUTO-001 after smokes |
| **F&F blocker?** | **No** — manual owner support OK |
| **Paid/open blocker?** | **Partial** — human runbooks + P1-ADM still required; AI **recommended** not prerequisite for TRACK 0 |
| **Can mutate prod?** | **Never by default** — L4 only with explicit human approval |

**After SUPPORT-AI-ARCH-001:** no remaining **broad audits**. Only implementation, smoke, proof, owner decisions.

---

## 2. Support bot scope (case categories)

### A. VPN unstable / disconnects

| Field | Content |
|-------|---------|
| **Symptoms** | Internet OK without VPN; unstable with VPN; Happ shows connected but traffic fails; long SaaS session drops (INCIDENT-004); sleep/resume breaks (INCIDENT-003); mobile vs desktop difference |
| **Required questions** | Device, app (Happ/Hiddify), OS version, Wi‑Fi vs LTE, VPN UI state at failure, exact time, fresh import yes/no, other VPN installed |
| **Read-only checks** | Profile integrity (7353 B, 6 paths, DoH, parity); relay TCP; `onlineAt` if available; account active/expired |
| **Escalation trigger** | Repeated failures after fresh import; sleep/resume + reboot required; SaaS-only drops 20+ min |
| **Safe reply direction** | One recovery step: refresh sub → reimport → reboot → support escalate; no server claim without probes |

### B. Setup / import problems

| Field | Content |
|-------|---------|
| **Symptoms** | Cannot import; QR vs link confusion; wrong app; stale profile; subscription update fails |
| **Required questions** | Which app; import method (QR/link); error text; first setup or replacement |
| **Read-only checks** | Trial/wallet status; setup link resolvable; profile HTTP 200; `happAnnounce` present |
| **Escalation trigger** | Valid account but profile 4xx/empty; panel user missing |
| **Safe reply direction** | Link-first setup path; Happ only for primary; guide URL |

### C. Account / subscription problems

| Field | Content |
|-------|---------|
| **Symptoms** | No setup link; trial expired; wallet expired; balance visible but VPN dead; legacy/manual user |
| **Required questions** | Telegram ID; browser vs Mini App; last successful connection date |
| **Read-only checks** | `subscription_profile`; `active_config_count`; `configurations[]` masked; panel sync; `billing_profile` |
| **Escalation trigger** | DB/panel mismatch; orphan Remna user; multi-key anomaly |
| **Safe reply direction** | Explain trial vs wallet; route to topup or support replace |

### D. Payment problems

| Field | Content |
|-------|---------|
| **Symptoms** | Paid but no access; pending/failed; duplicate payment; top-up not visible |
| **Required questions** | Approx payment time; amount last 4 digits; YooKassa receipt if any (no card data) |
| **Read-only checks** | Payment record; webhook delivered; `yk:{payment_id}` idempotency key; balance delta; panel extend result — **no reconcile --apply** |
| **Escalation trigger** | Webhook OK but balance unchanged; duplicate credit suspicion |
| **Safe reply direction** | «Проверяем статус оплаты»; never promise refund without operator |

### E. Device problems

| Field | Content |
|-------|---------|
| **Symptoms** | New device; copied config to 2nd device; replacement; limit questions; same-sub reuse suspicion |
| **Required questions** | Old vs new device; one or two phones using same link |
| **Read-only checks** | `active_config_count`; DEVICE-ENFORCE status if implemented; config list masked |
| **Escalation trigger** | Same URL on 2 devices; needs tracked replace |
| **Safe reply direction** | One config = one device policy; support replace path — no self-service promise until DEVICE-ADD |

### F. Referral problems

| Field | Content |
|-------|---------|
| **Symptoms** | Referral link; invite count wrong; bind not credited; missing invitee |
| **Required questions** | Inviter TG; invitee TG/email prefix; link type (bot vs portal) |
| **Read-only checks** | `referred_by`; `referrals` count; bind status; web vs TG source — **PARTIAL** until REF-ADMIN |
| **Escalation trigger** | G4 bind failure pattern; attribution dispute |
| **Safe reply direction** | Tracking-only; no bonus promise |

### G. Known incident follow-ups

| Field | Content |
|-------|---------|
| **Symptoms** | Sleep/resume (INCIDENT-003); browser SaaS drops (INCIDENT-004); profile integrity concerns |
| **Required questions** | Per incident doc checklists |
| **Read-only checks** | Candidate D parity probes; owner diagnostic script outputs (redacted) |
| **Escalation trigger** | Matches open incident hypothesis |
| **Safe reply direction** | Known limitation disclosure; workaround steps from runbook |

---

## 3. Permission levels (safety model)

| Level | Capability | Default |
|-------|------------|---------|
| **L0** | Conversation only — FAQ/runbooks; ask screenshots, app, version, device | **MVP start** |
| **L1** | Read-only account — trial/wallet/legacy/expired; `active_config_count`; masked configs; balance/days; no secrets | **MVP target** |
| **L2** | Read-only infra — sub edge health; profile size/paths; relay TCP; AMS/LV service status; billing job **read**; webhook delivery **read** | Operator copilot |
| **L3** | Operator handoff — structured Cursor prompt; allowed checks listed; **no mutation** | **Required for engineering cases** |
| **L4** | Controlled actions — revoke, extend, deploy, reconcile | **Future only**; explicit human approval per action |

### Hard rules (never)

- Run deploy scripts
- `reconcile --apply`
- YooKassa write endpoints
- Balance changes
- Config create/revoke
- Remna / Caddy / template PATCH
- Expose full subscription URLs or vault secrets to operators unless policy exception
- Promise fix before evidence

---

## 4. Diagnostic data model (design only)

```text
support_ticket:
  ticket_id
  user_telegram_id
  username
  contact_email              # optional, masked in exports
  created_at
  channel                    # telegram_bot | portal | admin_manual
  issue_category             # A..G enum
  severity                   # low | medium | high | outage
  user_message
  bot_summary
  collected_device_info
  app_name
  app_version
  os
  network_type
  vpn_status_user_reported
  error_text
  screenshot_present         # bool
  diagnostic_file_present    # bool
  account_profile            # trial | wallet | legacy | expired
  active_config_count
  config_status_summary      # redacted
  payment_status_summary     # redacted
  referral_status_summary    # optional
  last_profile_integrity_check
  last_infra_check
  escalation_status          # none | pending | cursor | operator | resolved
  cursor_handoff_prompt      # text, no secrets
  support_reply_draft
  resolution_status
  closed_at
```

### Privacy

- Redact full subscription URLs in tickets and handoffs
- Redact bind tokens, JWT, API keys
- Mask payment IDs (`yk:****`); never store card data
- Screenshot storage policy: **TBD** — prefer ephemeral + hash reference
- Retention: **TBD** — align with DATA-MINIMIZATION policy

---

## 5. Read-only diagnostics catalog (not implementation)

### Account

| Check | Source today | Status |
|-------|--------------|--------|
| User by `telegram_id` | `database.py` / admin | **PARTIAL** — no admin command |
| `subscription_profile` | `portal_cabinet.py` | **CONFIRMED** API |
| `active_config_count` | P1-DEV-001 | **CONFIRMED** deployed |
| Masked `configurations[]` | cabinet API | **CONFIRMED** |
| Balance / `days_left` | cabinet API | **CONFIRMED** |
| Last payment read-only | DB query | **BLOCKED** — P1-ADM-003 |
| Referral attribution | `referred_by`, `referrals` | **PARTIAL** |

### VPN / profile

| Check | Source | Status |
|-------|--------|--------|
| Sub HTTP 200, size, proxy count | `probe_subscription.py` | **CONFIRMED** ops |
| DoH, selector parity | probe scripts | **CONFIRMED** |
| Relay TCP | balancer probes | **CONFIRMED** ops |
| AMS/LV service up | SSH/docker read | **CONFIRMED** manual |
| Client-side intake | User-reported only | **L0** |

### Payment

| Check | Source | Status |
|-------|--------|--------|
| Payment exists | `payments` table | **PARTIAL** — admin view missing |
| Webhook delivered | logs / DB | **PARTIAL** |
| Idempotency `yk:{id}` | `payment_idempotency.py` | **CONFIRMED** code |
| Balance credited | user row | **CONFIRMED** |
| Panel sync | logs | **PARTIAL** |

### Device / referral

| Check | Source | Status |
|-------|--------|--------|
| Active configs | cabinet | **CONFIRMED** |
| Same-sub reuse | DEVICE-ENFORCE-001 | **NOT_STARTED** |
| Inviter/invitee | REF-ADMIN-001 | **NOT_STARTED** |

---

## 6. Cursor / operator handoff prompt format

```text
SUPPORT-ESCALATION — <category> — <severity> — <ticket_id>

Context:
- User: <masked identity — TG id/username, email prefix if web>
- Plan/status: <trial | wallet | legacy | expired>
- Device/app/OS: <collected>
- Symptom: <user words>
- Started at: <timestamp user reported>
- User-visible error: <text or "none">
- Recent changes: <import, payment, device change>
- Screenshots/logs attached: <yes/no, file refs redacted>
- Support conversation summary: <3–5 sentences>

Read-only diagnostics already collected:
- account: <profile, config count, balance summary>
- config: <masked status>
- billing: <payment/webhook summary if relevant>
- VPN profile: <probe results — size, paths, parity>
- infra: <AMS/LV/relay if run>
- referral/device: <if relevant>

Requested Cursor task:
- Inspect relevant code/docs/logs for this case category
- Run ONLY allowed read-only checks unless explicit approval exists
- Classify likely cause (A/B/C/D/E/F/G + sub-hypothesis)
- Do NOT mutate prod, deploy, billing, reconcile, Remna, Caddy, template
- Propose fix design if needed; implement only after approval phrase
- Return:
  1. technical finding (CONFIRMED/PARTIAL/BLOCKED)
  2. customer-safe response (Russian, calm, one next step)
  3. support action for operator
  4. whether developer/operator mutation required (yes/no)
  5. approval phrase if mutation required

Guardrails:
- No secrets in output
- No prod mutation
- No Remna/Caddy/template patch
- No YooKassa write
- No balance changes
- No config revoke/create unless approved
```

### Example (VPN unstable)

```text
SUPPORT-ESCALATION — A-VPN-unstable — medium — TKT-20260610-0042

Context:
- User: TG @masked_user (id redacted in ticket store)
- Plan/status: wallet active, 12 days_left
- Device/app/OS: Windows 11, Happ desktop 1.x, Wi‑Fi
- Symptom: "интернет без VPN работает, с VPN обрывается каждые 10–15 мин"
- Started at: 2026-06-10 ~14:00 MSK
- User-visible error: Happ shows Connected, pages timeout
- Recent changes: fresh import yesterday
- Screenshots: no
- Summary: User reports intermittent failure; mobile same account OK per user

Read-only diagnostics already collected:
- account: wallet, active_config_count=1, balance OK
- VPN profile: 7353B, 6 paths, parity OK (probe 2026-06-10)
- infra: relay TCP green

Requested Cursor task:
- Check INCIDENT-003/004 alignment; Happ TUN lifecycle docs
- Read-only: suggest owner sleep/resume or SaaS soak steps
- Do not patch routing
- Return finding + user reply + whether INCIDENT-003 owner diag needed
```

---

## 7. Human-style customer communication

**Style:** short, calm, trustworthy; one next step; no jargon; no blame; no unproven promises.

| Case | Example reply (RU) |
|------|-------------------|
| VPN unstable | «Поняла, давайте быстро проверим. Напишите, пожалуйста: устройство, приложение, версия ОС, Wi‑Fi или мобильная сеть, и что показывает VPN в момент сбоя — подключено или ошибка. Если сбой повторится, отметьте точное время.» |
| Payment | «Проверю статус оплаты и доступа. Пришлите, пожалуйста, примерное время оплаты и последние 4 цифры суммы/чека, если есть. Полные данные карты отправлять не нужно.» |
| Device replace | «Сейчас настройка привязана к устройству. Для замены мы отключим старую настройку и выпустим новую. Передам запрос специалисту, чтобы не было двойного списания.» |
| Referral | «Проверю, зафиксировалось ли приглашение. Нужен ваш Telegram ID или ник и, если есть, ник приглашённого пользователя.» |
| Escalated | «Передала техническому специалисту. Пока он проверяет, попробуйте обновить подписку в Happ (кнопка обновления) и переподключиться. Отвечу, как только будет результат.» |

**Forbidden:** «Мы уже исправили на сервере» without evidence; bonus/referral promises; HWID enforcement claims; «выпустите новую настройку в кабинете» until DEVICE-ADD exists.

---

## 8. Architecture options

| Option | Description | Pros | Cons | Verdict |
|--------|-------------|------|------|---------|
| **A** | Rule-based FAQ bot | Fast; cheap | Weak diagnostics | FAQ layer only |
| **B** | AI triage + read-only tools | Strong context; Cursor handoff | Needs permission gates | **Target core** |
| **C** | Autonomous fixes | Fast resolution | **Too risky** now | **REJECT** |
| **D** | Internal copilot first | Safe MVP; human approves | No user automation yet | **MVP shell** |

**Recommendation:** **MVP = D + B**

1. Internal operator copilot (Telegram admin channel or web console)
2. L0–L2 read-only diagnostics wired gradually
3. L3 Cursor handoff for engineering cases
4. Human approves every customer-facing reply
5. SUPPORT-AUTO-001 user-facing only after SUPPORT-SMOKE-001 PASS

---

## 9. Gates

| Gate | Status | F&F | Soft | Paid | Open | Action |
|------|--------|-----|------|------|------|--------|
| **SUPPORT-AI-ARCH-001** | **DONE** (this doc) | — | — | — | — | — |
| **SUPPORT-TICKET-001** | NOT_STARTED | No | No | Partial | Partial | Ticket schema |
| **SUPPORT-RAG-001** | NOT_STARTED | No | No | No | Partial | Index docs/runbooks |
| **SUPPORT-DIAG-001** | NOT_STARTED | No | Partial | **Yes** | **Yes** | Read-only diag pack |
| **SUPPORT-CURSOR-HANDOFF-001** | NOT_STARTED | No | Partial | **Yes** | **Yes** | Prompt generator |
| **SUPPORT-REPLY-001** | NOT_STARTED | No | Partial | **Yes** | **Yes** | Reply draft templates |
| **SUPPORT-SECURITY-001** | NOT_STARTED | No | Partial | **Yes** | **Yes** | Redaction + ACL |
| **SUPPORT-SMOKE-001** | NOT_STARTED | No | No | Partial | Partial | Simulated cases |
| **SUPPORT-ADMIN-001** | NOT_STARTED | No | Partial | **Yes** | **Yes** | Operator queue UI |
| **SUPPORT-AUTO-001** | NOT_STARTED | No | No | No | Partial | User-facing bot — gated |

**Note:** AI support **does not replace** P1-ADM-001, LAUNCH-004 runbooks, or DEVICE-ADMIN — it **depends on** them for L1 diagnostics.

---

## 10. Implementation roadmap (one surface per commit)

| Order | ID | Objective | Files likely | Deploy? | Risk | Prerequisite | Approval |
|-------|-----|-----------|--------------|---------|------|--------------|----------|
| 1 | SUPPORT-AI-ARCH-001 | Architecture | docs | No | None | — | — |
| 2 | SUPPORT-TICKET-001 | Ticket storage design | `database.py` schema doc, migrations spec | No | Low | ARCH | approve SUPPORT-TICKET-001 schema |
| 3 | SUPPORT-RUNBOOK-001 | Incident→runbook conversion | `docs/runbooks/` | No | None | LAUNCH-004 partial | — |
| 4 | SUPPORT-DIAG-001 | Read-only diag script/API | `ops/support_diag_*.py`, read-only admin | AMS read | Low | P1-ADM-001 partial | approve SUPPORT-DIAG-001 read-only |
| 5 | SUPPORT-CURSOR-HANDOFF-001 | Escalation prompt builder | bot module or ops script | No | Low | TICKET-001 | — |
| 6 | SUPPORT-REPLY-001 | Reply draft generator | templates + policy guard | No | Low | RAG partial | approve SUPPORT-REPLY-001 |
| 7 | SUPPORT-SECURITY-001 | Redaction layer | shared util | No | Med | SECURITY review | approve SUPPORT-SECURITY-001 |
| 8 | SUPPORT-SMOKE-001 | 5 simulated cases | `tests/` or `ops/` | No | Low | DIAG-001 | approve SUPPORT-SMOKE-001 |
| 9 | SUPPORT-ADMIN-001 | Operator queue | admin UI / bot channel | Yes AMS | Med | TICKET+DIAG | approve SUPPORT-ADMIN-001 |
| 10 | SUPPORT-AUTO-001 | User-facing automation | bot handler | Yes | **High** | SMOKE+SECURITY | approve SUPPORT-AUTO-001 |

**Do not implement** in this pass.

---

## 11. Owner decisions

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | MVP surface | Internal copilot vs user bot | **Internal copilot first (D)** |
| 2 | LLM provider | External API vs local | **Deferred** — no credentials in repo |
| 3 | Ticket storage | SQLite vs separate DB | SQLite extension MVP |
| 4 | Screenshot handling | Store vs ephemeral | Ephemeral + hash |
| 5 | Auto-reply to users | On/off | **Off** until SMOKE PASS |

---

## 12. Explicit NO-GO

- AI bot with L4 mutation by default
- Connecting external AI with production credentials in this phase
- Using AI to bypass missing P1-ADM / runbooks
- User-facing auto-reply before SUPPORT-SECURITY-001
- Semgrep / secret scanning via AI pipeline

---

## 13. References

| Artifact | Role |
|----------|------|
| `INCIDENT-2026-06-10-VPN-LAPTOP-SLEEP-RESUME.md` | Category G |
| `INCIDENT-2026-06-10-VPN-BROWSER-LONG-SESSION-DROPS.md` | Category G |
| `POSTDEPLOY-2026-06-10-BILL-FIX-001.md` | Payment diag context |
| `ARCH-2026-06-10-MULTI-DEVICE-BILLING-ENFORCEMENT.md` | Device category E |
| `ARCH-2026-06-10-REFERRAL-ACQUISITION-PORTAL-ANALYTICS.md` | Referral category F |
| `BENDERVPN-PRODUCT-POLICY.md` §9 | Support policy |

---

**SUPPORT-AI-ARCH-001 complete.** No implementation. No AI runtime. No credentials.
