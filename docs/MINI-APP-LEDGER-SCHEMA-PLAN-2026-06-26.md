# Balance ledger (Phase B) + referral accrual — schema & migration plan

**Status:** PLAN ONLY. No schema change, no migration run, no balance mutation applied.
Branch/staging only; prod untouched; accrual stays **OFF** (`REFERRAL_REWARDS_ACTIVE` unset)
until owner OK. Ticket: `REF-LEDGER-001` (supersedes the dead `REF-BONUS-001` month-model).

Order (this doc covers steps 0–2; STOP for review before running the migration):
**0. reward-model fix → 1. ledger schema (v8) → 2. backfill plan → 3. accrual (idempotent) →
4. `/portal-referral` earned from ledger → 5. front.**

---

## 0. Reward model — fixed, contradiction removed

Canon (single source of truth, drives copy + accrual):

| Tier | Friend gets | Referrer/Partner gets |
|---|---|---|
| **Regular** | **+100 ₽** on registration | **+30 %** of friend's **first** top-up |
| **Partner** | +100 ₽ on registration | **+50 %** of first top-up **+ 10 %** of every later top-up |

- New display-driven constants already in `config.py` (added previous step):
  `REFERRAL_FRIEND_BONUS_RUB=100`, `REFERRAL_REFERRER_PCT=30`,
  `REFERRAL_PARTNER_FIRST_PCT=50`, `REFERRAL_PARTNER_RECURRING_PCT=10`,
  `REFERRAL_PARTNER_MIN_WITHDRAW_RUB=5000`, gate `referral_rewards_active()` (default OFF).
- **DELETE the dead month-model** from `config.py`:
  `REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_ENABLED`, `…_MONTHS`. Never implemented; contradicts
  canon (it said «+1 month to referrer»).
  - **Coupled change:** `ops/test_referral_invitee_bonus_gate.py` asserts both deleted names
    (lines ~45–47, 65–66, 72–73). Update that guard test in the same commit, or it breaks.
  - Docs referencing the month model (lower priority, follow-up): `ARCH-2026-06-10-*`,
    `BENDERVPN-PRODUCT-POLICY.md` row «Referrer reward».
- **Untouched:** the separate legacy invitee `+3d` bonus
  (`REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_*`, `referral_invitee_first_purchase_bonus_days()`)
  — still referenced by `handlers.py`, stays gated OFF as-is.

---

## 1. Ledger table — schema (migration v8)

`balance_ledger` is an **append-only journal alongside** the existing wallet. It does **not**
become the balance source: `users.balance` (REAL ₽) stays authoritative so the hot billing
path (`try_deduct_balance` / `add_balance`) is unchanged (§6 do-not-touch). Every money move
also appends one ledger row. Amounts are **kopeks (signed integers)** for exactness.

```sql
CREATE TABLE IF NOT EXISTS balance_ledger (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               INTEGER NOT NULL,
    kind                  TEXT    NOT NULL,   -- topup | daily_charge | referral_reward
                                              -- | partner_reward | fortune | adjustment
    amount_kopeks         INTEGER NOT NULL,   -- signed: + credit, - debit
    balance_after_kopeks  INTEGER,            -- wallet kopeks AFTER this row; NULL for backfill
    ref                   TEXT,               -- per-user-unique event id (idempotency); NULL = manual
    meta                  TEXT,               -- optional JSON audit ({"from_user":..,"pct":30})
    created_at_utc        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
-- Idempotency: at most ONE row per (user, event). Manual adjustments (ref NULL) are exempt.
CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_user_ref
    ON balance_ledger(user_id, ref) WHERE ref IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ledger_user_id ON balance_ledger(user_id, id DESC);
```

**Columns vs your spec:** `kind / amount_kopeks / balance_after / ref / created_at_utc` — kept
verbatim except `balance_after` → `balance_after_kopeks` (unit-explicit) and two **additions for
correctness**: `id` (PK) and `user_id` (the journal is multi-user); plus optional `meta` for
audit. ← please confirm these additions.

**`ref` conventions (this is the idempotency key):**

| kind | ref | unique scope = «one per…» |
|---|---|---|
| `topup` | YooKassa payment id (e.g. `yk:2f3a…`) | payment |
| `daily_charge` | `daily:YYYY-MM-DD` | user × UTC day |
| `referral_reward` | `ref_first:<invitee_id>` | referrer × invitee's first top-up |
| `referral_reward` (welcome) | `ref_welcome` (on invitee row) | invitee (once) |
| `partner_reward` | `pt_first:<invitee_id>` / `pt_recur:<payment_id>` | per event |
| `adjustment` | NULL | not idempotent (manual support correction) |

`_migrate_v8(conn)`: create table + 2 indexes; bump `SCHEMA_VERSION` 7→8; register in
`_MIGRATORS`. Pure additive (no `ALTER`, no data move) → safe & reversible (drop table).

---

## 2. Backfill plan (one-time, idempotent)

So `/portal-transactions` can switch to the ledger **without changing its response contract**
and without losing existing history, backfill `balance_ledger` from `user_actions`:

| user_actions row | → ledger | ref | amount |
|---|---|---|---|
| `action='topup'`, numeric meta | `topup` | `legacy:topup:<action_id>` | `+meta` |
| `action LIKE 'daily_balance:%'`, numeric meta | `daily_charge` | `daily:<DATE>` | `-meta` |
| meta `insufficient` / `waived_topup` | skip (not a money move) | — | — |
| idempotency rows `yk:` / `crypto:` | skip (dup of topup) | — | — |

- `balance_after_kopeks = NULL` for backfilled rows (historic running balance unknown; we do not
  reconstruct it — honest NULL beats a guessed number).
- `created_at_utc` copied from the source row (history preserved, newest-first ordering intact).
- Idempotent: stable `ref` + the unique index → re-running the backfill inserts nothing new.
- Runs once inside the v8 migration **or** as a separate `ops/` backfill script — see decision Q4.

**Then** `/portal-transactions` (`portal_balance.build_transactions` / `get_balance_ledger`) reads
`balance_ledger` instead of `user_actions`, mapping `kind → {type, sign, amount_rub, at_utc}`:
`topup→(+)`, `daily_charge→(−)`, `referral_reward/partner_reward→(+)`. Same JSON shape the
front already consumes; the only additive bit is a new `type` value for reward rows (one label in
`balance.js`, not a rewrite). ← confirm at Q3.

---

## 3. Accrual hooks (step 3 — built next, gated OFF)

All credits go through one idempotent primitive (atomic INSERT-OR-IGNORE ledger + balance bump
in a single transaction; returns False if the event was already rewarded):

```
credit_ledger(user_id, kind, amount_kopeks, ref, meta) -> bool
   BEGIN
     INSERT OR IGNORE balance_ledger(user_id, kind, amount_kopeks, ref, meta, balance_after_kopeks=?)
     if changes()==0: return False           # already rewarded for this event
     UPDATE users SET balance = balance + amount_kopeks/100 WHERE telegram_id = user_id
   COMMIT
```

- **Friend +100 ₽** — hook at referral link (`handlers.py` `referral_linked` / `link_referral`).
  ref=`ref_welcome` on the invitee. Anti-abuse: only after invitee agreed terms.
- **Referrer +30 % of first top-up** — hook in the top-up credit path (`handlers.py` ~`credit
  topup`): after crediting the invitee, if this is the invitee's **first** top-up (ledger count
  of invitee `topup` == 1) and `users.referred_by` set → credit referrer
  `round(amount*30%)`. ref=`ref_first:<invitee_id>` on the referrer.
- **Partner 50/10** — same primitive, `partner_reward`; **deferred** until a partner-approval
  system exists (no DB for it yet). Hook shape defined, not wired.
- **Gate:** every accrual is a no-op unless `referral_rewards_active()` is true (default OFF).
  Flipping it live = separate owner OK (touches balance → §6). Until then ledger still journals
  topups/daily (Phase B), referral credits = none, so `earned_rub` stays an honest 0.

## 4–5 (later, after this is approved)
`/portal-referral.earned_rub` = SUM(referrer's `referral_reward`+`partner_reward`)/100 (real, from
ledger); per-invitee «начислено» from the `ref_first:<invitee_id>` row. Then build both mockup
states.

---

## Decisions needed before I run the migration (STOP)

- **Q1.** OK to add `id` + `user_id` (and optional `meta`) to your 5-column spec? (needed for a
  multi-user journal + audit)
- **Q2.** Keep `users.balance` (REAL ₽) authoritative and treat ledger as a parallel journal
  (recommended, zero risk to billing path), vs. make ledger the balance source (Phase C, bigger,
  not now)?
- **Q3.** OK that referral rewards appear in `/portal-transactions` as a new additive `type`
  (one label added to `balance.js`), keeping the JSON contract?
- **Q4.** Backfill **inside** the v8 migration, or as a **separate idempotent `ops/` script**
  run explicitly on staging first? (I lean separate script — safer, re-runnable, observable.)
```
