# RU-RELAY-ARCH-UNIFICATION-001 — Standard RU Relay Architecture

**Task:** RU-RELAY-ARCH-UNIFICATION-001
**Date:** 2026-06-17
**Mode:** Architecture unification (define standard, register compliance, gate generator). Repo-side; one scoped read-only server compare. No prod mutation this task.
**Parents:** [`DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md`](DESKTOP-RELAY1-SERVICE-REPAIR-2026-06-17.md) ·
[`CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md`](CLIENT-STABILITY-DESKTOP-RELAY-PATH-FIX-2026-06-17.md) ·
[`RELAY1-DRAIN-OR-RETEST-DECISION.md`](RELAY1-DRAIN-OR-RETEST-DECISION.md)
**Branch / HEAD baseline:** `product-referral-cabinet-ui-v1` @ `69ceb28`

> Endpoints redacted to `ep_<hash>:port`; nodes by `node_id`. No raw IPs/UUIDs/secrets.
> Read-only SSH compare of ru-relay-1 and ru-relay-2. No LV/relay2/subscription/template mutation.

---

## 1. Decisive finding — the relays are identical twins on one upstream

Read-only compare of ru-relay-1 vs ru-relay-2:

| Aspect | ru-relay-1 | ru-relay-2 | Same? |
|--------|------------|------------|-------|
| Stack | hysteria v2.8.1 forwarder | hysteria v2.8.1 forwarder | ✅ |
| xray / REALITY | **none installed** | **none installed** | ✅ |
| docker / remnanode | none | none | ✅ |
| caddy | inactive | inactive | ✅ |
| client.yaml keys | server/auth/tls/tcpForwarding | identical | ✅ |
| tls insecure | true | true | ✅ |
| **hysteria upstream** | `ep_4b84b15b:443` | `ep_4b84b15b:443` | ✅ **shared** |
| **tcp forward remote** | `ep_82c23da5:443` | `ep_82c23da5:443` | ✅ **shared** |
| forwarding-error rate | 10 / 180s | 10 / 180s | ✅ |
| server-side errors | 0 | 0 | ✅ |

**Conclusions:**
1. The RU relay architecture is a **hysteria TCP-forwarder** (server UDP:443 + client TCP
   443/8443/9443 forwarding to an upstream). The `VPN-NODE-RUNBOOK.md` xray/REALITY design
   describes **exits**, not RU relays.
2. ru-relay-1 is **NOT a uniquely broken server path** — it is functionally identical to the
   "healthy" ru-relay-2, same error rate. report(10)'s ~80.3% reset dominance on ru-relay-1
   was **session/balancer-specific**, not a persistent server defect.
3. **Both relays share one upstream/backend** (`shared_upstream_group: ru-fwd-upstream-1`).
   They are two front-ends to ONE backend → **not independent delivery paths**. The
   relay2-only "fix" is an A/B diagnostic of front-end choice, **not** real redundancy.

---

## 2. STANDARD_RU_RELAY_PATH_V1 (canonical RU relay)

| Dimension | Standard |
|-----------|----------|
| path_role | `relay` |
| Service type | hysteria v2.8.x (server + client tcpForwarding) |
| Process / unit | `hysteria-server.service` (UDP:443), `hysteria-client.service` (TCP 443/8443/9443) |
| Port ownership | hysteria owns 443/udp + 443/8443/9443/tcp |
| Transport | client TCP ingress → hysteria QUIC tunnel → upstream exit |
| Upstream | a registered exit/upstream (`shared_upstream_group`) |
| Firewall | default-deny except 443(t/u), 8443/tcp, SSH, monitor port |
| Health check | hysteria-client forwarding-error rate; upstream reachability; listener ownership |
| Logs | `journalctl -u hysteria-client/-server` (redacted) |
| Registry fields | `path_role`, `architecture_compliance`, `architecture_standard`, `shared_upstream_group` |
| Generator | registry-driven, position-independent `out-<node_id>` tags (no proxy-N) |
| Canary / drain | `status`, `rollout.canary_percent`, `exclude_from_desktop_canary`, `incident` |

> Exits (LV/NL) use a separate standard (xray/REALITY/Caddy per runbook). This doc covers
> the RU relay tier only.

---

## 3. Architecture decision — PATH C (formalize) + honest capacity correction

| Path | Verdict |
|------|---------|
| A — rebuild relay1 to xray/REALITY | **Rejected** — would DIVERGE from the actual twin architecture; needs unavailable Remna/REALITY secrets; relay2 isn't xray either. |
| B — replace relay1 | **Rejected as a fix** — relay1 ≈ relay2; replacing one twin adds no independent path (same upstream). |
| **C — formalize hysteria-forwarder as STANDARD_RU_RELAY_PATH_V1** | **Chosen** — matches reality on both relays; make `path_role`/`architecture_compliance`/`shared_upstream_group` first-class so non-compliant paths can't enter pools and twins aren't double-counted. |

**The real scalability gap is an INDEPENDENT exit/upstream, not a relay1 rebuild.** Adding a
second relay that forwards to the same upstream does NOT create a second delivery path.

---

## 4. Repo changes

- `ops/validate_vpn_node_registry.py`: new optional enums `PATH_ROLES`,
  `ARCHITECTURE_COMPLIANCE`; validates `path_role`, `architecture_compliance`,
  `shared_upstream_group` when present.
- `ops/vpn_registry_model.py`: `architecture_compliance()`, `path_role()`,
  `shared_upstream_group()`, `is_architecture_compliant()`; **fail-closed gate** — only
  `architecture_compliance == compliant` nodes may enter CANARY/PUBLIC_PROD; model exposes
  the new fields; `exclusion_reason` reports architecture non-compliance.
- `ops/config/vpn_node_registry.yaml`:
  - `lv-exit-1` → `path_role: exit`, `architecture_compliance: compliant`.
  - `ru-relay-1` / `ru-relay-2` → `path_role: relay`, `architecture_compliance: compliant`,
    `architecture_standard: STANDARD_RU_RELAY_PATH_V1`, `shared_upstream_group: ru-fwd-upstream-1`.
  - `ru-relay-1` reclassified: `repair_status: architecture_twin_verified`; incident framing
    corrected (twin of relay2, not uniquely broken); kept excluded from desktop canary +
    `retest_required` (conservative).
  - `nl-node-1` → `architecture_compliance: unverified` (staging; must be verified before canary).
  - `path_role` set on lab/backup nodes.
- `ops/generate_desktop_relay_path_canary.py`: plan now carries `architecture_compliance` +
  `shared_upstream_group` and flags `diagnostic_ab_not_guaranteed_fix` when both relays share
  one upstream.
- Tests: `tests/test_vpn_registry_model_architecture.py` (fail-closed gate, helpers);
  generator/model test helpers set `architecture_compliance` for clean synthetic exits.

**Invariants enforced + tested:** unverified/non_compliant/replace_required excluded from
canary/prod; compliant exit retained; relays compliant but still not standalone delivery
paths; lab unaffected; PUBLIC_PROD stays NO-GO; `delivery_path_nodes` stays honest (=1).

---

## 5. relay1 vs relay2 vs standard (decision table)

| Check | Standard | ru-relay-1 | ru-relay-2 | Decision |
|-------|----------|------------|------------|----------|
| service | hysteria fwd | hysteria fwd | hysteria fwd | comply |
| upstream | registered | ru-fwd-upstream-1 | ru-fwd-upstream-1 | shared (no diversity) |
| error rate | low | 10/180s | 10/180s | parity |
| compliance | compliant | compliant | compliant | both standard |
| independent path | required for scale | NO (shared) | NO (shared) | need new upstream |

---

## 6. Owner artifacts (.local, not committed)

- **Immediate A/B diagnostic:** relay2-only owner profile via
  `ops/generate_desktop_relay_path_canary.py` + `ops/generate_happ_relay2_lab_profile.py`
  (relabeled: A/B test of front-end choice, not a guaranteed fix — both relays share upstream).
- **Architecture path:** the durable fix is an independent exit/upstream (procurement),
  per `VPN-ARCH-30K-CAPACITY-PLAN.md`.

---

## 7. Tests / smoke

| Check | Result |
|-------|--------|
| `validate_vpn_node_registry.py` | PASS (no secrets) |
| `vpn_registry_model.py` | lv-exit-1 PROD/CANARY kept; relays excluded; unverified fail-closed |
| `vpn_selector_apply_gate.py --cohort PUBLIC_PROD` | NO-GO (expected) |
| generator dry-run LAB_OWNER / CANARY | GO (lab profile / lv-exit-1) |
| desktop canary generator | tokens correct; diagnostic_ab flag set |
| pytest (VPN/relay/registry/selector/matrix/canary) | 230 passed |
| `git diff --check` | clean |

---

## 8. Gate status

| Gate | Status |
|------|--------|
| Desktop stability | OPEN — root cause is shared upstream/forward design, not relay1 alone |
| relay1 | COMPLIANT twin of relay2; retest_required; not uniquely broken |
| relay2 | COMPLIANT reference; not an independent path (shared upstream) |
| PUBLIC_PROD | NO-GO (`delivery_path_nodes=1`) |
| 300 / 30k | NO-GO (need an INDEPENDENT second exit/upstream) |

---

## 9. Owner next action — choose ONE

- **`RUN OWNER RELAY2-ONLY DESKTOP CANARY 15 MIN`** — A/B diagnostic (does front-end choice
  reduce resets, given shared upstream?).
- **`APPROVE NEW RELAY NODE PURCHASE TO REPLACE RELAY1`** — procure an **independent** second
  exit/upstream (true path diversity) per `VPN-ARCH-30K-CAPACITY-PLAN.md` — the durable fix.

> Desktop PASS NOT claimed. 300/30k GO NOT claimed. No prod mutation this task.
