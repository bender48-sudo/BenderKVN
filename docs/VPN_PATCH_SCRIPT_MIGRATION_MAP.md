# VPN Patch-Script Migration Map

**Task:** VPN-PATCH-SCRIPT-MIGRATION-MAP-001 (part of VPN-ARCH-CONSOLIDATION-001)
**Companion:** [`VPN_PRODUCTION_GUARDRAILS.md`](VPN_PRODUCTION_GUARDRAILS.md)
**Guard module:** [`ops/vpn_production_guardrails.py`](../ops/vpn_production_guardrails.py),
[`ops/vpn_apply_guard.py`](../ops/vpn_apply_guard.py)

---

## Are we still patch-on-patch?

**PARTIALLY.** The inventory-driven architecture
(`node inventory → smoke matrix → production guardrails → selector apply gate →
owner-approved apply`) now exists and is enforced for the **future** selector
apply path. But legacy hardcoded patch scripts still exist and most still apply
to the live template via `--apply`. This sprint:

- **Consolidated now:** central guardrail module + tests; selector apply gate uses
  it; manual capacity-collapse patchers fail closed without `--owner-approved`;
  all listed capacity reducers print a guardrail banner; inventory SoT vocabulary
  documented.
- **Still patch-on-patch:** cron-managed auto-cutters
  (`latency_selector_autotrim`, `relay_failover_template`,
  `lv_node_down_nl_failover`, `lv_node_failover_auto`, `sync_injecthosts_connected`)
  still `--apply` from cron with hardcoded selectors/IPs. They are banner-flagged
  but NOT yet wired into the central guardrail (deliberate — changing live failover
  control flow risks an outage and needs owner approval).
- **Next:** migrate the cron auto-cutters to call `evaluate_guardrail()` before any
  capacity-reducing PATCH (P0 tasks below).

## Legacy script inventory

Source of truth used: `hardcoded` (IPs/selectors in code), `live API` (Remna panel),
`registry` (inventory-driven). Default mode: all default to **dry-run** (require
`--apply`) unless noted.

| Script | Purpose | Source of truth | Mutates prod? | Default mode | Owner gate | Rollback snap | Capacity guard | Can reduce pool? | Risk | Action taken |
|--------|---------|-----------------|---------------|--------------|-----------|---------------|----------------|------------------|------|--------------|
| `latency_selector_autotrim.py` | Trim slow relay/NL from Intl selectors (hysteresis) | hardcoded + live API | YES (`--apply`, cron) | dry-run | no | yes (snap) | MIN_PATHS=3 only | YES (relay1/2-only) | UNSAFE | Banner added; **P0 migrate** |
| `relay_failover_template.py` | Trim relay outbounds on RU probe fail | hardcoded + live API | YES (`--apply`, cron) | dry-run | no | yes | partial | YES | UNSAFE | Banner added; **P0 migrate** |
| `lv_node_down_nl_failover.py` | LV down → NL-only template failover | hardcoded + live API | YES (`--apply`, cron) | dry-run | no (`--gate`) | yes | no | YES (collapse to NL) | UNSAFE | Banner added; **P0 migrate (incident-only)** |
| `lv_node_failover_auto.py` | Cron driver for the above | hardcoded | YES (`--apply`, cron) | dry-run | no | via child | no | YES | UNSAFE | Banner added; **P0 migrate** |
| `sync_injecthosts_connected.py` | Drop injectHosts for down/disabled nodes | live API | YES (`--apply`, cron) | dry-run | no (`--gate`) | yes | MIN_INJECT=3 | YES (host count) | WARN | Banner added; **P0 migrate** |
| `patch_super_balancer_lv_relay_only.py` | Catch-all → LV+relay only | hardcoded | YES (`--apply`, manual) | dry-run | **YES now** | yes | no | YES | UNSAFE→GATED | `--owner-approved` required |
| `patch_trim_injecthosts_relay_only.py` | injectHosts → relay-only (6) | live API | YES (`--apply`, manual) | dry-run | **YES now** | yes | refuse-empty | YES | UNSAFE→GATED | `--owner-approved` required |
| `patch_trim_injecthosts_relay_nl.py` | Remove RELAY→NL :9443 hosts | live API | YES (`--apply`, manual) | dry-run | **YES now** | yes | no | YES (inject) | WARN→GATED | `--owner-approved` required |
| `patch_add_relay2_vpn.py` | Add relay#2 hosts + selectors | hardcoded | YES (`--apply`, manual) | dry-run | no | yes | n/a (adds) | no (adds) | WARN (legacy patcher) | Migrate to inventory (P1) |
| `patch_add_nl_intl_gated.py` | Add NL :443 to Intl_Direct (RU-probe gated) | hardcoded | YES (`--apply`, manual) | dry-run | no | yes | keeps relays | no (adds) | WARN (legacy patcher) | Migrate to inventory (P1) |
| `vpn_selector_apply_gate.py` | Read-only apply precondition gate | registry | NO | read-only | n/a | n/a | **YES (central)** | no | SAFE | Integrated with guardrail |
| `vpn_node_smoke_matrix.py` | Readiness matrix | registry | NO | read-only | n/a | n/a | yes | no | SAFE | Leave (architecture) |
| `vpn_production_guardrails.py` | Central capacity validator | registry/synthetic | NO | read-only | n/a | n/a | **core** | no | SAFE | New (architecture) |

> Many additional one-off `patch_*.py` (DNS/SNI/routing/encoding) exist; they are
> manual diagnostics-era patchers. They are P2 cleanup: classify as deprecated or
> document as read-only as they are touched. None are cron-managed.

## Target future home

| Script | Target home |
|--------|-------------|
| `latency_selector_autotrim.py` | production guardrails + selector (registry-driven trim with guard) |
| `relay_failover_template.py` | production guardrails (incident mode + TTL) |
| `lv_node_down_nl_failover.py` / `lv_node_failover_auto.py` | production guardrails (incident mode, TTL/rollback) |
| `sync_injecthosts_connected.py` | node inventory + apply gate (drive from registry health) |
| `patch_add_relay2_vpn.py` / `patch_add_nl_intl_gated.py` | node inventory onboarding (registry entry → generator) |
| manual trim/collapse patchers | deprecated once guardrail-driven degrade exists |

## Migration priority

- **P0 — unsafe live auto-cutters (cron):** `latency_selector_autotrim`,
  `relay_failover_template`, `lv_node_down_nl_failover` + `lv_node_failover_auto`,
  `sync_injecthosts_connected`.
- **P1 — one-off legacy patchers:** `patch_add_relay2_vpn`,
  `patch_add_nl_intl_gated`, manual relay/NL inject patchers.
- **P2 — diagnostics cleanup:** the remaining `patch_*` DNS/SNI/routing scripts.

## Exact next migration tasks

| Task ID | Scope | Done when |
|---------|-------|-----------|
| `SCRIPT-MIGRATE-LATENCY-AUTOTRIM-001` | Wire `latency_selector_autotrim` apply path through `evaluate_guardrail()` (degrade/incident mode, owner approval + rollback) | Apply blocked when it would breach minimums or collapse to relay-only without owner approval + TTL; tests prove it |
| `SCRIPT-MIGRATE-INJECTHOSTS-SYNC-001` | Drive `sync_injecthosts_connected` from registry health; guard host-count floor | Cannot drop below `minimum_delivery_paths`; guarded apply + tests |
| `SCRIPT-MIGRATE-RELAY-FAILOVER-001` | Convert `relay_failover_template` + `lv_node_*_failover` to incident mode with TTL + rollback + owner approval | No silent collapse; auto-restore on recovery; tests |
| `SCRIPT-MIGRATE-NL-RELAY-PATCHERS-001` | Replace hardcoded `patch_add_*` patchers with registry-driven onboarding generator | New nodes added via registry + apply gate, not hardcoded IPs |

Each task is owner-approved and must not perform live mutation without the
guardrail returning `allowed=true` plus a separate owner apply step.
