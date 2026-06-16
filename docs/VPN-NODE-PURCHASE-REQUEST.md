# VPN-NODE-PURCHASE-REQUEST — second production delivery path

**Task:** NODE-ONBOARD-NEW-PROD-PATH-001
**Status:** READY FOR OWNER ACTION
**Why:** `delivery_path_nodes = 1`. PUBLIC_PROD, paid beta, 300, and 30k are all
NO-GO until a **second, provider/DC-diverse, production-capable** exit exists.
**This doc does not buy anything.** It is the exact spec for the owner to procure.

---

## 1. Provider requirements (hard)

| Requirement | Value | Why |
|-------------|-------|-----|
| Virtualization | **KVM** (not OpenVZ/LXC) | Need own kernel for Xray/TUN tuning |
| Root access | **Full root** | Bootstrap + monitoring agent |
| IPv4 | **Dedicated IPv4** (not shared/CGNAT) | Stable reachability + SNI/stealth |
| AUP | **VPN/proxy explicitly allowed** | Avoid mid-month termination |
| Diversity | **Different provider AND datacenter/ASN than lv-exit-1** | Real N+1; one provider outage must not drop both paths |
| Billing | **Monthly or trial first** | No annual prepay before acceptance PASS |
| Refund window | **>= 7 days** | Reject fast if smoke fails |

## 2. Capacity minimums (first prod path, ~300 configs target)

| Resource | Minimum | Notes |
|----------|---------|-------|
| vCPU | 2 | AES-NI present |
| RAM | 2 GB | 4 GB preferred for headroom |
| Bandwidth | >= 5 TB/mo or fair-use that tolerates VPN | Confirm no silent throttle |
| Port speed | >= 1 Gbps shared | Burst for evening peak |
| Disk | 20 GB SSD | Logs rotate small |

## 3. Target geo options (pick by routing strategy)

Ordered by fit with `VPN-ROUTING-PROFILE-STRATEGY.md`:

1. **EU non-LV** (e.g. DE/NL/FI) — diversifies away from the single LV exit.
2. **Low-latency-to-RU EU edge** — keeps relay→exit hop short.
3. Avoid re-using the exact LV provider/DC even if cheapest.

> No specific provider names committed here. Keep provider identity in the owner
> secure store, not git.

## 4. Acceptance criteria (must ALL pass before promotion)

Run `VPN-NODE-ACCEPTANCE-CHECKLIST.md` P0. Summary:

- Boots, root SSH works, KVM confirmed.
- Dedicated IPv4 reachable; no CGNAT.
- AUP re-confirmed in writing (ticket/email).
- Xray/stealth comes up; owner smoke PASS (active traffic + sleep/wake).
- Provider/DC differs from lv-exit-1.
- Monitoring agent reports healthy for >= 24 h soak.

## 5. Reject criteria (any one → return within refund window)

- OpenVZ/LXC or no own kernel.
- Shared/CGNAT IPv4.
- AUP forbids VPN/proxy or is "unclear" and provider won't confirm.
- Same provider/DC as lv-exit-1 (no real diversity).
- Smoke fails or reconnect storms during 24 h soak.
- Silent bandwidth throttle under evening load.

## 6. Exact first owner action

1. Procure ONE node meeting §1–§3 (monthly/trial).
2. Reply: **`APPROVE NEW NODE PURCHASE USING VPN-NODE-PURCHASE-REQUEST.md`**
   then follow `VPN-NODE-ONBOARDING-EXECUTION.md`.

**Expected effect on success:** `delivery_path_nodes` 1 → 2, unlocking the
PUBLIC_PROD / paid-beta gate re-evaluation in the smoke matrix (still requires
the selector apply gate + owner APPROVE APPLY before any live change).
