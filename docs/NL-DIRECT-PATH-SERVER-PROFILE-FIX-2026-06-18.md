# NL Direct Path — Server/Profile Consistency Fix — 2026-06-18

**Task:** NL-DIRECT-PATH-SERVER-PROFILE-FIX-001
**Status:** **PATH B — client profile corrected; WAITING_CLEAN_DIRECT_BASIC_SMOKE**
**Companions:**
[`NL-INDEPENDENT-EXIT-FIX-2026-06-18.md`](NL-INDEPENDENT-EXIT-FIX-2026-06-18.md) ·
[`NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md`](NL-INDEPENDENT-EXIT-TRAFFIC-SMOKE-2026-06-18.md)

> Repo-side generator/profile/validator fix only. No prod apply, no registry
> promotion, no server mutation. IPs/secrets redacted (ep_<hash>:port / node IDs).

---

## 1. Owner report(13) — recorded

| Field | Value |
|-------|-------|
| Active profile | `BenderVPN NL Split Stealth Canary — owner only` |
| Happ external routing overlay | **ON** — `selectedRoutingRule=BenderVPN RU`, `useRouting=true` |
| Session | connected ~1.5 min, then died |
| Telegram / relay2 stealth | **came alive** (loading) |
| Normal sites via NL direct | **did not load** |
| TUN startup | healthy (~1.5 s) |
| DNS set | OK |
| NL direct endpoint | reset / closed storm during active session |

**report(13).zip not present on this workstation** → analyzed from the owner's
described findings; a synthetic report(13)-class fixture
(`tests/fixtures/nl_smoke_report13_fixture.py`) encodes these for regression.

### Classification

- `SPLIT_STEALTH_FAIL_DIRECT_BRANCH` — stealth/relay2 carried Telegram; NL direct branch reset.
- `EXTERNAL_ROUTING_OVERLAY_STILL_ENABLED` — BenderVPN RU overlay can override embedded rules.
- `NL_DIRECT_RESET_STORM` consistent with a **client-side REALITY handshake break** on the direct exit.
- **NOT an NL PASS.**

---

## 2. Profile consistency check (redacted)

| Field | DIRECT_BASIC | SPLIT_STEALTH |
|-------|--------------|---------------|
| vless outbounds | 4 (NL only) | 7 (4 NL + 3 relay2) |
| NL exit | `ep_91…17:443` ×4 | same ×4 |
| relay2 | none | `ep_46…252:9443` ×3 |
| relay1 present | no | no |
| flow | `xtls-rprx-vision` | `xtls-rprx-vision` |
| security | `reality` | `reality` |
| SNI (NL) | `www.yandex.ru` | `www.yandex.ru` |
| shortId variants (NL) | 2 | 2 |
| publicKey | single, consistent | single, consistent |
| fingerprint | `chrome` | `chrome` |
| **sockopt.fragment (before)** | **present on all REALITY outbounds** | **present on all REALITY outbounds** |

### Root cause — client-side (PATH B)

`sockopt.fragment` (TLS fragmentation) was carried verbatim from the owner
source subscription onto **REALITY + xtls-rprx-vision** outbounds. Fragmenting
the TLS ClientHello corrupts the REALITY handshake on the **direct exit path**:
the session connects, survives a few seconds, then resets — exactly the
report(13) NL-direct reset storm. The relay2/stealth forwarder path re-wraps the
upstream connection, so it tolerated the fragment enough for Telegram to come
alive — matching "stealth alive, direct dead".

The repo already strips this **server-side**
(`ops/patch_remove_fragment_defaults.py` — "can break Reality on some ISPs");
the canary **client builder** previously did not.

---

## 3. Correction applied (repo-side, client profile)

- `ops/nl_canary_profile_builder.py`:
  - `_strip_reality_fragment()` removes `sockopt.fragment` from every REALITY
    outbound during `_finalize()` (other sockopt keys — tcpNoDelay/keepalive —
    are preserved); empty `sockopt` is dropped.
  - `reality_fragment_outbounds()` helper lists any REALITY outbound still
    carrying fragment (used by the validator).
- `ops/validate_happ_importable_profile.py`: `validate_nl_canary_variant` now
  **FAILS** if any REALITY outbound carries `sockopt.fragment`.
- Profiles regenerated (`.local`, not committed); both variants validate
  `ok=True`; `fragment` occurrences = **0**.

No server mutation. No registry promotion.

---

## 4. Read-only NL server/Remna check

Not performed from this workstation: no SSH key/config present and panel access
requires live prod credentials (would hit production). The client-side fragment
defect is independently sufficient to explain report(13) and is fixed here.
Owner-runnable read-only checks remain available:
`ops/nl_node_health_probe.py` and `.secrets/nl-health.sh` (docker/ports/load).

If a clean Direct Basic smoke on the corrected profile still resets NL direct,
escalate to a server-side REALITY consistency check (shortId/publicKey/SNI/dest)
under **APPROVE NL DIRECT SERVER FIX**.

---

## 5. Tests

- `tests/test_nl_canary_profile_builder.py`:
  - builder strips REALITY fragment (direct_basic);
  - validator rejects a profile that still carries fragment.
- `tests/test_analyze_nl_canary_smoke.py`: report(13)-class fixture →
  `NOT_TESTED` (overlay enabled).
- Full relevant suite: **31 passed**.

---

## 6. Gate

| Gate | State |
|------|-------|
| NL Direct Basic | client profile corrected · **WAITING_CLEAN_DIRECT_BASIC_SMOKE** |
| NL Split Stealth | not accepted (overlay-contaminated report 13) |
| Registry promotion | **NO** |
| PUBLIC_PROD | **NO-GO** (`delivery_path_nodes=1`) |
| 300 / 30k | **NO-GO** |

**Next owner action:** RUN OWNER NL DIRECT BASIC SMOKE (clean — overlay OFF, no
Telegram, import only `independent_exit_nl_DIRECT_BASIC_IMPORTABLE_PROFILE.json`).
