# AUDIT — Telegram web-trial bind flow (P1-REF-001 §9)

**Date:** 2026-06-09 (read-only pass)  
**Mode:** Telegram bind-flow audit only — no deploy, no prod mutation  
**Branch:** `product-referral-cabinet-ui-v1` · local HEAD ahead of origin  
**Related:** [`POSTDEPLOY-2026-06-10-P1-REF-001.md`](POSTDEPLOY-2026-06-10-P1-REF-001.md), [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md) (prior device/balance findings preserved separately)

---

## 1. Executive summary

**Verdict:** The prepared `p1bind-` trial **never reached the prod bot `/start bind_*` handler** on AMS. This is **not** evidence of a bind migration bug.

| Conclusion | Detail |
|------------|--------|
| **Most likely cause** | Bind deep link **not opened in the Telegram app** (browser preview, copied wrong link, or bind step skipped despite owner belief) |
| **Confidence** | **High** for “no bot entry”; **Low** for any migration-code defect |
| **Token state** | Still valid (not expired, not consumed) at audit time |
| **Prod bot** | Polling active; bind routing code deployed; other `/start` traffic logged |
| **Instrumentation** | `funnel_bot_start` with `meta LIKE 'bind:%'` count = **0** (all time); `web_tg_bind` count = **0** (all time) |

**Do not retry owner bind until retest plan (§9) is followed.** Do not mark POSTDEPLOY §9 PASS without DB bind evidence.

---

## 2. Current failure evidence

From prior verification runs and this audit (AMS read-only):

| Check | Result |
|-------|--------|
| Smoke verify | `NOT_BOUND` · `P1_BIND_VERIFY_PENDING` |
| `web_trial_claims.telegram_id` | **NULL** |
| `web_trial_claims.bound_at` | **NULL** |
| `web_trial_claims.bind_token` | **Present** (prefix `ef549b****`) |
| Web surrogate row | **Exists** |
| `referrals.referred_user_id` on web uid | **Present** (not migrated to TG id) |
| `user_actions` `funnel_bot_start` `bind:*` | **0 rows (all time)** |
| `user_actions` `web_tg_bind` | **0 rows (all time)** |
| Container logs | No `merge_web` / bind success / `both_have_keys` lines |

Owner reported bind completed twice; **AMS DB and instrumentation show no bind attempt ever hit the bot process.**

---

## 2.1 Fresh retest — p1bind2- (2026-06-09)

Controlled prepare at ~15:46 UTC; owner reported bind completed; AMS verify immediately after.

| Check | Result |
|-------|--------|
| Email prefix | **`p1bind2-`** (`p1bind2-1781019986458956739@bendervpn-smoke.invalid`) |
| Token prefix | `6f90a8****` (still present — not consumed) |
| Token expiry at verify | **Not expired** (`2026-06-10T15:46:26Z`) |
| Smoke verify | `NOT_BOUND` · `P1_BIND_VERIFY_PENDING` |
| `funnel_bot_start` `bind:*` (all time) | **0** |
| `funnel_bot_start` after prepare | **0** |
| `web_tg_bind` | **0** |
| Owner bot response | **Not provided** to operator |

**Same failure mode as `p1bind-`:** bind deep link did not produce recorded `/start bind_*` on prod bot. **Do not patch migration code** until bot entry is proven with owner-supplied success/conflict message + non-zero funnel row.

---

## 3. Code path map

### 3.1 Link generation

| Step | Location | Behavior |
|------|----------|----------|
| Web trial API | `bot_src/portal_web_trial.py` | After provision → `ensure_bind_token(web_uid)` |
| Token create | `bot_src/web_trial_db.py` | `secrets.token_hex(16)` · **24h** expiry in `bind_token_expires_at` |
| URL | `bot_src/config.py` `telegram_bind_url()` | `https://t.me/{TELEGRAM_BOT_USERNAME}?start=bind_{token}` |
| Default username | `TELEGRAM_BOT_USERNAME` env or **`Bender_KVN_bot`** |
| Portal UI | `web/portal/assets/setup.js` | `renderBindTelegram()` sets `#btn-bind-tg.href = extra.bind_url`; copies to `localStorage.bvpn_bind_url` |

**Exact deep-link format:** `https://t.me/Bender_KVN_bot?start=bind_<32-char-hex>` (username from env on AMS: `Ben***` — consistent with `Bender_KVN_bot`).

### 3.2 `/start` routing

| Step | Location | Behavior |
|------|----------|----------|
| Entry | `bot_src/bot/handlers.py` `start_handler` | Parses `message.text` after first space |
| Payload | `start_arg.startswith("bind_")` | `bind_token = start_arg[5:]` — expects **`bind_<token>`**, not raw token |
| Instrumentation | Same handler, **before** terms check | `log_action(user_id, "funnel_bot_start", "bind:***")` when bind_token set |
| Terms gate | If `agreed_to_terms` false | `pending_web_bind` stored in FSM; bind applied after `agree_to_terms` |
| Terms OK | If `agreed_to_terms` true | `_apply_web_bind(message, bind_token)` immediately |

**Critical:** Any successful delivery of `/start bind_<token>` to the bot **must** insert `funnel_bot_start` with `meta='bind:***'` (or legacy ref meta). **Zero such rows ⇒ update never arrived.**

### 3.3 Bind handler

| Step | Location | Behavior |
|------|----------|----------|
| Handler | `bot_src/web_tg_bind.py` `bind_web_account_by_token()` | Lookup claim by token (lowercased) |
| Token lookup | `get_claim_by_bind_token()` | Rejects if missing, len &lt; 16, or **expired** |
| Merge | `merge_web_user_to_telegram()` | Moves keys, balance, `referred_by`, `referrals` row |
| Conflicts | `both_have_keys`, `already_bound_other`, `not_found` | Returns error dict — **still would have funnel row** |
| Success log | `handlers._apply_web_bind` | `log_action(user_id, "web_tg_bind", customer_id)` **only on ok** |

### 3.4 DB writes on success

| Field | Writer |
|-------|--------|
| `web_trial_claims.telegram_id`, `bound_at` | `mark_web_claim_bound()` — sets `bind_token = NULL` |
| `users` merge / surrogate delete | `merge_web_user_to_telegram()` |
| `referrals.referred_user_id` | Updated web surrogate → TG id in merge |

### 3.5 User-facing bot messages

| Outcome | Message key |
|---------|-------------|
| Success | `MSG_WEB_BIND_OK` — «Аккаунт привязан к Telegram» + customer ID |
| Already bound same TG | `MSG_WEB_BIND_ALREADY` |
| Invalid / expired token | `MSG_WEB_BIND_INVALID` |
| Both sides have keys | `MSG_WEB_BIND_CONFLICT` + customer ID |
| Bound to other TG | `MSG_WEB_BIND_OTHER_TG` |

**Silent no-op paths:** Only if `/start` never runs with `bind_` payload, or bot process not receiving updates (ruled out — see §4).

---

## 4. Prod AMS read-only findings

**Target:** AMS `168.100.11.140` · container `remna-shop-bot` · read-only

### 4.1 Deployed code

| File | Status |
|------|--------|
| `/app/src/shop_bot/web_tg_bind.py` | Present · `bind_web_account_by_token` |
| `/app/src/shop_bot/bot/handlers.py` | Present · `bind_` routing (not `/app/src/shop_bot/handlers.py`) |
| `/app/src/shop_bot/config.py` | `telegram_bind_url` present |
| `/app/src/shop_bot/web_trial_db.py` | `bind_token_expires_at` present |

Container **running** since deploy restart `2026-06-09T13:25:25Z`.

### 4.2 Update delivery

| Check | Result |
|-------|--------|
| Mode | **`dp.start_polling(bot)`** in `main.py` — not Telegram webhook |
| Flask | Port **1488** for YooKassa / portal-web-trial only |
| Polling started | Log: `Bot polling started` after each restart |
| Other bot traffic | `funnel_bot_start` with ref codes on **2026-06-09 08:07–08:08 UTC** — bot **is receiving updates** |
| Bind-specific logs | **None** in docker logs sample |

### 4.3 DB state — `p1bind-` trial

| Field | Value (redacted) |
|-------|------------------|
| Email prefix | `p1bind-17810***@bendervpn-smoke.invalid` |
| `web_user_id` | Negative surrogate (smoke) |
| `bind_token` | Prefix `ef549b****` — **still set** (not consumed) |
| `bind_token_expires_at` | `2026-06-10T14:18:19Z` — **not expired** at audit |
| `claimed_at` | `2026-06-09T14:18:19Z` |
| `telegram_id` / `bound_at` | **NULL** |
| Web `referred_by` | Prefix `jHGK****` (ref code string) |
| Web keys | **1** |
| `referrals` on web uid | Row exists — **not migrated** |

### 4.4 Global instrumentation

| Query | Count |
|-------|-------|
| `funnel_bot_start` WHERE `meta LIKE 'bind:%'` | **0** |
| `web_tg_bind` | **0** |

**Interpretation:** No Telegram account has ever completed the bind deep-link entry path on this AMS shop DB (or success was never logged). Conflict / invalid-token attempts would still leave `funnel_bot_start bind:***` — absent.

### 4.5 Owner / test account (from logs only)

Owner/admin TG activity in `user_actions` shows normal bot use (`funnel_bot_start` empty meta on 2026-06-05) — **no bind funnel meta**. Cannot prove which account owner used for bind attempt; even main account with existing keys would still log `bind:***` if link opened.

---

## 5. Verifier / helper review

**Script:** `ops/smoke_p1_ref_tg_bind_ams.py` (local, not on origin)

| Aspect | Assessment |
|--------|------------|
| DB target | Correct — `/app/data/shop_bot.db` via `docker exec` |
| Email prefix search | Correct |
| `referred_by` expectation | Ref **code string** — matches implementation |
| Negative web surrogate IDs | Handled via `int(web_uid_s)` |
| Verify mode | Read-only — no writes |
| Secrets in output | Reads `PORTAL_WEB_TRIAL_SECRET` for prepare only; verify does not print it |
| **Gaps** | `NOT_BOUND` lumps **NOT_OPENED**, **TOKEN_EXPIRED**, **CONFLICT**, and **MIGRATION_FAIL**; does not check `bind_token_expires_at`; does not query global `funnel_bot_start bind:%`; does not verify bot username on URL vs AMS env |

**Recommended helper improvements (later, optional):**

- On `NOT_BOUND`, also report: token present/expired, global bind funnel count, suggested classification (`LIKELY_NOT_OPENED` vs `TOKEN_INVALID` vs `NEEDS_CONFLICT_CHECK`).
- Do not print full `BIND_URL` in prepare output to owner chat logs (prefix only).

---

## 6. Root cause decision matrix

| Hypothesis | Evidence for | Evidence against | Confidence | Next safe test |
|------------|--------------|------------------|------------|----------------|
| **Link not opened in Telegram app** | Zero `funnel_bot_start bind:*`; token unconsumed; owner “done” vs DB | — | **High** | Fresh `p1bind2-` · open in **Telegram app** · screenshot bot reply |
| Wrong bot username | AMS env `Ben***` matches code default | — | **Low** | Compare `bind_url` host to env username on prepare |
| Stale / expired token | — | Expires **2026-06-10T14:18Z**; token still in DB | **Low** | Re-prepare if past expiry |
| Token already consumed | — | `bind_token` still non-NULL | **Low** | N/A for current trial |
| Handler payload mismatch | Code expects `bind_<token>`; URL uses same | — | **Low** | Log `/start` payload in retest (support read-only) |
| Prod bot not receiving updates | Ref `funnel_bot_start` same day | — | **Low** | Already disproved |
| Prod bot code mismatch | Bind handlers present in container | — | **Low** | N/A |
| Conflict (existing TG keys) | Owner account likely has keys | Would still log `funnel_bot_start bind:***` | **Low** as *primary* cause | Clean TG account retest |
| Logging gap | — | `log_action` runs unconditionally on bind `/start` before bind result | **Very low** | N/A |
| Verifier mismatch | — | Claim/token queries consistent with manual SQL | **Very low** | Extend verifier labels |
| **Migration bug** | — | Bind never entered handler; no merge attempted | **Very low** | Only after proven bot entry + failure |

---

## 7. Fresh bind retest plan (do not run until owner ready)

### 7.1 Prepare (Cursor / AMS)

```bash
# On AMS — after uploading helper to /tmp if needed
python3 /tmp/smoke_p1_ref_tg_bind_ams.py prepare
# Edit prepare to use email prefix p1bind2- OR run once and note new p1bind-* email
```

Recommended: extend prepare to accept `--email-prefix p1bind2-` (future helper tweak). For now, note generated email prefix from output.

Record: email prefix, `bind_token` prefix only, approximate UTC prepare time.

### 7.2 Owner steps (mandatory)

1. Use a **clean Telegram account** — **no existing VPN keys** in bot; no conflicting `referred_by` unless accepting PARTIAL PASS.
2. Open bind link **inside Telegram app** (long-press → Open in Telegram, or tap from mobile TG) — **not** browser-only preview.
3. If bot shows terms — tap **«Принимаю»**; bind runs after accept (or immediately if returning user).
4. **Copy exact bot message** (success / conflict / invalid) or screenshot.
5. Record approximate **UTC timestamp** of attempt.
6. **Do not** share full token in docs/chat.

### 7.3 Verify (AMS, after owner confirms bot message)

If owner saw **success** message (`MSG_WEB_BIND_OK`):

```bash
python3 /tmp/smoke_p1_ref_tg_bind_ams.py verify --email-prefix p1bind2-
# or p1bind- if reusing same trial
```

Expect: `P1_BIND_VERIFY_OK`, web surrogate deleted, referrals migrated.

If owner saw **conflict** or **invalid** — **do not** call PASS; classify from bot text; inspect `funnel_bot_start bind:***` (should be ≥1) and logs around timestamp.

If owner saw **no bot response** — classify as NOT_OPENED / wrong bot; inspect polling logs only.

---

## 8. No-go before next referral development

| Blocker | Status |
|---------|--------|
| POSTDEPLOY §9 TG bind PASS | **Open** |
| G2-A bind migration verified | **Blocked** |
| P1-REF-002 (hidden +3d bonus) | **Blocked** until G2-A bind PASS or explicit owner risk waiver documented |
| P1-CAB-001 | **Not blocked by bind** — can proceed in parallel after owner prioritizes |
| Portal copy / guide UI | **Blocked for bind-related claims** only |

---

## 9. Recommended fixes (after root cause confirmed — not this pass)

| If root cause confirmed | Fix surface |
|-------------------------|-------------|
| NOT_OPENED | Setup copy: “Open **in Telegram app**”; optional QR to t.me link; journey QA scenario |
| Conflict | Document clean-account requirement in POSTDEPLOY; optional admin merge runbook |
| Token expiry | Surface expiry in setup UI; refresh bind link button |
| Verifier ambiguity | Extend smoke helper status codes |
| Migration bug (only if bot entry proven) | Patch `web_tg_bind.py` / handlers — separate change |

---

## 10. Cross-reference — prior audit preserved

Device UI, multi-device policy, balance/legacy bypass findings remain in [`AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md`](AUDIT-2026-06-10-DEVICE-LINKS-BALANCE-UX.md). This document **only** deepens the Telegram bind entry-path analysis.

---

## 11. Skills / rules applied

| Source | How it affected this audit |
|--------|----------------------------|
| `bendervpn-guardrails.mdc` | No prod/deploy/billing changes; no live claims without evidence; narrow docs-only scope |
| `bendervpn-journey-qa/SKILL.md` | Bind treated as Telegram journey step; code inspection + AMS read-only, not claimed browser-verified |
| `bendervpn-repo-workflow.mdc` | SSH read-only AMS; no secrets printed |
| `sequential-backlog.mdc` | Stopped after audit/docs — no next Q started |
| User prompt constraints | No Semgrep, no push, no `.cursor` commit, preserve DEVICE-LINKS doc |
