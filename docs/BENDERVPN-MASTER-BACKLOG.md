# BenderVPN Master Backlog

**Status:** canonical · **FROZEN:** 2026-06-10 ([`AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md`](AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md))
**Branch:** `product-referral-cabinet-ui-v1`
**Purpose:** single source of truth for product, technical, audit, UX, ops, and deferred decisions — nothing lost between sessions.

**Related docs:**

| Document | Role |
|----------|------|
| [`BENDERVPN-PRODUCT-POLICY.md`](BENDERVPN-PRODUCT-POLICY.md) | Accepted owner decisions (policy v1) |
| [`STRATEGY-2026-06-10-GROWTH-POSITIONING-CAPACITY.md`](STRATEGY-2026-06-10-GROWTH-POSITIONING-CAPACITY.md) | Positioning, copy workflow, 10k growth model, capacity gates |
| [`ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md`](ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md) | Portal-first referral acquisition, slots, trial cap, temp access, paid conversion (ACQUISITION-JOURNEY-001) |
| [`ARCH-2026-06-10-QA-SANDBOX-CUSTOMER-JOURNEYS.md`](ARCH-2026-06-10-QA-SANDBOX-CUSTOMER-JOURNEYS.md) | QA/staging sandbox for customer journey scenarios (QA-SANDBOX-001) |
| [`BENDERVPN-PRODUCT-QUALITY-PLAN.md`](BENDERVPN-PRODUCT-QUALITY-PLAN.md) | Portal UX execution log (Batches 1–3 done) |
| [`BENDERVPN-AUDIT-ROADMAP.md`](BENDERVPN-AUDIT-ROADMAP.md) | Ordered audit sequence |
| [`BACKLOG-QUEUE.md`](BACKLOG-QUEUE.md) | Linear ops Q001+ queue (infra phases closed) |
| [`BACKLOG-MAP.md`](BACKLOG-MAP.md) | Legacy doc hierarchy map |
| [`BACKLOG-VPN-FULL-AUDIT-2026-05-28.md`](BACKLOG-VPN-FULL-AUDIT-2026-05-28.md) | VPN infra backlog (gen/sub/routing) |
| [`VPN-INCIDENT-LESSONS-2026-05-25.md`](VPN-INCIDENT-LESSONS-2026-05-25.md) | Hotfix guardrails |
| [`INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md`](INCIDENT-DIAG-2026-06-10-WINDOWS-SLEEP-RESUME-MAIL.md) | INCIDENT-DIAG-003-004 — Windows Happ report (sleep/mail) |
| [`INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md`](INCIDENT-DIAG-2026-06-10-HAPP-TUN-DAEMON-PROXY-FALLBACK.md) | CLIENT-STABILITY-001 — TUN daemon + Bender Proxy Track A/B |
| [`INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md`](INCIDENT-DIAG-2026-06-12-HAPP-TUN-ACTIVE-FAILURE.md) | CLIENT-STABILITY-001 — DirectIp fix; report(5) relay egress; [recovery capture](CLIENT-STABILITY-HAPP-RECOVERY-CAPTURE.md) |
| [`CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md) | CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-001 — report(10): single relay endpoint = 80% of resets; TUN/routing healthy; relay-path fix proposed |
| [`CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md) | CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001 — bad relay mapped to ru-relay-1; registry incident + owner/staging desktop canary excludes bad path, keeps healthy relay #2 |
| [`DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md`](DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md) | DESKTOP-RELAY1-SERVICE-REPAIR-DEPLOY-001 — relay1 is hysteria TCP-forwarder (no xray); scoped hysteria-client restart did NOT clear resets; relay1 kept degraded; relay2-only canary = workaround; deeper rebuild owner-gated |
| [`RU-RELAY-ARCH-UNIFICATION-2026-06-17.md`](RU-RELAY-ARCH-UNIFICATION-2026-06-17.md) | RU-RELAY-ARCH-UNIFICATION-001 — relay1≡relay2 (identical hysteria forwarders, shared upstream, same error rate); formalized STANDARD_RU_RELAY_PATH_V1; registry path_role/architecture_compliance/shared_upstream_group + fail-closed pool gate (+tests); real gap = independent exit/upstream |
| [`CODERABBIT-AUDIT-TRIAGE-2026-06-14.md`](CODERABBIT-AUDIT-TRIAGE-2026-06-14.md) | CodeRabbit commercial launch triage — accepted blockers + remediation order (`c03f638`) |
| [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) | Target 30k capacity architecture — backend-controlled multi-node delivery |
| [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md) | Fast node bring-up runbook (unified template) |
| [`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md) | Operational node acceptance checklist |
| [`VPN-ROUTING-PROFILE-STRATEGY.md`](VPN-ROUTING-PROFILE-STRATEGY.md) | Happ routing strategy; SafeVPN reference boundaries |
| [`examples/node-registry.example.yaml`](examples/node-registry.example.yaml) | Node registry schema v1 (redacted example) |

---

## 1. Executive summary

### Current product state

| Layer | State |
|-------|-------|
| **Portal client journey** | **Good enough for pilot** — two-path landing (TG 90d + email 1d), legal 90d/1d distinction, capacity badge hidden, status/setup/errors aligned |
| **Product policy** | **Locked** — `BENDERVPN-PRODUCT-POLICY.md` v1 (2026-06-09) |
| **Backend vs policy** | **Misaligned** — invite gate, capacity cap, device limit, web referral attribution, cabinet API fields |
| **VPN reliability** | **User reports unstable connection / reconnect loops** — needs read-only diagnostic before any routing patch |
| **Admin/reporting** | **Incomplete** — referral ledger, user lookup, funnel metrics missing |
| **Ops queue (Q001+)** | **Phases 1–17 closed** — infra scale/monetize/VPN node resilience done; product-logic track is separate |

### What is already done

- Portal UX Batches 1–3 (`7ffe7c5`, `a54f7a2`, `19678fa`, `3a9fa73`) — cabinet fallback, legal terms, onboarding copy, guide nav, a11y, two-path CTA
- UX-201–207 — status visual language, capacity counter hidden, support `/id`
- Product Policy v1 + Decision Workshop (`81db9a2`)
- VPN infra: xhttp Happ trim (Q-VPN-STAB-005), sub HA, transport mux, commerce go-live (per `BACKLOG-QUEUE.md`)

### Biggest remaining risks

| Risk | Severity | Why |
|------|----------|-----|
| **VPN reconnect instability** | P0/P1 | Direct user pain; may be routing/sub/Happ — patch without audit risks repeat of gen-13→20 incidents |
| **TG bind / referral migration** | P0 | G4 BLOCKED; web attr fixed but bind unproven |
| **Same-sub URL reuse undetected** | P0 | DEVICE-ENFORCE-001; bypasses billing × N |
| **Policy vs code gaps** | P1 | Invite-only, 30k cap, one-device are copy-only |
| **No admin visibility** | P1/P2 | Cannot scale invites, detect fraud, or hit 300-config threshold safely |
| **REG-001 not designed** | P2 | Recovery, fraud, legal reconciliation deferred |
| **Legal/privacy final review** | P2 | REG-001 and support visibility not reconciled |

### Audit closeout (2026-06-10)

**AUDIT-CLOSEOUT-001:** [`AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md`](AUDIT-CLOSEOUT-2026-06-10-LAUNCH-BACKLOG-FREEZE.md) — audits **closed**; implementation starts **TRACK 0** tomorrow.

**STRATEGY-GROWTH-001:** [`STRATEGY-2026-06-10-GROWTH-POSITIONING-CAPACITY.md`](STRATEGY-2026-06-10-GROWTH-POSITIONING-CAPACITY.md) — commercial positioning, copy standards, 10k growth + capacity planning (docs only; before large-scale copy/backend work).

### Frozen implementation tracks (priority order)

| Track | Focus | Tomorrow? |
|-------|-------|-----------|
| **TRACK 0** | Copy/UX hygiene — COPY-TRUTH, DEVICE-COPY, REF-COPY, SETUP-UX | **Yes** |
| **TRACK 1** | Bind + referral — G4-BIND-RETEST, REF-PORTAL, REF-ADMIN | Partial tomorrow |
| **TRACK 2** | Billing proof — **CodeRabbit remediation** (BILL-TERMS-GUARD → BILL-UT), BILL-SMOKE prep | **Yes** — before automated paid pilot |
| **TRACK 3** | Device — SMOKE, ENFORCE, DATA, ADMIN, BILL | After TRACK 0–2 |
| **TRACK 4** | VPN stability + **node capacity readiness** — INCIDENT-003/004, **VPN-ARCH-001**, **VPN-ARCH-30K pack**, NL revalidation AC | Owner-led; before growth |
| **TRACK 5** | Monitoring / CI / runbooks — **MONITOR-FLAP-001**, **OPS-ALERT-HYGIENE-001**, G9/G11 | After soft blockers; before acquisition scale |
| **TRACK 6** | Support AI / technical triage | After P1-ADM + runbooks; not F&F blocker |

### Tomorrow queue (TRACK 0 + prep)

1. ~~**COMMERCIAL-UX-DEVICE-MVP-001**~~ — portal cabinet/setup MODEL A UX (**DONE** repo `product-referral-cabinet-ui-v1`, not deployed)
2. ~~**DEVICE-COPY-001**~~ — portal `ru.json` MODEL A copy (**DONE** in COMMERCIAL-UX-DEVICE-MVP-001)
3. ~~**COPY-TRUTH-001**~~ — bot ghost labels + NL/LV removal (**DONE** repo, not deployed)
4. ~~**SETUP-UX-001**~~ — link-first setup page (**DONE** in COMMERCIAL-UX-DEVICE-MVP-001)
5. ~~**CABINET-TYPE-001**~~ — balance typography (**DONE** in COMMERCIAL-UX-DEVICE-MVP-001)
6. ~~**P1-REF-002**~~ — gate hidden +3d invitee bonus OFF; target reward = +1 month to referrer (REF-BONUS-001 deferred) (**DONE** repo, not deployed)
7. **REF-COPY-001** — soften `referral_preserve_note` (separate commit; **not started**)
8. **G4-TG-BIND-RETEST-001** — owner in-app bind after handoff deploy (`ed8b563`)
9. **BILL-TERMS-GUARD-001** — terms on all trial/pay/wizard callbacks + tests
10. **TRIAL-GRANT-ATOMIC-001** — atomic/idempotent trial grant
11. **BILL-AUTOPAY-LIVE-GUARD-001** — defense-in-depth in autopay batch
12. **BILL-BALANCE-KOPEKS-001** — kopeks/Decimal day-rate
13. **BILL-UT-001/002** — offline billing + webhook/idempotency unit tests
14. **BILL-SMOKE-001 prep** — script skeleton only

### VPN capacity architecture pack (2026-06-15) — docs DONE, implementation OPEN

Source: owner decision — stop isolated client smoke loops; prepare **backend-controlled multi-node delivery** for 30k path. Pack commit: **`VPN-ARCH-30K-CAPACITY-PACK-001`**.

| # | ID | Sev | Doc status | Impl status | Blocks |
|---|-----|-----|------------|-------------|--------|
| — | **VPN-ARCH-30K-CAPACITY-PACK-001** | P0 | **DONE** | — | Umbrella doc pack |
| — | **VPN-ARCH-30K-CAPACITY-PLAN-001** | P0 | **DONE** | OPEN | 300/30k gates |
| — | **VPN-NODE-RUNBOOK-001** | P1 | **DONE** ([`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md)) | OPEN (automation) | Fast node scale |
| — | **VPN-NODE-REGISTRY-001** | P1 | **DONE** | **DONE** (repo SoT) | Assignment engine |
| — | **SUB-GEN-SELECTOR-STRATEGY-001** | P0 | **DONE** | **DONE** (dry-run) | Live sub integration |
| — | **SUB-GEN-SELECTOR-INTEGRATION-001** | P0 | **DONE** (shadow) | **SHADOW DONE / APPLY OPEN** | Owner review + generator wiring; [`ops/vpn_sub_assignment_shadow.py`](../ops/vpn_sub_assignment_shadow.py) |
| — | **SUB-GEN-SELECTOR-APPLY-001** | P0 | OPEN | OPEN | Owner-reviewed apply (snapshot+rollback); never auto |
| — | **VPN-NODE-PROCUREMENT-POLICY-001** | P1 | **DONE** | — | Owner-safe VPS purchase ([`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) §13) |
| — | **UX-AUTO-CONNECT-PRINCIPLE-001** | P1 | **DONE** | — | One-button BenderVPN Auto; no server picker ([§14](VPN-ARCH-30K-CAPACITY-PLAN.md)) |
| — | **ROUTING-PROFILE-RU-DIRECT-001** | P1 | **DONE** ([`VPN-ROUTING-PROFILE-STRATEGY.md`](VPN-ROUTING-PROFILE-STRATEGY.md)) | OPEN | Routing pack + tests |
| — | **NODE-SMOKE-MATRIX-001** | P1 | **DONE** (acceptance checklist) | OPEN (runner) | Node quality |
| — | **NODE-SMOKE-MATRIX-RUNNER-001** | P1 | **DONE** | **DONE** | [`ops/vpn_node_smoke_matrix.py`](../ops/vpn_node_smoke_matrix.py) — registry→readiness matrix (dry-run); 11 tests |
| — | **SUB-GEN-SELECTOR-APPLY-GATE-001** | P0 | **DONE** | **DONE** | [`ops/vpn_selector_apply_gate.py`](../ops/vpn_selector_apply_gate.py) — APPLY_ALLOWED gate (read-only); 8 tests |
| — | **CLIENT-STABILITY-OWNER-CANARY-PROFILE-001** | P1 | **DONE** | **DONE** | [`ops/generate_owner_canary_profile.py`](../ops/generate_owner_canary_profile.py) — owner-only `.local` profile plan; 9 tests |
| — | **RELAY1-DRAIN-OR-RETEST-001** | P0 | **DONE** | **DONE** (policy+tests) | [`RELAY1-DRAIN-OR-RETEST-DECISION.md`](RELAY1-DRAIN-OR-RETEST-DECISION.md) — suspect-exclusion enforced; owner go/no-go |
| — | **NODE-ONBOARD-NEW-PROD-PATH-001** | P0 | **DONE** | **READY FOR OWNER ACTION** | [`VPN-NODE-PURCHASE-REQUEST.md`](VPN-NODE-PURCHASE-REQUEST.md) + [`VPN-NODE-ONBOARDING-EXECUTION.md`](VPN-NODE-ONBOARDING-EXECUTION.md) + template + [`ops/prepare_new_node_registry_entry.py`](../ops/prepare_new_node_registry_entry.py) |
| — | **VPN-SELECTOR-SPEED-STABILITY-POLICY-001** | P1 | **DONE** | **DONE** | Selector excludes suspect/lab/disabled/backup; 7 tests |
| — | **VPN-CORE-SCALABILITY-STABILITY-SPRINT-001** | P0 | **DONE** | **DONE** | Execution sprint umbrella; `delivery_path_nodes` gate still NO-GO until 2nd node |
| — | **VPN-ARCH-CONSOLIDATION-001** | P0 | **DONE** | **DONE (partial; cron migration pending)** | Stop patch-on-patch; central guardrails + apply-gate integration + legacy hardening |
| — | **VPN-PRODUCTION-GUARDRAILS-001** | P0 | **DONE** | **DONE** | [`docs/VPN_PRODUCTION_GUARDRAILS.md`](VPN_PRODUCTION_GUARDRAILS.md) + [`ops/vpn_production_guardrails.py`](../ops/vpn_production_guardrails.py); 21 tests |
| — | **VPN-AUTO-CUTTING-GUARD-001** | P0 | **DONE** | **PARTIAL (3/4 cron migrated)** | Manual patchers gated; autotrim + injecthosts sync + relay_failover guardrail-wired; LV→NL failover pair remains |
| — | **VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-001** | P0 | **DONE** | **DONE (repo-side; no prod apply)** | Registry-driven model + generator + integrity verifier + stealth guard + proxy-N decouple; [`docs/VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-2026-06-17.md`](VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-2026-06-17.md) |
| — | **VPN-INVENTORY-DRIVEN-CONFIG-GENERATOR-001** | P0 | **DONE** | **DONE (dry-run; .local only)** | [`ops/vpn_registry_model.py`](../ops/vpn_registry_model.py) + [`ops/generate_vpn_config_from_registry.py`](../ops/generate_vpn_config_from_registry.py); node_id→tag→cohort; PUBLIC_PROD NO-GO until 2 paths; 21 tests |
| — | **VPN-CONFIG-INTEGRITY-VERIFIER-001** | P0 | **DONE** | **DONE** | [`ops/vpn_config_integrity.py`](../ops/vpn_config_integrity.py) — UUID↔host↔selector↔node_id; count-only rejected; already-applied proves injected+enabled; 10 tests |
| — | **VPN-PROXY-N-DECOUPLE-001** | P0 | **DONE** | **PARTIAL** | Model/generator/verifier are position-independent (out-<node_id>); `patch_add_relay_nl` integrity-gated; legacy positional selectors quarantined by verifier |
| — | **VPN-STEALTH-ROUTING-GUARDRAILS-001** | P1 | **DONE** | **DONE** | [`ops/vpn_stealth_routing_guard.py`](../ops/vpn_stealth_routing_guard.py) — TG/Meta stay stealth; no Super_Balancer catch-all; Happ DirectIp geoip:ru regression guard; 7 tests |
| — | **NL-CANARY-PREP-001** | P1 | **DONE** | **DONE (artifact)** | NL staging; synthetic canary preview + `.local/nl_canary_owner_profile.*`; [`docs/NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md`](NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md) |
| — | **NL-A2-A4-CONTROLLED-CANARY-SMOKE-001** | P0 | **PARTIAL** | **OPEN (traffic)** | SSH revalidation PASS; synthetic preview; awaits owner APPROVE NL CANARY TRAFFIC SMOKE |
| — | **SCRIPT-MIGRATE-INJECTHOSTS-SYNC-001** | P0 | **DONE** | **DONE** | [`ops/sync_injecthosts_connected.py`](../ops/sync_injecthosts_connected.py) — central guardrail on apply; UUID↔selector consistency; 20 tests; bare `--apply` fails closed |
| — | **VPN-CAPACITY-GATE-001** | P0 | **DONE** | **DONE** | Apply gate consumes central guardrail; PUBLIC_PROD APPLY_ALLOWED=false; guardrail blockers surfaced |
| — | **VPN-NODE-INVENTORY-SOT-001** | P1 | **DONE (examples/templates)** | OPEN (live schema bump) | Lifecycle/capacity vocabulary documented; live registry unchanged |
| — | **VPN-PATCH-SCRIPT-MIGRATION-MAP-001** | P0 | **DONE** | **DONE** | [`docs/VPN_PATCH_SCRIPT_MIGRATION_MAP.md`](VPN_PATCH_SCRIPT_MIGRATION_MAP.md) — "partially patch-on-patch"; P0/P1/P2 |
| — | **SCRIPT-MIGRATE-LATENCY-AUTOTRIM-001** | P0 | **DONE** | **DONE** | [`ops/latency_selector_autotrim.py`](../ops/latency_selector_autotrim.py) — central guardrail on apply; 18 tests; bare `--apply` fails closed |
| — | **SCRIPT-MIGRATE-INJECTHOSTS-SYNC-001** | P0 | OPEN | OPEN | Registry-driven injectHosts sync with host-count floor |
| — | **SCRIPT-MIGRATE-RELAY-FAILOVER-001** | P0 | **DONE (partial)** | **PARTIAL** | `relay_failover_template` → central guardrail (mode+TTL+rollback+owner; relay collapse blocked); 8 tests. LV→NL failover pair still OPEN |
| — | **SCRIPT-MIGRATE-NL-RELAY-PATCHERS-001** | P1 | OPEN | OPEN | Replace hardcoded add-node patchers with registry onboarding |
| — | **NODE-RU-NL-BALANCER-CANARY-001** | P0 | **PARTIAL** | **PARTIAL** | [`docs/NODE-RU-NL-BALANCER-CANARY-2026-06-17.md`](NODE-RU-NL-BALANCER-CANARY-2026-06-17.md) — SSH inventory PASS; NL `disabled→staging`; owner canary generated; live apply owner-gated |
| — | **NL-NODE-CANARY-ENABLE-001** | P0 | **PARTIAL** | **OPEN** | NL SSH PASS + artifact ready; needs A2/A4 traffic smoke + owner APPROVE PROD APPLY before `staging→canary` |
| — | **RU-NODE-CANARY-ENABLE-001** | P1 | OPEN | OPEN | ru-relay-2 reachable/healthy candidate; relay-1 stays suspect; canary needs owner approval |
| — | **ROLLOUT-CANARY-DRAIN-001** | P1 | **DONE** (in runbook + plan) | OPEN | Safe rollout |
| — | **MONITOR-CAPACITY-001** | P1 | OPEN | OPEN | Capacity dashboard/alerts |

**Architecture decision:** relay2-only = **`LAB_OWNER`** evidence only — **not** production default. **`delivery_path_nodes < 2`** remains blocker for 300/30k. **UX:** one-button BenderVPN Auto — users do not pick servers. **Procurement:** monthly trial first; no long prepaid before acceptance.

**Implementation order after pack:** ~~VPN-NODE-REGISTRY-001~~ **DONE** → ~~**SUB-GEN-SELECTOR-STRATEGY-001**~~ **DONE (dry-run)** → ~~**VPN-NODE-PROCUREMENT-POLICY-001**~~ **DONE** → ~~**UX-AUTO-CONNECT-PRINCIPLE-001**~~ **DONE** → **SUB-GEN-SELECTOR-INTEGRATION-001** → runbook automation → NODE-SMOKE-MATRIX runner → MONITOR-CAPACITY-001 → ROLLOUT-CANARY-DRAIN-001 → NL A2/A4 / relay #1 paths.

### CodeRabbit remediation order (2026-06-15)

Source: [`CODERABBIT-AUDIT-TRIAGE-2026-06-14.md`](CODERABBIT-AUDIT-TRIAGE-2026-06-14.md) (`c03f638`). **Rejected Rabbit claims preserved:** test count “2 only” (repo has **72** pytest); LV+NL capacity PASS for 300 (**NO-GO** until ≥2 verified delivery paths).

| # | ID | Sev | Status | Blocks |
|---|-----|-----|--------|--------|
| 1 | **BILL-TERMS-GUARD-001** | P0 | OPEN | Automated paid pilot; legal on money/trial paths |
| 2 | **TRIAL-GRANT-ATOMIC-001** | P1 | OPEN | Paid beta scale; trial retry after crash |
| 3 | **BILL-AUTOPAY-LIVE-GUARD-001** | P1 | OPEN | Autopay hardening (**PAY-AUTO-001**) |
| 4 | **BILL-BALANCE-KOPEKS-001** | P1 | OPEN | Honest 200 ₽ ≈ 30 days copy |
| 5 | **BILL-UT-001** | P0 | OPEN | Offline debit/day-rate tests |
| 5 | **BILL-UT-002** | P0 | OPEN | Offline webhook/idempotency/autopay tests |
| — | **BILL-WEBHOOK-CLAIM-TOCTOU-001** | P1 | OPEN | Atomic webhook claim |
| — | **BOT-QR-MISSING-KEY-UX-001** | P2 | OPEN | `show_qr_handler` silent returns |
| — | **BILL-LEGACY-PAYMENT-FLOW-GATE-001** | P2 | OPEN | Legacy `buy_*_month` sunset |
| — | **SUBSCRIPTION-RESOLVE-TZ-001** | P2 | OPEN | Naive `datetime.now()` in resolve |
| 6 | **G4-TG-BIND-RETEST-001** | P0 | OPEN | Referral/public acquisition |
| 7 | **CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001** | P0 | ELIGIBLE | Owner approval only — not auto |
| 8 | **CLIENT-STABILITY-MOBILE-SMOKE-001** | P0 | PENDING | Mobile acquisition |
| — | **CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-001** | P0 | **DIAGNOSED** | report(10): one relay endpoint = 80.3% of resets; TUN/routing/profile healthy → [`CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-HAPP-DROPOUT-2026-06-17.md) |
| — | **CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001** | P0 | **DONE (owner-gated)** | bad relay = ru-relay-1; registry incident + exclude_from_desktop_canary; owner/staging desktop canary excludes bad path → [`CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md) |
| — | **DESKTOP-RELAY1-SERVICE-REPAIR-DEPLOY-001** | P0 | **PARTIAL (owner-gated)** | relay1 = hysteria TCP-forwarder (no xray, diverges from runbook); upstream reachable; scoped `systemctl restart hysteria-client` did NOT clear forwarding resets → kept degraded; relay2-only canary = workaround → [`DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md`](DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md) |
| — | **RU-RELAY-ARCH-UNIFICATION-001** | P0 | **DONE (PATH C)** | relay1≡relay2 (identical hysteria forwarders, **shared upstream ru-fwd-upstream-1**, same error rate) → relay1 not uniquely broken; formalized **STANDARD_RU_RELAY_PATH_V1**; registry `path_role`/`architecture_compliance`/`shared_upstream_group` + fail-closed generator gate + 230 tests green → [`RU-RELAY-ARCH-UNIFICATION-2026-06-17.md`](RU-RELAY-ARCH-UNIFICATION-2026-06-17.md) |
| — | **NEW-INDEPENDENT-EXIT-PATH-001** | P0 | **DONE — PATH A (owner-gated smoke)** | nl-node-1 VALIDATED as the 2nd INDEPENDENT exit candidate → [`NEW-INDEPENDENT-EXIT-PATH-2026-06-17.md`](NEW-INDEPENDENT-EXIT-PATH-2026-06-17.md) |
| — | **NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-AND-PROMOTION-001** | P0 | **WAITING (owner smoke)** | Enhanced `.local/independent_exit_nl_canary.*` runbook (import, 10–15 min checklist, PASS/PARTIAL/FAIL, record template); **no** owner PASS ingested; registry **not** promoted; `independent_exit_paths=1` → [`NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md`](NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md) |
| — | **CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-001** | P0 | OPEN (proposed) | De-weight/replace resetting relay; owner-gated read-only check or owner canary — no broad apply |
| 9 | **MONITOR-FLAP-TUNE-001** | P1 | SOAK OPEN | Before NL A2/A4 |
| 10 | **VPN-ARCH-001** | P1 | AWAITING APPROVAL | Capacity ≥2 delivery paths |

### ACQUISITION-JOURNEY-001 backlog (architecture done — implementation gated)

See [`ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md`](ARCH-2026-06-10-PORTAL-FIRST-ACQUISITION-JOURNEY.md). **Do not implement** until owner approves per-surface commits.

| ID | P | Status | Summary |
|----|---|--------|---------|
| **ACQ-PORTAL-001** | P1 | OPEN | Portal referral landing, gate API, portal-first share URL |
| **ACQ-IDENTITY-001** | P1 | OPEN | Lead schema; phone+email required; dedup |
| **ACQ-TRIAL-CAP-001** | P1 | OPEN | 90d trial closes at **300 active configs/devices**; bot+portal sync — **also requires node capacity acceptance** (see §Node capacity) |
| **ACQ-TEMP-001** | P1 | OPEN | Identity-bound 1d temp access (model B) |
| **ACQ-PAID-CONVERT-001** | P1 | OPEN | Paid start + temp→paid same config |
| **ACQ-BOT-BIND-001** | P0 | OPEN | G4 bind + portal lead merge |
| **ACQ-SLOTS-001** | P2 | OPEN | Active config count; 30k slots; public badge gate — **capacity forecast + infra headroom** before badge/gate goes live |

**Commercial acquisition / referral growth — do not proceed without (link existing IDs only):**

- **≥2 production-capable nodes/relays in the customer delivery path** — both must participate in auto host / generated subscriptions / routing, **or** non-participating paid server is decommissioned/replaced; **one Latvia-only path is not acceptable** for growth
- **VPN-ARCH-001** — NL/Amsterdam revalidation acceptance (read-only first; do not blindly re-enable); **VPN-NODE-RUNBOOK-001** — fast node+relay bring-up template
- **MONITOR-FLAP-001** + **OPS-ALERT-HYGIENE-001** — monitoring must be trustworthy before using alerts as node-quality source of truth
- **ACQ-SLOTS-001** + **ACQ-TRIAL-CAP-001** — product + **infra** capacity gate at 300 active configs/devices (not **OPS-CAPACITY-300-001**)
- RU relay diversity: **Q120** / **VPN-AUD-201 DONE** (historical second relay) — not **NODE-RELAY-ADD-001**

### Node capacity & delivery path readiness (BACKLOG-CAPACITY-NODES-001)

**Owner rule (2026-06-11):** Netherlands/Amsterdam may be paid but **not participating** in Bender auto host / subscription routing today. Before acquisition/referral growth or **300 active configs/devices**:

| Requirement | IDs / evidence |
|-------------|----------------|
| Two verified production-capable surfaces on the **customer path** | **≥2 geographic VPN exits** in generated profiles/routing (not relay-only×6 to single LV); NL if revalidated, or new node per **VPN-NODE-RUNBOOK-001** |
| NL participation decision | **VPN-ARCH-001** owner AC — see below; **PROOF-001** + **QUALITY-PROOF-001 DONE** (2026-06-11); historical **VPN-AUD-220** / **Q167–Q171** are **not** live proof of normal Auto capacity |
| Repeatable fast scale template | **VPN-NODE-RUNBOOK-001** OPEN — gaps vs `deploy-node.sh` / `THIRD-PROD-NODE-ONBOARDING.md` |
| Alert hygiene before infra decisions | **MONITOR-FLAP-001**, **OPS-ALERT-HYGIENE-001** |
| Infra queue (closed phases) | **Q167–Q171** node resilience DONE; **Q120** second RU relay DONE — do not reopen as new relay-add IDs |

**VPN-ARCH-001 — Netherlands/Amsterdam revalidation acceptance (no NODE-NL-REVALIDATE-001):**

**VPN-ARCH-001-NL-AUTOHOST-PROOF-001 — DONE (read-only, 2026-06-11):**

| Finding | Live evidence (2026-06-11) |
|---------|----------------------------|
| Normal Bender Auto customer path | **Candidate D relay-only×6** — RU relay #1 ×3 + RU relay #2 ×3 in `injectHosts`; **NL=0, LV direct=0, AMS=0** |
| Generated ACTIVE Happ subs | 6 vless relay outbounds; **`Intl_Direct` / `Intl_Stealth`** = `RELAY6_SELECTOR` only; sampled users **NL=0** (`probe_subscription`, `transport_mux_audit`) |
| NL panel state | **Connected/enabled**; hosts exist; **not** in live `injectHosts` or Intl selectors |
| Effective VPN exit | **Single LV geography** behind relays — relay diversity ≠ second prod node |
| NL roles today | **Failover/manual** (`lv_node_down_nl_failover.py`, Q167–Q171); **backup sub edge** `n4l8q:4433` — **not** active delivery capacity |
| Amsterdam-01 | **Disconnected/disabled** — panel/sub-page; not prod VPN capacity |
| Classification | Normal Auto/new users: **D** (documented/backup, not participating); LV-down emergency: **C** (manual/cron PATCH) |

**VPN-ARCH-001-NL-QUALITY-PROOF-001 — DONE (read-only, 2026-06-11):**

| Finding | Evidence |
|---------|----------|
| NL still **not** active delivery capacity | `usersOnline=0`; ACTIVE subs **NL outbounds=0**; live `injectHosts` **NL=0** — billable/maintained, unused for normal Auto |
| RU reachability (customer-relevant path) | **`nl_reachability_probe_ru.py` PASS from bvpn-lv** — relay#1→NL ~60.5 ms, relay#2→NL ~54.8 ms (gate 120 ms) |
| NL infra health | remnanode + caddy-selfsteal up; low load; **BBR/fq**; ru-monitor NL TLS alive |
| A2/A4 tooling feasible | **`patch_add_nl_intl_gated.py`** — NL direct ×4 in **`Intl_Direct` only**; **`Intl_Stealth`** stays relay-only; no observatory; no blind **VPN-AUD-220** restore |
| Pre-qualified, not prod-ready | **No** end-to-end Happ/VLESS through NL direct yet; **MONITOR-FLAP-001** soak **PARTIAL** (2026-06-13) — residual `microsoft.com` quorum TG; NL A2/A4 needs owner risk acceptance or tuning first |
| Tooling caveat | **`nl_node_health_probe`** may report **FAIL** pre-inclusion because it expects **`injectHosts` NL ≥4** — precondition mismatch, **not** a node-quality rejection before A2/A4 smoke |

**Failover-ready or paid/connected does not equal active customer capacity.** NL **does not count** toward **`delivery_path_nodes`** until included in generated profiles/routing, **controlled smoke passes**, post-inclusion audit shows ACTIVE users with NL path, and owner accepts NL as active capacity. Acquisition/referral growth and **300 active configs/devices** remain **blocked**.

**Owner path after proof (recommended, not decided):**

| Option | Guidance |
|--------|----------|
| **Preferred** | Continue toward **A2/A4 controlled smoke** after **MONITOR-FLAP-001** soak **PARTIAL** accepted by owner (or **MONITOR-FLAP-TUNE-001** done) + explicit approval — **not** blind prod PATCH |
| **Interim B** | Failover-only acceptable **short-term** while soak completes; **does not** satisfy growth/300 gate |
| **Not now C** | Do **not** decommission — NL healthy; backup edge + failover value |
| **Not now D** | Pivot to another node **only** if controlled smoke fails or owner rejects NL |

**Controlled smoke gates (before any `--apply` / prod template mutation):**

1. **MONITOR-FLAP-001** — soak **PARTIAL** (2026-06-13); **MONITOR-FLAP-TUNE-001 deployed LV** — short soak review ~17:16 / ~22:46 UTC before NL A2/A4
2. **Owner explicit approval** for **A2/A4** smoke (Option A)
3. Template **snapshot / rollback** ready (`.secrets/snapshots/template-before-nl-intl-*.json`; **`patch_restore_6relay_stealth.py`** rollback path)
4. **`patch_add_nl_intl_gated.py` dry-run** from **bvpn-lv** (RU probe requires relay SSH keys on LV)
5. **Limited cohort:** owner + **1–3 internal/mobile** users only — **CLIENT-STABILITY-001** desktop **out of scope** for first cohort
6. Post-`--apply` verify: **`verify_vpn_balancer_profile`**, **`probe_subscription`**, **`probe_routing`**
7. **`transport_mux_audit`** — NL **> 0** for smoke cohort (not yet global)
8. **Happ mobile** import/connect smoke — [CLIENT-STABILITY-MOBILE-SMOKE-001](CLIENT-STABILITY-MOBILE-SMOKE.md); confirm **TG/IG/Meta still relay-only** via **`Intl_Stealth`**
9. **Rollback path confirmed** before broadening traffic
10. User impact plan: **`subscription_config_notify`**, generation bump comms

**Owner decision required (pick one path before any prod routing/template mutation):**

| Option | Meaning |
|--------|---------|
| **A** | Re-include NL in active Bender Auto routing after quality/soak gates |
| **B** | Keep NL paid **failover-only**; accept cost; do not count NL in capacity math |
| **C** | Decommission or repurpose NL VPS |
| **D** | Add or replace with **another production node** first (via **VPN-NODE-RUNBOOK-001**) |

Questions: Should NL return to active Auto routing? Stay failover-only? Be decommissioned/replaced? Should a third prod node be added before NL re-entry?

**Remaining VPN-ARCH-001 AC (post-proof):**

1. ~~Read-only: does NL appear in auto host / generated subs / injectHosts?~~ → **No (PROOF-001)**
2. ~~Read-only: NL RU reachability + infra quality?~~ → **Pre-qualified (QUALITY-PROOF-001)**; controlled smoke still required
3. **MONITOR-FLAP-001** 24h soak PASS → owner authorizes **A2/A4 controlled smoke**
4. Owner picks A/B/C/D for long-term (stays **AWAITING APPROVAL** until smoke + decision)
5. If smoke PASS: post-inclusion audit; NL counts toward **`delivery_path_nodes`** only then
6. If smoke FAIL: pivot **D** or keep **B** — do **not** force NL; do **not** blindly restore **VPN-AUD-220**

**VPN-NODE-RUNBOOK-001 — fast node + relay bring-up (not Q120 / VPN-AUD-201):**

Historical **Q120** / **VPN-AUD-201** = second RU relay delivered once. **VPN-NODE-RUNBOOK-001** = reusable template for future fast capacity expansion when user influx spikes.

| AC | Requirement |
|----|-------------|
| 1 | Documented repeatable template for adding a production-capable node/relay |
| 2 | Defines what must be configured **before** users receive configs on the new server |
| 3 | Minimum quality: latency, throughput, packet loss/stability, Caddy/selfsteal, RU reachability (if relevant), client import/connect smoke, monitoring alert hygiene |
| 4 | Gradual traffic: internal smoke → owner test → small cohort → new-user-only routing → broader routing |
| 5 | Rollback: remove from auto host/routing; stop issuing new configs; support notify; decommission if unstable |
| 6 | Owner approval gates at routing inclusion and production-ready |

**Partial existing material (link, do not duplicate):** `deploy-node.sh`, `docs/DEPLOY.md`, `docs/NODE-POLICY-LV-NL.md`, `docs/THIRD-PROD-NODE-ONBOARDING.md`, `docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md` — gap = unified checklist + controlled onboarding + soak + decommission.

**300 active configs/devices — capacity acceptance checklist (ACQ-TRIAL-CAP-001 / ACQ-SLOTS-001):**

- Active configs/devices forecast vs **≥2** **verified** delivery-path nodes (NL counts **only after** controlled smoke + post-inclusion audit)
- CPU/RAM/network headroom per node
- Latency/throughput + packet loss / reconnect rate
- Selfsteal/Caddy stability (post **MONITOR-FLAP-001**)
- RU reachability where relevant
- Monitoring alert hygiene (**OPS-ALERT-HYGIENE-001**)
- Support incident volume baseline
- Client connection quality (Happ smoke)
- Rollback/failover path documented (**RUNBOOK-LV-DOWN-NL-FAILOVER.md**, **VPN-NODE-RUNBOOK-001**)

### QA-SANDBOX-001 backlog (architecture done — implementation gated)

See [`ARCH-2026-06-10-QA-SANDBOX-CUSTOMER-JOURNEYS.md`](ARCH-2026-06-10-QA-SANDBOX-CUSTOMER-JOURNEYS.md). Staging/local only; production-identical code paths; mocks at YooKassa/Remna boundaries only.

| ID | P | Status | Summary |
|----|---|--------|---------|
| **QA-SANDBOX-001** | P1 | **DONE** (doc) | Architecture — this document |
| **QA-GUARD-001** | P0 | **DONE** (repo) | `runtime_env.py`; Remna/YooKassa boundary guards; `ops/test_runtime_env_guards.py` |
| **QA-STAGING-BOT-001** | P1 | OPEN | Staging bot + isolated DB + portal origin runbook |
| **QA-DB-SEED-001** | P1 | **DONE** (repo) | `ops/qa_seed_scenarios.py`; `ops/test_qa_seed_scenarios.py` |
| **QA-BOT-FAKE-TG-001** | P1 | **DONE** (repo) | `qa_bot_fake_tg.py`; `ops/test_qa_bot_fake_tg.py` |
| **QA-REMNA-DRYRUN-001** | P1 | **DONE** (repo) | `remna_dryrun.py`; `ops/test_remna_dryrun.py` |
| **QA-PAYMENT-DRYRUN-001** | P1 | **DONE** (repo) | `yookassa_dryrun.py`; `ops/test_yookassa_dryrun.py` — `payment_create` only |
| **QA-PAYMENT-WEBHOOK-001** | P1 | OPEN | Staging payment success webhook simulator |
| **QA-PORTAL-FIXTURES-001** | P1 | **DONE** (repo) | `qa_portal_fixtures.py`; `qa_serve_portal_preview.py`; `ops/test_qa_portal_fixtures.py` |
| **QA-SCENARIO-MATRIX-001** | P1 | **DONE** (repo) | `qa_scenario_matrix.py`; `ops/test_qa_scenario_matrix.py` |
| **QA-E2E-001** | P2 | OPEN | Playwright portal→cabinet smokes |
| **QA-OWNER-PREVIEW-001** | P2 | **DONE** (repo) | `qa_owner_preview.py` journey walkthrough index; FIX-001 transcripts + CTA map |
| **QA-OWNER-PREVIEW-FIX-002** | P2 | **DONE** (repo `8a107ba`) | Bot visual preview HTML; cabinet `#cabinet-actions` CTA dedup for new browser users; raw transcript collapsible; preview artifacts gitignored |
| **PORTAL-LANDING-CTA-DEDUP-001** | P2 | **DONE** (repo) | Browser landing: landing-paths primary, journey steps, account-fold dedup |

### TRACK 5 — Monitoring / CI / ops (BACKLOG-SYNC-002)

Parent gates: **G9** (launch audit), **OBS-001** (§4.9). Repo implementation by default; **no LV/AMS deploy without owner approval.** No Caddy/template/prod mutation in these tasks.

| ID | P | Status | Type | Summary |
|----|---|--------|------|---------|
| **MONITOR-FLAP-001** | P1 | **DEPLOYED LV + soak PARTIAL** | repo + LV (`50a6ac4`) | Anti-flap deployed; legacy spam gone; residual microsoft quorum TG — **MONITOR-FLAP-TUNE-001 repo DONE**, deploy pending |
| **MONITOR-FLAP-TUNE-001** | P1 | **DEPLOYED LV + short soak** | `selfsteal-monitor.py` (`21f5a97`) | CDN quorum log-only; retried warn ≤1/h; soak from **2026-06-13 16:46 UTC** |
| **OPS-ALERT-HYGIENE-001** | P1 | **DEPLOYED LV + soak PASS** | alert policy | Cert digest batched (6 TG/24h soak); 0 per-target cert spam; cooldown OK — `docs/MONITORING.md` |
| **Profile integrity alert** | P1 | NOT_STARTED | ops cron | G9 — scheduled probe + TG (see CLOSEOUT TRACK 5) |
| **Payment callback monitor** | P1 | NOT_STARTED | ops | G9 webhook path |
| **BILL-MON-001** | P2 | NOT_STARTED | ops | Billing job alert |
| **P2-CI-001/002** | P1 | NOT_STARTED | CI | G11 gitleaks / secret scan |
| **LAUNCH-004** | P1 | NOT_STARTED | docs | Support/incident runbooks |

**Prerequisite for node readiness decisions:** **MONITOR-FLAP-001** + **OPS-ALERT-HYGIENE-001** — noisy alerts must be cleaned before monitoring is used as node-quality source of truth (otherwise real degradation vs false positives is indistinguishable).

**Done (infra, do not re-open):** `ru-monitor.py` anti-flap batch (2026-05-27); `monitor.sh` streak 3/2; **Q120** second RU relay (**VPN-AUD-201**); **VPN-AUD-220** NL injectHosts verify (2026-06-03) — live auto-host participation must be re-verified under **VPN-ARCH-001**.

### Completed audits (frozen — do not re-audit)

~~BILL-FIX-001~~ · ~~USER-LIFECYCLE-001~~ · ~~DEVICE-ARCH-001~~ · ~~DEVICE-ENFORCE-001 design~~ · ~~REFERRAL-ARCH-001~~ · ~~SUPPORT-AI-ARCH-001~~ · ~~BILL-001~~ · ~~P1-CAB/DEV/REF deploys~~ · ~~AUDIT-CLOSEOUT-001~~

### TRACK 6 — Support AI / technical triage

| ID | P | Status | Launch blocker | Owner? | Summary |
|----|---|--------|----------------|--------|---------|
| **SUPPORT-AI-ARCH-001** | P1 | **DONE** | None (F&F) | LLM deferred | [`ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md`](ARCH-2026-06-10-AI-SUPPORT-TRIAGE-BOT.md) — internal copilot MVP |
| **SUPPORT-TICKET-001** | P1 | OPEN | Paid partial | No | Ticket schema |
| **SUPPORT-DIAG-001** | P1 | OPEN | Paid partial | No | Read-only diag pack |
| **SUPPORT-CURSOR-HANDOFF-001** | P1 | OPEN | Paid partial | No | Escalation prompts |
| **SUPPORT-REPLY-001** | P1 | OPEN | Paid partial | No | Human-style drafts |
| **SUPPORT-SECURITY-001** | P1 | OPEN | Paid partial | No | Redaction + permissions |
| **SUPPORT-RAG-001** | P2 | OPEN | Open | No | Docs/runbook index |
| **SUPPORT-ADMIN-001** | P2 | OPEN | Open | No | Operator queue |
| **SUPPORT-SMOKE-001** | P2 | OPEN | Auto gate | No | Simulated cases |
| **SUPPORT-AUTO-001** | P2 | OPEN | User bot | **Yes** | After smokes only |

**Rule:** AI support does not replace P1-ADM-001 or LAUNCH-004 runbooks.

---

## 2. Backlog principles

1. **Product truth first, implementation second** — policy v1 and PT-01…PT-12 before code changes.
2. **No false promises** — no live capacity counter, referral bonus, device enforcement, or invite gate in copy until implemented.
3. **No fake capacity counter** — badge «Доступ по приглашению · лимит 30 000» only until stable read-only API.
4. **No Semgrep dependency** — security audits use Trivy, Gitleaks, Bandit, pip-audit, etc.; not Semgrep.
5. **No VPN/prod mutation without explicit approval** — one probe → smoke → commit; see `VPN-INCIDENT-LESSONS`.
6. **One surface per commit** — portal, bot copy, ops, docs — not mixed.
7. **Audit before patch** — especially VPN routing, template PATCH, billing.
8. **Live verification before push** — scoped deploy smoke on LV/AMS for touched surface.

---

## 3. Severity definitions

| Severity | Definition | Examples |
|----------|------------|----------|
| **P0** | Blocks access, security-critical, data/payment loss, active product-promise breach | VPN down/reconnect loop; web ref drop; secrets exposed |
| **P1** | Breaks core model: onboarding, invite/referral, account, support trust, billing clarity | Ghost bot labels; invite policy mismatch; cabinet API gaps |
| **P2** | Important before scale: fraud, admin, UX clarity, observability, REG-001 | Waitlist design; capacity dashboard; fraud signals |
| **P3** | Polish, future scale, nice-to-have | Referral bonus; public capacity API; UX-209 footer ref |
| **P4** | Later ideas / post-scale | Partner automation; calendar subscription; HWID at signup |

---

## 4. Master backlog table

**Legend:** Decision = Accepted / Deferred / N/A · Phase = Policy §12 phase · Status = OPEN / IN_PROGRESS / DONE / DEFERRED / BLOCKED

### 4.1 Product policy & access

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| DEC-IMPL-001 | P1 | Product policy | Policy v1 sign-off | Informal truths scattered | **Accepted** | — | Canonical rules | Workshop 2026-06-09 | `BENDERVPN-PRODUCT-POLICY.md` | Doc published; team uses PT-01…12 | — | No | Done | — | **DONE** |
| PROD-001 | P1 | Invite-only / waitlist | Invite-only not enforced | Copy says invite-only; `/start` allows organic 90d trial | **Accepted:** soft pilot; waitlist after 300 active configs | 4 | Trust + growth control | Full Product Audit | `handlers.py`, portal copy | Organic flagged; no hard gate until Phase 4 | Manual review flag spec | No | No | DEC-IMPL-008 | OPEN |
| PROD-002 | P2 | Capacity / 30k | 30k cap not enforced | Positioning only; no counter or stop | **Accepted:** active configs; grandfather; waitlist at cap | 4 | Overload risk | Audit; UX-207 | `capacity_snapshot.py`, bot | Internal count matches policy §3.4 | ops snapshot | No | Yes at cap | DEC-IMPL-009 | OPEN |
| DEC-IMPL-008 | P2 | Invite-only / waitlist | Waitlist flow | No waitlist UX or data model | **Accepted** Phase 4 | 4 | Controlled growth | Policy §3.3 | portal, bot, DB (later) | No-ref after 300 → waitlist state | UX + admin | Yes | Yes | 300 config metric | DEFERRED |
| DEC-IMPL-009 | P2 | Capacity / 30k | Internal capacity dashboard | No admin view of active configs | **Accepted** | 4 | Threshold decisions | Policy §10.4 | ops, admin | Dashboard shows active configs vs 30k | ops snapshot | No | No | — | OPEN |
| DEC-IMPL-015 | P2 | Invite-only / waitlist | Invite gate enforcement | Hard gate not built | **Deferred** post-300 | 4 | Organic block | Policy §3.3 | `handlers.py` | No-ref blocked after threshold | E2E bot | Yes | Yes | DEC-IMPL-008, 300 configs | DEFERRED |
| DEC-IMPL-020 | P3 | Capacity / 30k | Public capacity API | No stable read-only source | **Deferred** OD-06 | 4 | Transparency | UX-207 audit | portal, setup API | Optional public counter; no fake numbers | API smoke | Yes | Yes | OD-06 | DEFERRED |
| DEC-IMPL-022 | P2 | Capacity / 30k | Hard 30k stop + waitlist drain | No issuance stop at cap | **Accepted** Phase 4 | 5 | Capacity promise | Policy §3.4 | bot, panel | New trials/keys blocked at 30k | admin + bot | Yes | **Yes** | DEC-IMPL-009 | DEFERRED |

### 4.2 Referral & anti-fraud

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| PROD-003 | P0 | Referral | Web `ref_code` dropped | Email fallback loses referral before `issue_web_trial` | **Accepted:** fix end-to-end | 1 | Attribution integrity | P1-REF-001 | `web_referral.py` | Web signup records `referred_by` | smoke PASS | Yes | No | — | **DONE** — [`POSTDEPLOY-2026-06-10-P1-REF-001.md`](POSTDEPLOY-2026-06-10-P1-REF-001.md) |
| DEC-IMPL-002 | P0 | Referral | Web referral attribution fix | Same as PROD-003 | **Accepted** | 1 | Growth data | Policy §5.1 | `portal_web_trial.py`, `database.py` | `ref_code` preserved through chain | smoke PASS | Yes | No | — | **DONE** — P1-REF-001 |
| DEC-IMPL-006 | P1 | Admin/reporting | Referral ledger | No who→whom report | **Accepted** | 1 | Invite scale | Policy §10.1 | admin, DB queries | Export/list inviter→invitee | manual admin | No | No | — | OPEN |
| DEC-IMPL-017 | P3 | Referral | Referral bonus later | No reward implemented | **Deferred** OD-02 | 3 | Economics | Policy §5.3 | bot, billing | Small time credit after active/paid only | fraud review | Yes | **Yes** | OD-02 | DEFERRED |
| AF-001 | P2 | Anti-fraud | Fraud signals baseline | No IP/email cluster detection | **Accepted** Phase 2 | 2 | Abuse before scale | Policy §10.2 | admin, logs | Same-IP/email flags visible | audit | No | No | DEC-IMPL-006 | OPEN |
| AF-002 | P2 | Anti-fraud | Referral attribution completeness metric | Unknown % with `referred_by` | **Accepted** | 2 | Growth quality | Policy §10.2 | admin | Dashboard % attributed | SQL report | No | No | DEC-IMPL-006 | OPEN |
| DEC-IMPL-018 | P3 | Anti-fraud | Email verification | Not at MVP | **Deferred** OD-04 | 3 | Abuse reduction | Policy §4.1 | web trial | Codes only if abuse threshold | — | Yes | Yes | OD-04 | DEFERRED |
| DEC-IMPL-019 | P3 | Partner channel | Partner ref codes + payout ledger | No partner separation | **Deferred** OD-01 | 5 | Partner scale | Policy §10.3 | admin, ref codes | Partner tag ≠ user ref | manual ledger | No | **Yes** | OD-01 | DEFERRED |
| PARTNER-001 | P3 | Partner channel | Partner seller growth audit | CAC, payout, fraud undefined | **Deferred** OD-01 | 5 | Commercial channel | GTM wiki | docs | Audit report before partner launch | AUDIT-014 | No | **Yes** | OD-01 | OPEN |

### 4.3 Registration (REG-001)

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| REG-001 | P2 | Registration | REG-001 design | TG path collects no phone/email | **Accepted:** soft ask; no block at pilot | 2 | Recovery + fraud | Policy §4; Audit | bot onboarding | Design doc: fields, consent, storage | AUDIT-004 | No | No | — | OPEN |
| DEC-IMPL-011 | P2 | Registration | Optional phone/email in bot onboarding | Not implemented | **Accepted** | 2 | Contact capture | Policy §4.1 | `handlers.py`, keyboards | Contact share + optional email; no trial block | py_compile; UX | Yes | No | REG-001 design | DEFERRED |
| DEC-IMPL-012 | P2 | Registration | Phone/email uniqueness if collected | No UNIQUE on phone | **Accepted** | 2 | Dedup | Policy §4.2 | `database.py` | UNIQUE when field populated | migration review | Yes | **Yes** | OD-09 | DEFERRED |
| DEC-IMPL-016 | P2 | Legal/privacy | Privacy/terms update for REG-001 | Minimization doc conflicts | **Deferred** OD-09 | 2 | Legal compliance | `DATA-MINIMIZATION-POLICY.md` | legal/, privacy | Terms match collection | AUDIT-011 | Yes | **Yes** | OD-09 | OPEN |
| OD-05 | P2 | Registration | Mandatory phone before topup | Not decided | **Deferred** | 2 | Payment fraud | Policy OD-05 | bot, billing | Owner decision recorded | — | — | **Yes** | — | BLOCKED |

### 4.4 Device / config / trial

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| P1-DEV-001 | P1 | Device/config | Cabinet read-only config count/list | User cannot see active links count | **Accepted:** Option A MVP; read-only; no revoke | 1 | Trust + support load | [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md) §14.6 | `portal_cabinet.py`, `portal.js`, `ru.json` | API+UI show count, list, primary badge; multi-key anomaly | `tests/test_portal_cabinet_billing.py` | Yes | No | P1-CAB-001 | **DONE** — deploy [`POSTDEPLOY-2026-06-10-P1-DEV-001.md`](POSTDEPLOY-2026-06-10-P1-DEV-001.md) |
| PROD-004 | P1 | Device/config | One device not enforced | Multiple `vpn_keys` allowed | **Accepted:** 1 active config; support for new device | 1 policy / 3 enforce | Fairness + capacity | Audit | panel, `database.py` | Policy documented; no false HWID claim | AUDIT-006 | No | No | — | OPEN |
| DEC-IMPL-014 | P0 | Device/config | Device enforcement design | No deviceLimit/HWID; URL sharing bypass | **Accepted** evaluate | 1 | Link sharing abuse | DEVICE-ENFORCE-001 §14 | panel, Remna | Design in DEVICE-ARCH-001 §14; smoke before PATCH | DEVICE-SMOKE-001 | No | **Yes** | OD-03, G7 | OPEN — superseded by DEVICE-ENFORCE-001 |
| PROD-007 | P1 | Trial policy | Post-trial invite copy alignment | Post-trial text may not match §3 | **Accepted** | 1 | Policy consistency | Audit | `handlers.py`, `ru.json` | Copy matches soft invite-first | forbidden-copy rg | Yes | No | — | OPEN |
| DEC-IMPL-010 | P2 | Trial policy | Trial 90d→30d after 300 active configs | Code still 90d only | **Accepted** | 4 | Economics | Policy §7; `config.py` | `REMNA_TRIAL_DAYS`, bot | New trials 30d; grandfather 90d | env + announce | Yes | **Yes** | 300 configs | DEFERRED |
| OD-03 | P3 | Device/config | Second device paid SKU | Not decided | **Deferred** | 3+ | Revenue | Policy OD-03 | billing, bot | Owner decision | — | — | **Yes** | — | BLOCKED |

### 4.5 Billing / cabinet / bot UX

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| BILL-001 | P1 | Billing/topup | Billing commercial readiness audit | Trial vs wallet; money flow; idempotency; paid pilot gates | **Accepted** | 1 | Payment trust | [`AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md`](AUDIT-2026-06-10-BILLING-PAYMENT-COMMERCIAL-READINESS.md) | bot, webhook, scheduler | Audit doc; BILL-FIX-001 + smokes before automated paid | BILL-SMOKE-001 | No | No | — | **DONE** (audit) — implementation OPEN |
| BILL-FIX-001 | P0 | Billing/topup | Reconcile idempotency `yk:` alignment | Webhook `yk:` vs reconcile `yookassa:` double-credit risk | **Accepted** | 1 | Payment integrity | BILL-001 §7.1 | `payment_idempotency.py`, `payment_queue.py`, reconcile | Canonical key shared; dry-run default; legacy skip | unittest + AMS import | Yes | No | — | **DONE** — [`POSTDEPLOY-2026-06-10-BILL-FIX-001.md`](POSTDEPLOY-2026-06-10-BILL-FIX-001.md) |
| **BILL-TERMS-GUARD-001** | P0 | Billing/legal | Terms gate on all user callbacks | `_ensure_terms_or_prompt` only on `/start` + main menu message; 40+ callbacks skip (trial/topup/pay/wizard) | **Accepted** | 1 | Legal + paid pilot | [`CODERABBIT-AUDIT-TRIAGE-2026-06-14.md`](CODERABBIT-AUDIT-TRIAGE-2026-06-14.md) CB-1 | `handlers.py` | All trial/pay/wizard callbacks enforce terms; pytest | handler tests | Yes | **Yes** | — | **DONE** — deployed AMS 2026-06-15 ([`POSTDEPLOY-2026-06-15-BILLING-GUARDS.md`](POSTDEPLOY-2026-06-15-BILLING-GUARDS.md)) |
| **BILL-TERMS-GUARD-002** | P0 | Billing/legal | Terms gate residual callback paths | `toggle_autorenew` bind path; wizard sub-steps; `enter_promo_start` reachable via stale keyboards | **Accepted** | 1 | Legal + paid pilot | Review cf7ca8a..0110ce8 | `handlers.py` | Autopay-bind + wizard/promo entry guarded; pytest | `test_bill_terms_guard.py` | Yes | **Yes** | BILL-TERMS-GUARD-001 | **DONE** — deployed AMS 2026-06-15 |
| **LIVE-TERMS-UX-SMOKE-001** | P0 | Billing/legal | Live Telegram terms UX + offline harness | Owner taps not run 2026-06-16; offline cases 1–6 PASS | **Accepted** | 1 | Paid pilot gate | POSTDEPLOY-2026-06-15 | `ops/smoke_terms_guard_ux_offline.py`, `ops/smoke_live_terms_guard_ams.py` | Owner live matrix PASS; offline PASS | harness + owner | Yes | No | BILL-TERMS-GUARD-* | **PARTIAL** — offline PASS; live owner taps **OPEN** |
| **TRIAL-GRANT-ATOMIC-001** | P1 | Billing/trial | Atomic trial grant | `set_trial_used` before `provision_key`; crash blocks retry | **Accepted** | 1 | Trial abuse UX | CodeRabbit triage CB-2 | `handlers.py` | Flag after key row or idempotent reconcile | unit test | Yes | No | — | **DONE** — deployed AMS 2026-06-15 (marker smoke; no live trial soak) |
| **BILL-AUTOPAY-LIVE-GUARD-001** | P1 | Billing/autopay | Autopay batch live guard | `run_yookassa_autopay_batch` lacks internal guard; scheduler gated | **Accepted** partial | 1 | Defense-in-depth | CodeRabbit triage CB-3 | `yookassa_autopay_scheduler.py` | Early return if not `BOT_PAYMENTS_LIVE` | unit test | Yes | No | PAY-AUTO-001 | **DONE** — deployed AMS 2026-06-15 |
| **BILL-BALANCE-KOPEKS-001** | P1 | Billing/topup | Kopeks/Decimal day rate | `DAILY_RATE=6.67` float → 200 ₽ = 29 days | **Accepted** | 1 | Copy truth | CodeRabbit triage CB-4 | `config.py`, billing | Integer kopeks; preset labels match | BILL-UT-001 | Yes | No | — | **OPEN** |
| **BILL-UT-001** | P0 | Billing/tests | Offline daily debit tests | No `test_balance_billing.py` | **Accepted** | 1 | Automated paid pilot | BILL-001; CodeRabbit triage | `tests/` | `charge_daily_balance_if_due` edge cases | pytest CI | No | No | — | **OPEN** |
| **BILL-UT-002** | P0 | Billing/tests | Offline webhook/idempotency tests | Payment path gaps in CI | **Accepted** | 1 | Automated paid pilot | BILL-001; CodeRabbit triage | `tests/`, `database.py` | Topup idempotency + webhook claim | pytest CI | No | No | BILL-WEBHOOK-CLAIM-TOCTOU-001 | **OPEN** |
| **BILL-WEBHOOK-CLAIM-TOCTOU-001** | P1 | Billing/webhook | Harden webhook claim | `claim_webhook_delivery` SELECT-then-INSERT race | **Accepted** | 1 | Double-credit risk | CodeRabbit triage | `database.py` | INSERT OR IGNORE / txn; test concurrent claim | BILL-UT-002 | Yes | No | — | **DONE** — deployed AMS 2026-06-15 (offline claim smoke) |
| **BILL-LEGACY-PAYMENT-FLOW-GATE-001** | P2 | Billing/legacy | Gate legacy plan purchase | `buy_*_month` parallel to wallet model | **Accepted** | 2 | UX confusion | BILL-001 §3; CodeRabbit triage | `handlers.py`, `config.py` | Remove UI entry or gate behind flag | copy review | Yes | **Yes** | OD-10 | **OPEN** |
| **BOT-QR-MISSING-KEY-UX-001** | P2 | Bot UX | QR silent failure UX | `show_qr_handler` bare return on missing inbound/URI | **Accepted** | 1 | Support load | CodeRabbit triage | `handlers.py` | User-visible error on all paths | manual smoke | Yes | No | — | **OPEN** |
| **SUBSCRIPTION-RESOLVE-TZ-001** | P2 | Bot/cabinet | Timezone-safe expiry check | `datetime.now()` naive in `subscription_unavailable` | **Accepted** | 1 | Edge expiry bugs | CodeRabbit triage | `subscription_resolve.py` | UTC-aware compare | unit test | Yes | No | — | **OPEN** |
| **G4-TG-BIND-RETEST-001** | P0 | Acquisition | Live TG bind proof | `funnel_bot_start bind:*` = 0; handoff fix repo-only | **Accepted** | 1 | Referral growth | [`G4-TG-BIND-CLIENT-JOURNEY-AUDIT.md`](G4-TG-BIND-CLIENT-JOURNEY-AUDIT.md) | owner + AMS | bind:* ≥ 1; migration completes | smoke_p1_ref_tg_bind_ams | No | **Yes** | handoff deploy | **OPEN** |
| USER-LIFECYCLE-001 | P1 | Product/lifecycle | End-to-end user scenario audit | Launch gates need scenario matrix | **Accepted** | 1 | Launch readiness | Commercial audit + policy | docs, bot, portal | Scenarios A–H; REG/PAY/WEB gates; go/no-go | — | No | No | — | **DONE** — [`AUDIT-2026-06-10-USER-LIFECYCLE-SCENARIOS.md`](AUDIT-2026-06-10-USER-LIFECYCLE-SCENARIOS.md) |
| DEVICE-ARCH-001 | P0 | Device/config | Multi-device architecture + billing coefficient | Vague support-only insufficient | **Accepted** evaluate | 1 | Infra cost honesty | USER-LIFECYCLE-001 §G | docs, schema, billing, Remna | MODEL A recommended; MODEL B NOT READY; gates DEVICE-* | DEVICE-SMOKE-001 | No | **Yes** | OD-03, BILL-SMOKE | **DONE** (arch) — owner approve MODEL A |
| DEVICE-ENFORCE-001 | P0 | Device/config | Detect reuse of active config on 2nd device | URL sharing bypasses billing × N | **Accepted** evaluate | 1 | Abuse + infra honesty | DEVICE-ARCH-001 §14 | Remna HWID, panel, admin | L3/L4 for paid/open; staged consequences | DEVICE-SMOKE-001 | No | **Yes** | G7, OD-03 | OPEN — paid/open blocker |
| REFERRAL-ARCH-001 | P0 | Referral/growth | Referral entrypoint + portal role + analytics | Bot-only share contradicts two-path acquisition | **Accepted** evaluate | 1 | Growth clarity | USER-LIFECYCLE-001 §H | docs, portal, bot, admin | OPTION 3 hybrid; G4 bind BLOCKED; gates REF-* | REF-BIND-001 | No | **Yes** | G4, OD-02 | **DONE** (arch) — owner approve OPTION 3 |
| SUPPORT-AI-ARCH-001 | P1 | Support/AI | AI support triage + Cursor handoff | Support scale; diagnostic quality | **Accepted** evaluate | 1 | Support efficiency | AUDIT-CLOSEOUT TRACK 6 | docs, ops read-only | Option D+B MVP; L0–L3; no mutation | SUPPORT-DIAG-001 | No | **Yes** LLM | P1-ADM-001 | **DONE** (arch) — internal copilot first |
| DEC-IMPL-013 | P1 | Cabinet/account | Cabinet API `billing_profile` / trial-wallet | `portal_cabinet.py` missing fields `portal.js` expects | **Accepted** | 1 | Cabinet truth | Full Product Audit + [`AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md`](AUDIT-2026-06-10-TELEGRAM-ACCESS-SCENARIOS.md) | `portal_cabinet.py`, `portal.js` | API returns trial/wallet/legacy/expired + billing_note | py_compile; `tests/test_portal_cabinet_billing.py` | Yes | No | — | **DONE** — deploy [`POSTDEPLOY-2026-06-10-P1-CAB-001.md`](POSTDEPLOY-2026-06-10-P1-CAB-001.md) |
| PROD-005 | P1 | Bot UX/copy | Ghost button labels | «Начать бесплатно», «Мой VPN» in errors | **Accepted** | 1 | Onboarding confusion | Audit | `subscription_resolve.py`, `portal_cabinet.py` | Labels match live menu | py_compile | Yes | No | — | OPEN |
| DEC-IMPL-003 | P1 | Bot UX/copy | Bot/API label alignment | Same as PROD-005 | **Accepted** | 1 | Support load | Policy Phase 1 | bot handlers | All user strings match keyboards | grep labels | Yes | No | — | OPEN |
| PROD-006 | P1 | Bot UX/copy | NL/Latvia in user help | `msg_help_connect` exposes infra names | **Accepted** | 1 | Policy breach PT-11 | Audit | `user_messages.py` | No NL/LV/9443 in user copy | forbidden-copy rg | Yes | No | — | OPEN |
| DEC-IMPL-004 | P1 | Bot UX/copy | Remove infra names from help | Same as PROD-006 | **Accepted** | 1 | Trust | Policy Phase 1 | bot copy | BenderVPN Auto only | rg | Yes | No | — | OPEN |
| DEC-IMPL-005 | P1 | Bot UX/copy | Post-trial invite copy | Same as PROD-007 | **Accepted** | 1 | Growth messaging | Policy §3 | `handlers.py` | Matches soft invite-first | copy review | Yes | No | — | OPEN |
| BOT-001 | P1 | Bot UX/copy | Live bot flow audit | Real TG flow not re-verified post-copy fixes | N/A | 1 | End-to-end truth | Audit need | bot, Mini App | Audit report with safe test user | AUDIT-008 | No | No | — | OPEN |
| OD-10 | P4 | Billing/topup | Wallet-only vs calendar subscription | Not decided | **Deferred** | Future | Billing model | Policy OD-10 | billing | Owner decision | — | — | **Yes** | — | BLOCKED |

### 4.6 Portal UX (quality plan — mostly done)

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| SEM-001 / P1-1 | P1 | Portal UX | Browser cabinet false balance promise | Grace hides data | N/A | — | Trust | Quality plan | `ru.json`, `portal.js` | Browser subline honest | live smoke | Yes | No | — | **DONE** |
| SEM-002 / P1-2 | P1 | Portal UX | Legal 90d vs 1d | Ambiguous terms | N/A | — | Legal clarity | Quality plan | `terms.html` | TG 90d vs email 1d stated | read terms | Yes | No | — | **DONE** |
| SEM-003–008 | P2 | Portal UX | Landing length, tg-blocked CTA, FAQ /id, etc. | Conversion polish | N/A | — | Conversion | Quality plan | portal | Batches 2–3 acceptance | semantic audit | Yes | No | — | **DONE** |
| SEM-009–010, UX-211–212 | P3 | Portal UX | English trial, events-card, guide nav, a11y | Polish | N/A | — | Polish | Quality plan | portal | Batch 3 done | audit | Yes | No | — | **DONE** |
| UX-209 | P3 | Portal UX | Referral on support/footer TG links | Minor IA | N/A | — | Discovery | Quality plan | `ru.json` | Ref preserved in footer links | — | Yes | No | — | OPEN |

### 4.7 Support / admin / legal / ops

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| DEC-IMPL-007 | P1 | Admin/reporting | Admin user lookup | No TG/email/customer ID lookup | **Accepted** | 1 | Support + ops | Policy §10.1 | admin | Single-pane user status | manual test | No | No | — | OPEN |
| ADMIN-001 | P1 | Admin/reporting | Admin/reporting audit | Capabilities unknown vs policy | N/A | 1 | Ops readiness | Policy §10 | admin, bot | Gap report | AUDIT-009 | No | No | — | OPEN |
| DEC-IMPL-021 | P2 | Support/recovery | User-facing support email | TG-only today | **Accepted** before partner scale | 5 | Trust at scale | Policy §9.1 | portal, bot | Email published + SLA | — | Yes | **Yes** | OD-07 | DEFERRED |
| OD-07 | P2 | Support/recovery | Support email address + SLA | Not decided | **Deferred** | 5 | Operations | Policy OD-07 | — | hello@ vs support@ | — | — | **Yes** | — | BLOCKED |
| OD-08 | P2 | Support/recovery | Emergency comms channel | Required before 10k | **Deferred** | 4 | Incident comms | Policy §9.4 | status, email | Channel defined | AUDIT-012 | Yes | **Yes** | — | OPEN |
| RUNBOOK-001 | P2 | Documentation/runbooks | Support/incident runbooks | Support intake not formalized | **Accepted** | 1 | Ops consistency | Policy §9.2 | `docs/` | Runbook: device, /id, screenshot | doc review | No | No | — | OPEN |
| LEGAL-001 | P2 | Legal/privacy | Legal/privacy final review | Draft terms/privacy | N/A | 2 | Compliance | Quality plan §10 | legal/ | Review vs REG-001 | AUDIT-011 | Yes | **Yes** | OD-09 | OPEN |

### 4.8 VPN reliability & architecture

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| VPN-REL-001 | P0 | VPN reliability | Unstable reconnect loop diagnostic | Users report disconnect/reconnect | N/A | **Now** | Core product value | `AUDIT-2026-06-09-VPN-RELIABILITY.md` | ops probes, panel, Happ | RC-1 relay2-only SPOF; RC-2 random balancer | AUDIT-001 done | No | **Yes** for patch | Owner picks profile target | **AUDIT DONE** |
| VPN-ARCH-001 | P1 | VPN architecture | Full VPN architecture audit + NL revalidation AC | NL not active; pre-qualified for A2/A4 smoke after soak (PROOF-001 + QUALITY-PROOF-001) | N/A | **Now** | Growth blocked until ≥2 verified delivery-path nodes | **QUALITY-PROOF-001 DONE**; soak + controlled smoke pending | ops/, panel | A2/A4 smoke gates; owner approval; ≥2 path surfaces post-inclusion | `nl_reachability_probe_ru.py`; gate §1 | No | **Yes** global | VPN-REL-001; MONITOR-FLAP-001 | **AWAITING APPROVAL** |
| VPN-NODE-RUNBOOK-001 | P1 | VPN architecture / ops | Fast node + relay bring-up template | `deploy-node.sh` + partial docs exist; unified runbook **DONE** | N/A | **Now** | Fast scale on user influx | [`VPN-NODE-RUNBOOK.md`](VPN-NODE-RUNBOOK.md), [`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md) | docs **DONE**; automation OPEN | Repeatable checklist + canary/drain/rollback | owner review | No | **Yes** | VPN-ARCH-001; MONITOR-FLAP-001 | **DOCS DONE / IMPL OPEN** |
| VPN-ARCH-30K-CAPACITY-PLAN-001 | P0 | VPN architecture | 30k capacity target architecture | Single-path relay2 lab ≠ launch architecture | N/A | **Now** | 300/30k NO-GO until ≥2 delivery paths + registry | [`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md) | doc **DONE** | Backend-controlled multi-node delivery | — | No | **Yes** | delivery_path_nodes | **DOCS DONE / IMPL OPEN** |
| VPN-NODE-REGISTRY-001 | P1 | VPN architecture / ops | Node registry SoT | No inventory source for assignment | N/A | **Now** | Scale + support visibility | [`ops/config/vpn_node_registry.yaml`](../ops/config/vpn_node_registry.yaml), [`ops/validate_vpn_node_registry.py`](../ops/validate_vpn_node_registry.py) | registry + validator **DONE** | `validate_vpn_node_registry.py`; pytest | registry smoke | No | No | SUB-GEN-SELECTOR | **DONE** (v1 repo SoT; no live sub driver) |
| SUB-GEN-SELECTOR-STRATEGY-001 | P0 | VPN architecture | Cohort-based assignment dry-run | Static 6-outbound JSON for all users | N/A | **Now** | Honest multi-node delivery | [`ops/vpn_node_selector.py`](../ops/vpn_node_selector.py) | dry-run **DONE** | pytest + CLI cohort gates | transport_mux_audit | No | **Yes** (integration) | VPN-NODE-REGISTRY | **DONE** (dry-run; no live sub driver) |
| SUB-GEN-SELECTOR-INTEGRATION-001 | P0 | VPN architecture | Wire selector into subscription generator | Dry-run not yet applied to live subs | N/A | **Next** | Production assignment | selector module | OPEN | Owner review + gated integration | post-inclusion audit | Yes | **Yes** | SUB-GEN-SELECTOR-STRATEGY-001 | **OPEN** |
| ROUTING-PROFILE-RU-DIRECT-001 | P1 | VPN client routing | Curated RU direct routing pack | SafeVPN reference only; geoip:ru regression risk | N/A | **Now** | Happ stability | [`VPN-ROUTING-PROFILE-STRATEGY.md`](VPN-ROUTING-PROFILE-STRATEGY.md) | strategy **DONE** | Pack + directip guard tests | happ_routing_directip_guard | Yes | **Yes** (bittorrent OD) | fixed happRouting | **DOCS DONE / IMPL OPEN** |
| NODE-SMOKE-MATRIX-001 | P1 | VPN ops | Unified per-node smoke matrix | Scattered probes | N/A | **Now** | Node quality gate | [`VPN-NODE-ACCEPTANCE-CHECKLIST.md`](VPN-NODE-ACCEPTANCE-CHECKLIST.md) | checklist **DONE** | Runner script/CI | vpn_verify_gate | No | No | VPN-NODE-RUNBOOK | **DOCS DONE / IMPL OPEN** |
| ROLLOUT-CANARY-DRAIN-001 | P1 | VPN ops | Canary / drain / rollback automation | Manual PATCH risk | N/A | **Now** | Safe node intro | runbook §7–8 | process **DONE** | Weight + cohort automation | postmortem | Yes | **Yes** | SUB-GEN-SELECTOR | **DOCS DONE / IMPL OPEN** |
| MONITOR-CAPACITY-001 | P1 | Monitoring | Capacity metrics + alerts | No dashboard for delivery_path_nodes / load | N/A | **Now** | 1k/10k/30k gates | capacity plan §6 | OPEN | Metrics + TG/dashboard | capacity_snapshot | No | No | OPS-ALERT-HYGIENE | **OPEN** |
| VPN-STAB-005 | P2 | VPN reliability | xhttp Happ batch risk (historical) | xhttp causes «0 servers» in Happ | Partially done | — | Happ UX | `AUDIT-2026-05-VPN-STABILITY-RESOLUTION` | sub-page, template | batch_risk=LOW on Happ UA | diagnose_happ_import | Yes | No | — | **DONE** |
| VPN-INC-001 | P1 | VPN reliability | Incident guardrails enforcement | Repeat PATCH without probe caused gen 13→20 outages | N/A | ongoing | Prod stability | `VPN-INCIDENT-LESSONS` | ops patches | One PATCH → probe → smoke | verify gate | No | **Yes** | — | OPEN |
| **CLIENT-STABILITY-001** | P0 | VPN reliability | Windows Happ TUN recovery | Track D DirectIp **fixed**; relay2 report(7) **SOFT PASS** + report(8) repeat **PASS**; relay #1 strong suspect; sleep/wake **OPEN** | N/A | **Now** | Desktop launch gate | [relay2 lab](CLIENT-STABILITY-HAPP-RELAY2-LAB.md) · [report(8)](CLIENT-STABILITY-HAPP-RELAY2-LAB.md#report8--repeat-active-soak-evidence-2026-06-15) | docs, analyzer, guard | PROD-SELECTOR-CONTROLLED eligible (owner approval) | CLIENT-SMOKE-001..003 | No | **Yes** | sleep/wake | **OPEN** |
| **CLIENT-STABILITY-HAPP-RELAY2-REPEAT-SOAK-001** | P0 | VPN reliability | Relay2 lab repeat active soak | report(8) PASS — ~59 min post-wake; no i/o/dial storm; owner no incidents | N/A | **Now** | Gates controlled prod selector planning | [RELAY2-LAB §REPEAT-SOAK](CLIENT-STABILITY-HAPP-RELAY2-LAB.md#client-stability-happ-relay2-repeat-soak-001--repeat-active-soak-decision-gate) | owner laptop | PASS recorded | analyze_happ_report_tun report(8) | No | **Yes** | PROD-SELECTOR-CONTROLLED-001 | **DONE** — PASS |
| **CLIENT-STABILITY-HAPP-RELAY2-PROD-SELECTOR-CONTROLLED-001** | P0 | VPN reliability | Controlled prod relay #1 selector reduction | Repeat soak PASS; **not auto-approved** | N/A | **After owner approval** | Prod mitigation path | RELAY2-LAB §PROD-SELECTOR | ops/panel (owner-approved) | Snapshot + dry-run + smoke + rollback | happ guard; probe | **Yes** | **Yes** | owner approval | **ELIGIBLE — NOT STARTED** |
| **CLIENT-STABILITY-HAPP-LONG-SESSION-SOAK-001** | P0 | VPN reliability | Happ Windows TUN long-session soak | Superseded for relay2 path by REPEAT-SOAK-001; normal Bender row still pending | N/A | **Now** | Desktop launch gate | recovery doc §9 | owner laptop | Normal Bender 30–60 min still open | analyze_happ_report_tun on FAIL | No | **Yes** | — | **PENDING** — normal Bender |
| **CLIENT-STABILITY-DESKTOP-FALLBACK-001** | P0 | VPN reliability | Windows desktop fallback path | Happ TUN long-session risk; Proxy fail; need v2rayN/Karing safety | N/A | **Now** | Launch/support safety | [CLIENT-STABILITY-DESKTOP-FALLBACK.md](CLIENT-STABILITY-DESKTOP-FALLBACK.md) | docs, `probe_fallback_client_sub.py` | v2rayN smoke PASS; Karing exploratory | probe script | No | **Yes** | LONG-SESSION-SOAK optional | **PROTOCOL READY** |
| **CLIENT-STABILITY-MOBILE-SMOKE-001** | P0 | VPN reliability | Mobile stability + speed launch smoke | Happ primary iOS/Android; speed/lock/LTE handoff unproven | N/A | **Now** | **Blocks acquisition/referral growth** | [CLIENT-STABILITY-MOBILE-SMOKE.md](CLIENT-STABILITY-MOBILE-SMOKE.md) · [logs 2026-06-16](CLIENT-STABILITY-MOBILE-LOGS-2026-06-16.md) | docs, `generate_mobile_smoke_template.py`, `analyze_mobile_smoke_logs.py` | Happ PASS/SOFT on Wi‑Fi + LTE | `probe_fallback_client_sub.py` | No | **Yes** | SLEEPWAKE-001 | **PENDING** — owner run |
| **CLIENT-STABILITY-MOBILE-LOGS-001** | P0 | VPN reliability | Mobile owner log analysis | Owner instability report 2026-06-16 | N/A | **Now** | Evidence for mobile gate | [CLIENT-STABILITY-MOBILE-LOGS-2026-06-16.md](CLIENT-STABILITY-MOBILE-LOGS-2026-06-16.md) | `analyze_mobile_smoke_logs.py` | Redacted summary + classification | pytest mobile logs | No | **Yes** | — | **DONE** |
| **CLIENT-STABILITY-MOBILE-SLEEPWAKE-001** | P0 | VPN reliability | Mobile sleep/wake reconnect test | Owner report; logs NOT PROVEN | N/A | **Now** | Mobile launch gate | MOBILE-LOGS-2026-06-16 §7 | owner phone | Lock 2 min + LTE handoff; timed reconnect | analyze with `--owner-event` | No | **Yes** | MOBILE-SMOKE-001 | **OPEN** |
| **CLIENT-SUBSCRIPTION-IMPORT-HAPP-001** | P1 | VPN client | Happ provider/geofile import noise | Read-only review done; staging not started | N/A | **Staging gated** | Import UX vs reconnect | [IMPORT-READONLY](CLIENT-SUBSCRIPTION-IMPORT-HAPP-READONLY.md) | docs + `diagnose_happ_import.py` | Staging A/B owner gate | fullday analyzer | No | **Yes** | — | **DONE (read-only)** — staging **OPEN** |
| **CLIENT-STABILITY-MOBILE-PROFILE-COMPARISON-001** | P2 | VPN reliability | Multi-proxy vs single-path mobile compare | 6-way pool spread in access log | N/A | **If instability persists** | Path quality hypothesis | MOBILE-LOGS-2026-06-16 §5 track D | owner phone | Bender Auto vs controlled profile | log analyzer routes | No | **Yes** | SLEEPWAKE-001 | **OPEN** |
| **CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-001** | P0 | VPN reliability | Full-day passive mobile log correlation | Owner constant-use vs 21 min access export | N/A | **Now** | Evidence quality | [FULLDAY-DEEPDIVE-2026-06-16](CLIENT-STABILITY-MOBILE-FULLDAY-DEEPDIVE-2026-06-16.md) | `mobile_log_fullday.py`, `analyze_mobile_logs.py` | Timeline + cross-correlation | pytest fullday | No | **Yes** | — | **DONE** |
| **CLIENT-MOBILE-OBSERVABILITY-001** | P0 | VPN reliability | Full-day mobile access_log export/capture | Checklist + validate tooling done; owner export pending | N/A | **Now** | Blocks passive root-cause | [OBSERVABILITY-PLAN](CLIENT-MOBILE-OBSERVABILITY-PLAN.md) | `analyze_mobile_logs.py --validate-coverage` | Owner full-day export | pytest fullday | No | **Yes** | FULLDAY-DEEPDIVE-001 | **DONE** (tooling) — **owner export PENDING** |
| **CLIENT-MOBILE-DAILY-CAPTURE-001** | P0 | VPN reliability | Owner daily capture workflow for unstable days | Short runbook + notes template | N/A | **Now** | Next unstable day diagnosable | [OBSERVABILITY-PLAN §9](CLIENT-MOBILE-OBSERVABILITY-PLAN.md) | `generate_mobile_capture_template.py` | Owner uses §9 on next bad day | pytest capture template | No | **Yes** | OBSERVABILITY-001 | **DONE** |
| **CLIENT-SUBSCRIPTION-IMPORT-HAPP-STAGING-001** | P1 | VPN client | Staging Happ import A/B (xhttp batch) | Read-only review done in IMPORT-READONLY | N/A | **Owner gate** | Import path evidence | [IMPORT-READONLY](CLIENT-SUBSCRIPTION-IMPORT-HAPP-READONLY.md) | `diagnose_happ_import.py` | Redacted `--json` on staging | owner token gate | No | **Yes** | IMPORT-HAPP-001 | **OPEN** |
| **CLIENT-SMOKE-001** | P0 | VPN reliability | Happ Windows TUN sleep/resume repro | AFTER-BROKEN snapshots missing | N/A | **Now** | G1 / CLIENT-STABILITY Track A | INCIDENT-003 | owner laptop | Sleep 10–30 min; pre-reboot bundle; reboot Y/N | runbook §6 | No | **Yes** | — | OPEN |
| **CLIENT-SMOKE-002** | P0 | VPN reliability | Bender Proxy mode connectivity | Proxy fallback unverified; owner reports Bender Proxy fail | N/A | **Now** | G1 / CLIENT-STABILITY Track B | CLIENT-STABILITY-001 | owner laptop | Bender Proxy vs other VPN Proxy on same machine | runbook §6 | No | **Yes** | — | OPEN |
| **CLIENT-SMOKE-003** | P1 | VPN reliability | Alternative client fallback (Karing) | No validated Windows fallback if TUN/Proxy fragile | N/A | **Now** | Paid/open if Happ-only path | [CLIENT-STABILITY-DESKTOP-FALLBACK.md](CLIENT-STABILITY-DESKTOP-FALLBACK.md) | owner laptop | v2rayN first; Karing exploratory; 20–30 min smoke | `probe_fallback_client_sub.py` | No | **Yes** | CLIENT-SMOKE-001/002 | **PROTOCOL READY** |
| VPN-AUD-210+ | P2 | VPN architecture | Remaining VPN full audit items | geosite, DNS leak, remarks, etc. | Per infra backlog | infra | Routing quality | `BACKLOG-VPN-FULL-AUDIT-2026-05-28` | ops, panel | Per-item verify gate | probe scripts | Yes | **Yes** | VPN-REL-001 | OPEN |

### 4.9 Security / observability / performance / release

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Files/modules | Acceptance | Checks | Deploy? | Owner? | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|---------------|------------|--------|---------|--------|------------|--------|
| SEC-001 | P1 | Security | Full security audit | Last audit May 2025; surface grew | N/A | 2 | Breach prevention | `AUDIT-2026-05-SECURITY*.md` | bot, portal, ops | Report: secrets, auth, rate limits | AUDIT-010 | No | No | — | OPEN |
| OBS-001 | P2 | Monitoring/observability | Monitoring audit | Status page exists; user-impact detection weak; selfsteal TG noise | N/A | 4 | Incident response | `MONITORING.md`; BACKLOG-SYNC-001 | Gap report + child tasks | AUDIT-012 | No | No | — | OPEN |
| MONITOR-FLAP-001 | P1 | Monitoring/observability | Selfsteal monitor anti-flap | **DEPLOYED LV** (`50a6ac4`); soak **PARTIAL** 2026-06-13 | N/A | 4 | Alert fatigue | LV logs 2026-06-11..12 | **MONITOR-FLAP-TUNE-001 deploy + re-soak** | log review | No | No | OBS-001 | **SOAK PARTIAL** |
| MONITOR-FLAP-TUNE-001 | P1 | Monitoring/observability | CDN/github noise tune | **DEPLOYED LV** `21f5a97` 2026-06-13; short soak in progress | N/A | 4 | Residual TG/log noise | LV logs post-16:46 UTC | 30m/6h review | log review | No | No | MONITOR-FLAP-001 | **SOAK OPEN** |
| OPS-ALERT-HYGIENE-001 | P1 | Monitoring/observability | Alert hygiene policy | **DEPLOYED LV + soak PASS** — cert digest batched; 0 old cert spam | N/A | 4 | Ops trust at scale | `ops/test_ru_monitor_cert_digest.py` | Deploy LV + soak | log review | No | No | OBS-001, MONITOR-FLAP-001 | **SOAK PASS** |
| PERF-001 | P3 | Metrics/analytics | Performance/load audit | Portal/bot/web-trial load unknown | N/A | 4 | Scale readiness | — | portal, bot | Approved profile only | AUDIT-013 | No | **Yes** | — | OPEN |
| OPS-001 | P2 | Ops/deploy/release | Deploy/release safety audit | Dirty tree, stale smokes, rollback | N/A | 2 | Safe releases | `RUNBOOK-AMS-SAFE-DEPLOY` | deploy scripts | Audit report | AUDIT-015 | No | No | — | OPEN |

### 4.10 Open decisions (tracking only — not implementation)

| ID | Sev | Area | Title | Problem | Decision | Phase | Impact | Evidence | Blocked by | Status |
|----|-----|------|-------|---------|----------|-------|--------|----------|------------|--------|
| OD-01 | P3 | Partner channel | Partner program structure | Channel vs user referral | **Deferred** | 5 | GTM | Policy §11 | Owner | BLOCKED |
| OD-02 | P3 | Referral | Referral bonus economics | +1 month to **referrer** after invitee paid conversion | **Deferred** | 3 | Cost | Policy §5.3; ACQUISITION-JOURNEY-001 | REF-BONUS-001 | BLOCKED |
| OD-03 | P3 | Device/config | Second device paid SKU | Pricing, self-serve | **Deferred** | 3+ | Revenue | Policy §11 | Owner | BLOCKED |
| OD-04 | P3 | Anti-fraud | Email verification timing | Signup vs topup | **Deferred** | 3 | Abuse | Policy §11 | Owner | BLOCKED |
| OD-05 | P2 | Registration | Mandatory phone before topup | Hard vs soft | **Deferred** | 2 | Fraud | Policy §11 | Owner | BLOCKED |
| OD-06 | P3 | Capacity / 30k | Public capacity API shape | Endpoint design | **Deferred** | 4 | UX | Policy §11 | Owner | BLOCKED |
| OD-07 | P2 | Support/recovery | Support email + SLA | Address, response time | **Deferred** | 5 | Trust | Policy §11 | Owner | BLOCKED |
| OD-08 | P2 | Support/recovery | Emergency comms channel | Status vs email list | **Deferred** | 4 | Incidents | Policy §11 | Owner | BLOCKED |
| OD-09 | P2 | Legal/privacy | Privacy revision for REG-001 | Minimization conflict | **Deferred** | 2 | Legal | Policy §11 | Owner | BLOCKED |
| OD-10 | P4 | Billing/topup | Wallet vs calendar subscription | Product model | **Deferred** | Future | Billing | Policy §11 | Owner | BLOCKED |

### 4.11 Severity summary (open items only)

| Severity | Count (approx.) | Examples |
|----------|-----------------|----------|
| **P0** | 8+ | BILL-TERMS-GUARD-001, G4-TG-BIND-RETEST-001, BILL-UT-001/002, VPN-REL-001, CLIENT-STABILITY-* |
| **P1** | 22+ | TRIAL-GRANT, BILL-AUTOPAY/BALANCE/WEBHOOK, PROD-001,004–007; VPN-ARCH-001; … |
| **P2** | 22 | REG-001; DEC-IMPL-008–012,016,021; PROD-002; AF-*; LEGAL-001; RUNBOOK-001; OD-08; OPS-001; OBS-001; VPN-AUD+ |
| **P3** | 8 | DEC-IMPL-017–020; UX-209; PARTNER-001; PERF-001; OD-01–04,06 |
| **P4** | 1 | OD-10 |
| **DONE** | 12+ | Policy v1, portal batches, SEM/UX items, VPN-STAB-005 |
| **BLOCKED** | 10 | OD-01 … OD-10 (owner decisions) |

---

## 5. Current implementation sequence

### Phase 1 — Product logic alignment (before broader invite rollout)

**Do:** web ref attribution · bot/Mini App labels · remove NL/LV user copy · post-trial invite copy · referral ledger · admin user lookup · cabinet API trial/wallet fields · support runbook draft

**Do not:** schema-heavy REG-001 · hard invite gate · device HWID · capacity enforcement · referral bonus · VPN routing PATCH

**Unlock:** AUDIT-003 product policy implementation audit → then implement

### Phase 2 — Registration / REG-001 / before 300 active configs

**Do:** optional phone/email bot onboarding · legal/privacy update (OD-09) · trial switch policy prep · contact capture metrics · fraud signals · AUDIT-004/005/006

### Phase 3 — Referral / anti-fraud / partner readiness

**Do:** attribution completeness · fraud scoring · device enforcement design · referral bonus if OD-02 approved · email verification if OD-04 approved · partner tagging if OD-01 approved

### Phase 4 — Capacity and 10k readiness

**Do:** internal active config dashboard · waitlist · trial 90→30 switch · invite gate after 300 · emergency comms (OD-08) · observability (AUDIT-012) · support email prep

### Phase 5 — 30k closure & partner scale

**Do:** hard config/trial stop · waitlist drain · capacity expansion decision · user-facing support email · partner ledger · CAC reporting

---

## 6. Do-not-touch list

Without **explicit owner approval**, do not change:

| Category | Items |
|----------|-------|
| **Billing** | Billing logic, daily charge rules, trial skip, balance math |
| **Payments** | YooKassa integration, webhook handlers, real payment tests |
| **VPN core** | Remna provisioning, subscription template PATCH, routing/transport, geo rules |
| **Data** | Database schema migrations, production data mutation |
| **Infra** | Production Caddy, `deploy-node.sh`, emergency/patch/restore scripts |
| **Mass ops** | Mass subscription refresh, broadcast messages to all users |
| **Growth gates** | Referral gate logic (until Phase 4 policy implementation approved) |
| **Repo hygiene** | `git stash` apply, unrelated dirty files in commits, QA artifact commits |

**VPN PATCH rule (from incident lessons):** one change → `probe_subscription.py` → `diagnose_happ_import.py` → smoke → then next change.

---

## 7. Commit / release discipline

| Rule | Detail |
|------|--------|
| One surface per commit | portal · bot copy · ops · docs — not mixed |
| Checks by surface | `json.tool` / `node --check` / `py_compile` / forbidden-copy rg |
| Deploy scoped surface only | portal LV script; bot AMS; legal scp if needed |
| Live smoke before push | touched URLs on `k9x2m1.conntest.xyz:8443` or bot test user |
| No unrelated dirty files | QA screenshots, `.playwright-review/`, skills — exclude unless requested |
| Docs commits | May bundle policy + backlog + roadmap in one `docs(product):` commit |
| No push without ask | Unless owner explicitly requests |

---

## 8. Document maintenance

- **Add new items** to §4 table with ID, severity, source evidence.
- **Mark DONE** when acceptance criteria met + verify recorded in execution log.
- **Do not duplicate** `BACKLOG-QUEUE.md` infra Q items — link to `BACKLOG-VPN-FULL-AUDIT` for VPN infra.
- **Review** at 300 active configs or when policy v2 triggered.

---

**Version:** 1.0 · **Next:** AUDIT-001 VPN reliability diagnostic
