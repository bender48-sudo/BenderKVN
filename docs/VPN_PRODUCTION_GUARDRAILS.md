# VPN Production Guardrails

**Task:** VPN-PRODUCTION-GUARDRAILS-001 (part of VPN-ARCH-CONSOLIDATION-001)
**Status:** ACTIVE (repo-side enforcement; live apply still owner-gated)
**Module:** [`ops/vpn_production_guardrails.py`](../ops/vpn_production_guardrails.py)
**Tests:** [`tests/test_vpn_production_guardrails.py`](../tests/test_vpn_production_guardrails.py)

---

## 1. Core rule

**Stability must NOT be achieved by silently reducing production capacity.**

Every capacity reduction must be an explicit, owner-approved decision (degrade /
drain / incident / manual emergency) with a rollback snapshot and — for incidents
— a TTL. Auto-cutting is dry-run/diagnostic by default.

## 2. Source of truth

[`ops/config/vpn_node_registry.yaml`](../ops/config/vpn_node_registry.yaml) is the
**production node inventory source of truth**. Hardcoded IP/host patch scripts are
**legacy only** and are being migrated (see
[`VPN_PATCH_SCRIPT_MIGRATION_MAP.md`](VPN_PATCH_SCRIPT_MIGRATION_MAP.md)).

Target architecture:

```
node inventory -> node smoke matrix -> production guardrails -> selector apply gate -> owner-approved apply
```

## 3. Node lifecycle

```
staging -> canary -> production -> degraded -> drain -> disabled
```

| Stage | Counts as production capacity? | Notes |
|-------|-------------------------------|-------|
| staging | No | Pre-acceptance; canary_percent=0 |
| canary | No (separate canary count) | Small % only; never the full pool |
| production | Yes | active + delivery_path_eligible + healthy |
| degraded | Reduced weight, still a path | Must preserve minimum |
| drain | Being emptied | No new assignments; explicit |
| disabled | No | Out of pool |

Lab-only, backup/sub-edge, suspect, and unknown-status nodes **never** count as
production capacity.

## 4. Operational modes (kept separate)

| Mode | Purpose | Capacity reduction? |
|------|---------|---------------------|
| `dry_run` | Validate only; never applies | n/a (no apply) |
| `scale` | Add capacity / raise weights | **Not allowed to reduce** |
| `degrade` | Lower weight but preserve the path where possible | Allowed if minimums preserved |
| `incident` | Temporary cut with TTL + auto re-evaluate | Allowed with TTL + rollback + approval |
| `manual_emergency` | Owner human override with snapshot/rollback | Allowed, owner-driven |

## 5. Auto-patch / apply hard gates

A production-changing apply **fails closed** unless ALL hold:

- a dry-run was generated first;
- owner approval present;
- rollback snapshot present;
- delivery-path minimum preserved (`minimum_delivery_paths`, default 2);
- relay-IP minimum preserved (`minimum_relay_ips`, default 2 where relays apply);
- geo/location minimum preserved if configured (`minimum_geos`);
- canary nodes preserved unless an explicit drain;
- lab-only nodes not counted as production;
- disabled/backup nodes not counted as production;
- no relay-only collapse (`block_relay_only_collapse`) outside manual emergency;
- no production-capacity decrease without degrade/incident/drain mode;
- incident TTL present if capacity decreases;
- unknown-status nodes not counted as clean capacity;
- selector apply gate ([`ops/vpn_selector_apply_gate.py`](../ops/vpn_selector_apply_gate.py)) passes.

The selector apply gate consumes this module, so the same rules apply to any
future selector apply.

## 6. Drain policy

1. Degrade weight first.
2. Drain before disabling — no sudden deletion.
3. A TTL or review date is required for incident-driven reductions.
4. Restoring capacity is always allowed (it is not a reduction).

## 7. Legacy script policy

- Old hardcoded patch scripts are **not** architecture.
- They must become dry-run, guarded, or deprecated.
- Capacity-reducing manual patchers fail closed without `--owner-approved`
  (via [`ops/vpn_apply_guard.py`](../ops/vpn_apply_guard.py)).
- cron-managed reducers print a guardrail banner and are scheduled for P0
  migration to the central guardrail (control flow unchanged this sprint to avoid
  an outage in live failover automation).
- New generators must consume the registry/inventory, not hardcoded IPs.

## 8. Capacity planning (inputs the inventory should carry)

| Dimension | Where |
|-----------|-------|
| concurrent users per node | registry `capacity` / estimates |
| Mbps / provider | registry `capacity_mbps_estimate` |
| peak online ratio | `capacity_policy.peak_concurrency_ratio_default` |
| outbounds per client | selector policy (no client server picker) |
| subscription page / Caddy / bot / DB / Remna bottlenecks | infra plan ([`VPN-ARCH-30K-CAPACITY-PLAN.md`](VPN-ARCH-30K-CAPACITY-PLAN.md)) |

## 9. Current truth (baseline `c17f012`)

- `delivery_path_nodes = 1` (lv-exit-1 only) → below minimum 2.
- PUBLIC_PROD selector = NO-GO; APPLY_ALLOWED = false.
- ru-relay-1 suspect (excluded); ru-relay-2-lab lab-only; nl-node-1 disabled;
  ams-backup-edge backup.
- 300 / 30k / commercial launch remain **NO-GO**.

> No prod mutation, deploy, Remna/Caddy/template/subscription change is performed
> by this guardrail. It validates only.
