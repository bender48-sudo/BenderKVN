# Database migrations (shop_bot SQLite)

Schema changes run through `bot_src/schema_migrations.py` on `initialize_db()`.

## Version chain

| Version | Change |
|---------|--------|
| **v1** | Indexes: `vpn_keys(user_id)`, `vpn_keys(expiry_date)`, `referrals(referrer_code)`, `user_actions(user_id)`, web trial `bind_token` |
| **v2** | `support_rate_limits` table; idempotent `ALTER` for legacy user/web_trial columns; `renewal_attempts` index |
| **v3** | `web_trial_claims.customer_seq` + index for `BVPN-` lookup |

Current target: **v3** (`SCHEMA_VERSION` in `schema_migrations.py`).

## Operations

- Fresh DB: `initialize_db()` creates tables, then migrations run 0 → v3.
- Existing prod DB: migrations apply only missing steps (transaction per version).
- Do not add silent `except OperationalError: pass` for new columns — extend `_migrate_vN()` instead.

## Verify

```bash
python -m py_compile bot_src/schema_migrations.py bot_src/database.py
```

After deploy, optional on AMS: `EXPLAIN QUERY PLAN` for `get_user_keys`, `count_referrals`, `get_claim_by_customer_id`.
