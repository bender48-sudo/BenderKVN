# VPN Config Stability / Scalability / Stealth Sprint — 2026-06-17

**Task:** `VPN-CONFIG-STABILITY-SCALABILITY-STEALTH-SPRINT-001`
**Branch:** `product-referral-cabinet-ui-v1`
**Scope:** repo-side VPN config architecture only. **No production apply, no
billing/cabinet/journey.** LV production path preserved.

Move from fragile proxy-N / patch-on-patch assumptions toward registry-driven
config generation, a central integrity verifier, stealth routing guardrails, and
guarded auto-cutters — with reproducible dry-run smoke and strict gates.

> Wording: this sprint does **not** make the VPN "undetectable". It only keeps the
> traffic profile closer to ordinary TLS/web, keeps sensitive destinations on the
> stealth path, keeps relay endpoints inside the tunnel, and preserves rollback.

---

## Baseline (Phase 0)

| Signal | Value |
|--------|-------|
| HEAD | `d46be45` (+ this sprint) |
| delivery_path_nodes | **1 / 2** (lv-exit-1 only proven exit) |
| PUBLIC_PROD | **NO-GO** |
| APPLY_ALLOWED | **false** |
| LAB_OWNER | GO (owner lab) |
| CANARY | dry-run only; NL not yet canary (canary_percent=0) |
| 300 / 30k | **NO-GO** |

## Proxy-N position assumptions (Phase 1)

| File | Old assumption | Risk | Fixed / gated / deprecated | Test |
|------|----------------|------|----------------------------|------|
| `patch_add_relay_nl_443_inject.py` | "last 6 UUIDs" injected; count-only already-applied; hosts enabled before patch | dead path / silent mismatch | **HARDENED** — patch+verify **before** host enable; already-applied proves injected+enabled; `--owner-approved`; integrity `verify_proxy_tags_within_slots` | `test_patch_add_relay_nl_443_inject_order.py` |
| `relay_failover_template.py` | positional `proxy-5..7` trim, no central guard | silent relay collapse | **MIGRATED** to central guardrail (mode+TTL+rollback+owner) | `test_relay_failover_guardrails.py` |
| `balancer_selectors.relay_n_selector` / selectors | positional `proxy-N` lists | selector over-reach beyond inject slots | **Quarantined by verifier** `verify_proxy_tags_within_slots` (proxy-N must not exceed inject slots) | `test_vpn_config_integrity.py` |
| new model/generator | n/a | n/a | **Position-independent** `out-<node_id>` outbound tags | `test_vpn_registry_model.py` |

## Registry-driven model + generator (Phases 2–3)

- `ops/vpn_registry_model.py` — registry → deterministic `NodeModel`
  (node_id, lifecycle, role, region, delivery_path_eligible, canary_percent,
  health, capacity, allowed_cohorts, **outbound_tag derived from node_id**,
  selector_group, route_classes, weight, drain/incident, exclusion reason).
  - disabled/suspect/lab/backup excluded from prod by default;
  - staging/canary selectable only for their cohorts;
  - PUBLIC_PROD requires ≥2 clean production delivery paths;
  - **no hardcoded "proxy-N means node X"**.
- `ops/generate_vpn_config_from_registry.py` — **dry-run** generator. Cohorts
  `LAB_OWNER` / `CANARY` / `PUBLIC_PROD`. Emits outbounds, selector groups, route
  policy, capacity + guardrail summary. Writes only to `.local/` (gitignored from
  commit), no secrets, no real UUID/endpoint.
  - PUBLIC_PROD current state → **NO-GO** (1 < 2 paths);
  - synthetic 2nd clean exit → dry-run GO (test-proven).

## Config integrity verifier (Phase 4)

`ops/vpn_config_integrity.py` proves:
- every selector target maps to a known outbound tag;
- proxy-N tags never exceed actual inject slots;
- inject UUIDs map to real, **enabled** hosts;
- host UUID → intended node_id group ("last 6 UUIDs" rejected);
- **already-applied** must prove injected **and** enabled (count-only rejected).
Used in the generator and in `patch_add_relay_nl_443_inject`.

## Stealth / routing guardrails (Phase 6)

`ops/vpn_stealth_routing_guard.py` (subscription template layer) +
`happ_routing_directip_guard.py` (Happ client layer):
- TG/Meta/Instagram/Telegram markers must stay on the stealth balancer, never the
  general/direct catch-all;
- stealth balancer must receive both an IP-CIDR and a domain rule;
- no flat `Super_Balancer` catch-all swallowing the split;
- regression test on committed `happ_routing_profile_ru.json` → **no `geoip:ru`
  DirectIp**, no relay infra in DirectIp, no `FallbackTag=direct`.

## Auto-cutting / failover status (Phase 7)

| Script | Status |
|--------|--------|
| `latency_selector_autotrim.py` | MIGRATED (prior sprint) |
| `sync_injecthosts_connected.py` | MIGRATED (prior sprint) |
| `relay_failover_template.py` | **MIGRATED this sprint** — `--apply` needs `--mode/--owner-approved/--rollback-snapshot`; relay collapse fails closed |
| `lv_node_down_nl_failover.py` / `lv_node_failover_auto.py` | **STILL PENDING** (banner only) — remaining silent-collapse risk |

## NL / RU canary readiness (Phase 8)

- NL: `staging`, `delivery_path_eligible=false`, `canary_percent=0`. Generator
  `CANARY` dry-run does not include NL until canary flag set. **No apply.**
- RU relay: identity/quality still ambiguous (relay-1 suspect; relay-2 diversity).
- Owner canary: `generate_owner_canary_profile.py` unchanged; LAB_OWNER GO.
- **Next owner phrase:** `APPROVE NL CANARY TRAFFIC SMOKE` (import `.local/nl_canary_owner_profile.md`).

## Tests

92 VPN-suite tests green (model 12, integrity 10, generator 6, patch-order 4,
stealth 7, relay-failover 8, + existing autotrim/injecthosts/directip suites).
`git diff --check` clean; secret/mojibake scan clean on new files.

## Safety

- Prod mutation: **NO**. Deploy/reload: **NO**. Remna/Caddy/template/subscription
  changes: **NO**. VPN routing changes: **NO**. LV path preserved: **YES**.
- Raw secrets printed/committed: **NO**. `.local`/raw logs committed: **NO**.
- 300/30k GO claimed: **NO**. "Undetectable VPN" claimed: **NO**.
