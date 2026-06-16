# RELAY1-DRAIN-OR-RETEST-001 — relay1 decision artifact

**Status:** DECISION READY — owner action required. No live apply in this sprint.
**Surface:** repo-side selector/matrix policy + this decision doc. No prod mutation.
**Parent:** VPN-CORE-SCALABILITY-STABILITY-SPRINT-001.

---

## 1. Why relay1 stops being a vague "suspect"

`ru-relay-1` has been carried as an undefined "suspect" node. This doc converts
that into an enforced, tested repo policy plus a single owner go/no-go.

### Current suspect evidence (registry-derived, redacted)

| Field | Value |
|-------|-------|
| node_id | `ru-relay-1` |
| role | relay |
| health.monitor_status | `suspect` |
| health.last_smoke_status | `needs_diagnosis` |
| health.last_owner_test_status | `soft_pass` |
| delivery_path_eligible | false |
| notes | live Candidate D injectHosts member; client stability reports (dial/open storms) |

The registry holds no endpoints/UUIDs — all evidence here is health metadata only.

---

## 2. Enforced policy (now tested in repo)

Tests: `tests/test_relay1_suspect_policy.py` (8 cases, green).

| Rule | Enforced by | Test |
|------|-------------|------|
| Suspect node excluded from `PUBLIC_PROD`, `OWNER_FF`, `PAID_BETA_MANUAL`, `CANARY` | `ops/vpn_node_selector.py` `_is_suspect` + `evaluate_node_for_cohort` | `test_relay1_excluded_from_production_cohorts` |
| Suspect never counted as production capacity | `ops/vpn_node_smoke_matrix.py` `is_production_capacity` | `test_relay1_not_production_capacity` |
| Suspect included ONLY with explicit `--allow-suspect`/`--diagnostic` | selector `allow_suspect` path | `test_relay1_included_only_with_diagnostic_flag` |
| Diagnostic inclusion still NOT production capacity | matrix `is_production_capacity` | same test |
| Owner canary excludes relay1 by default | `ops/generate_owner_canary_profile.py` | `test_relay1_excluded_from_owner_canary` |

**Net effect:** relay1 cannot silently re-enter production or canary selection,
and cannot inflate `delivery_path_nodes` / `production_capacity_nodes`.

---

## 3. What relay1 IS allowed for now

- Remaining in its current live Candidate D pool membership **as already
  deployed** (this sprint does NOT touch live config — no drain applied).
- Read-only diagnostic evaluation via `--allow-suspect` / `--diagnostic` flags.

## 4. What relay1 is BLOCKED from

- Counting toward `delivery_path_nodes` or `production_capacity_nodes`.
- Selection into any production or canary cohort in selector dry-run.
- Inclusion in the owner canary stability profile.
- Being treated as a healthy second path for 300/30k gates.

---

## 5. Owner next action — choose ONE

The three options are mutually exclusive for the next step. The repo policy holds
regardless of choice; these only decide what diagnostic/operational move follows.

| Option | What it means | Exact owner approval phrase |
|--------|---------------|-----------------------------|
| **A. Read-only retest** | Owner runs a controlled relay1-only smoke (no prod change) and exports logs for analysis before any drain | `APPROVE READ-ONLY RELAY1 RETEST` |
| **B. Exclude from next canary** | Keep relay1 out of the next canary/selector cohort explicitly (already the default policy; this confirms intent for a future apply) | `APPROVE RELAY1 EXCLUSION FROM NEXT CANARY` |
| **C. Replace / buy new node** | Treat relay1 as not worth retesting; prioritize a new production path (see `VPN-NODE-PURCHASE-REQUEST.md`) | `APPROVE NEW NODE PURCHASE USING VPN-NODE-PURCHASE-REQUEST.md` |

**Recommendation:** Option A (read-only retest) is the cheapest next step and
directly feeds the smoke matrix. If retest fails again, escalate to Option C.

> No live drain, exclusion apply, or node purchase is performed in this sprint.
> Each option above requires a separate explicit owner-approved prompt.
