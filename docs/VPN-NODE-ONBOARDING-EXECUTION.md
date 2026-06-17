# VPN-NODE-ONBOARDING-EXECUTION — new prod path, staging → canary → active

**Task:** NODE-ONBOARD-NEW-PROD-PATH-001
**Status:** READY FOR OWNER ACTION
**Pairs with:** `VPN-NODE-PURCHASE-REQUEST.md`, `VPN-NODE-RUNBOOK.md`,
`VPN-NODE-ACCEPTANCE-CHECKLIST.md`, `docs/examples/node-registry.new-prod-node.template.yaml`.

> Every step below is **staging-only / dry-run** in this sprint. No live
> subscription/template/Remna/Caddy mutation. Promotion to production requires a
> separate explicit owner APPROVE APPLY.

---

## 1. Bootstrap (after purchase)

1. Follow `VPN-NODE-RUNBOOK.md` bootstrap section on the new VPS.
2. Keep ALL connection material (IP, domain, UUID, keys) in the owner secure
   store / `.secrets/` — never in git, never in chat.
3. Confirm KVM, dedicated IPv4, AUP allows VPN (re-check §1 of purchase request).

## 2. Monitoring setup

1. Install the same monitor agent used for lv-exit-1 / relays.
2. Confirm it reports `monitor_status` and reconnect rate.
3. Require >= 24 h healthy soak before any promotion.

## 3. Registry staging entry

1. Copy `docs/examples/node-registry.new-prod-node.template.yaml`.
2. Fill **redacted** fields only (no secrets): `node_id`, `region`, `country`,
   `provider_label`, `groups`.
3. Keep defaults: `status: staging`, `canary_percent: 0`,
   `allow_new_assignments: false`, `delivery_path_eligible: false`.
4. Generate a local draft (never the prod registry):
   ```
   python ops/prepare_new_node_registry_entry.py --node-id de-exit-1 --country DE --dry-run
   ```
5. Validate a staging copy:
   ```
   python ops/validate_vpn_node_registry.py --registry <staging-copy>.yaml
   ```

## 4. Smoke checks

1. `python ops/vpn_node_smoke_matrix.py --markdown` — new node should show
   `WARN` (staging) and NOT count as production capacity yet.
2. Run owner smoke on the node (active traffic + sleep/wake), export logs to
   `.secrets/diagnostics/`.
3. Complete `VPN-NODE-ACCEPTANCE-CHECKLIST.md` P0.

## 5. Promotion gates (staged, each owner-approved)

| Stage | Registry change | Gate |
|-------|-----------------|------|
| 1. Canary | `status: canary`, `canary_percent: 1–5` | acceptance P0 PASS + owner OK |
| 2. Active (eligible) | `status: active`, `delivery_path_eligible: true`, `allow_new_assignments: true` | 24 h canary clean + owner APPROVE APPLY |
| 3. Selector apply | run `ops/vpn_selector_apply_gate.py` → APPLY_ALLOWED=true | all gates green + rollback ready |

Only after Stage 2 does `delivery_path_nodes` become 2.

## 6. Canary_percent policy

- Start at 0 (staging), step to 1–5 for canary, then ramp only with owner sign-off.
- Never jump straight to 100.

## 7. Rollback / decommission

- Canary fails → set `status: draining`, `allow_new_assignments: false`,
  drain, then `decommissioned`.
- No production default changes until Stage 2; rollback at canary is just
  removing the canary node from selection (no user migration).
- Return hardware within refund window if it fails acceptance.

## 8. What this does NOT do

- Does not write the production registry automatically.
- Does not mutate Remna/Caddy/subscriptions.
- Does not activate NL or relay2 as production default.
- Does not claim 300/30k GO.

**NL reference (2026-06-17):** [`NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md`](NL-A2-A4-CONTROLLED-CANARY-SMOKE-2026-06-17.md) — `nl-node-1` at `staging`, SSH PASS, synthetic canary preview ready; live `canary_percent` remains 0 until traffic smoke + owner approval.
