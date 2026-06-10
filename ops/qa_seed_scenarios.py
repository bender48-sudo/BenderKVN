#!/usr/bin/env python3
"""QA scenario DB seed/reset for customer journey matrix (QA-DB-SEED-001).

Seeds realistic states into an isolated staging/local/test SQLite DB.
Requires BVPN_ENV non-production + BVPN_QA_TOOLS_ENABLED=1.
Never targets production DB paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"

QA_TG_ID_MIN = 900_000_001
QA_TG_ID_MAX = 900_000_099
QA_REF_INVITER_CODE = "QA_REF_INVITER"
QA_EMAIL_DOMAIN = "sandbox.invalid"
_MANIFEST_PATH = ROOT / "ops" / "qa_scenario_manifest.json"

_NOW = datetime.now(timezone.utc)


def _bootstrap_shop_bot() -> None:
    if str(BOT) not in sys.path:
        sys.path.insert(0, str(BOT))
    import types

    if "shop_bot" not in sys.modules:
        pkg = types.ModuleType("shop_bot")
        pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
        sys.modules["shop_bot"] = pkg
    if "shop_bot.data_manager" not in sys.modules:
        dm = types.ModuleType("shop_bot.data_manager")
        sys.modules["shop_bot.data_manager"] = dm
        sys.modules["shop_bot"].data_manager = dm
    if "shop_bot.data_manager.database" not in sys.modules:
        import importlib

        database = importlib.import_module("database")
        sys.modules["shop_bot.data_manager.database"] = database
        sys.modules["shop_bot.data_manager"].database = database
    if "shop_bot.schema_migrations" not in sys.modules:
        import importlib

        schema_migrations = importlib.import_module("schema_migrations")
        sys.modules["shop_bot.schema_migrations"] = schema_migrations


def _ensure_guards(db_path: Path) -> Path:
    _bootstrap_shop_bot()
    from shop_bot.runtime_env import (
        assert_db_path_allowed_for_qa,
        require_non_production,
        require_qa_tooling_enabled,
    )

    require_non_production("qa_seed_scenarios")
    require_qa_tooling_enabled("qa_seed_scenarios")
    resolved = db_path.expanduser().resolve()
    assert_db_path_allowed_for_qa(resolved, "qa_seed_scenarios")
    return resolved


def _qa_email(scenario: str) -> str:
    slug = scenario.replace("_", "-")
    return f"qa+{slug}@{QA_EMAIL_DOMAIN}"


def _qa_phone(seq: int) -> str:
    return f"+7999000{seq:04d}"


def _qa_uuid(seed: str) -> str:
    digest = hashlib.sha256(f"qa-seed:{seed}".encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def _iso_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expiry(days: float) -> str:
    return _iso_dt(_NOW + timedelta(days=days))


@dataclass
class ScenarioManifest:
    name: str
    support: str  # full | partial | blocked
    tg_user_id: int | None = None
    username: str | None = None
    email: str | None = None
    phone: str | None = None
    ref_code: str | None = None
    referred_by: str | None = None
    expected_user_status: str = ""
    expected_cabinet_state: str = ""
    expected_bot_behavior: str = ""
    config_mode: str = "none"  # none | dummy_dry_run | dummy_expired
    notes: str = ""
    blocked_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _SeedCtx:
    conn: sqlite3.Connection
    manifest: list[ScenarioManifest] = field(default_factory=list)


def _upsert_user(
    conn: sqlite3.Connection,
    *,
    telegram_id: int,
    username: str,
    agreed_to_terms: int = 0,
    trial_used: int = 0,
    balance: float = 0.0,
    ref_code: str | None = None,
    referred_by: str | None = None,
    total_spent: float = 0.0,
) -> None:
    conn.execute(
        """
        INSERT INTO users (
            telegram_id, username, agreed_to_terms, trial_used, balance,
            ref_code, referred_by, total_spent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            agreed_to_terms = excluded.agreed_to_terms,
            trial_used = excluded.trial_used,
            balance = excluded.balance,
            ref_code = excluded.ref_code,
            referred_by = excluded.referred_by,
            total_spent = excluded.total_spent
        """,
        (
            telegram_id,
            username,
            agreed_to_terms,
            trial_used,
            balance,
            ref_code,
            referred_by,
            total_spent,
        ),
    )


def _insert_key(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    key_email: str,
    expiry_days: float,
    seed: str,
) -> None:
    conn.execute(
        """
        INSERT INTO vpn_keys (user_id, vless_uuid, key_email, expiry_date, created_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            _qa_uuid(seed),
            key_email,
            _expiry(expiry_days),
            _NOW.replace(tzinfo=None),
        ),
    )


def _insert_web_claim(
    conn: sqlite3.Connection,
    *,
    contact_email: str,
    web_user_id: int,
    panel_email: str,
    contact_phone: str | None = None,
    telegram_id: int | None = None,
    claimed_at: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO web_trial_claims (
            contact_email, web_user_id, panel_email, contact_phone,
            claimed_at, telegram_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(contact_email) DO UPDATE SET
            web_user_id = excluded.web_user_id,
            panel_email = excluded.panel_email,
            contact_phone = excluded.contact_phone,
            claimed_at = excluded.claimed_at,
            telegram_id = excluded.telegram_id
        """,
        (
            contact_email,
            web_user_id,
            panel_email,
            contact_phone,
            claimed_at or _iso_dt(_NOW),
            telegram_id,
        ),
    )


def _log_action(conn: sqlite3.Connection, user_id: int, action: str) -> None:
    conn.execute(
        "INSERT INTO user_actions (user_id, action) VALUES (?, ?)",
        (user_id, action),
    )


def _link_referral(conn: sqlite3.Connection, referrer_code: str, referred_user_id: int) -> None:
    conn.execute(
        "INSERT INTO referrals (referrer_code, referred_user_id) VALUES (?, ?)",
        (referrer_code, referred_user_id),
    )


def _blocked(name: str, reason: str) -> Callable[[_SeedCtx], None]:
    def _seed(ctx: _SeedCtx) -> None:
        ctx.manifest.append(
            ScenarioManifest(
                name=name,
                support="blocked",
                blocked_reason=reason,
                expected_user_status="not_seeded",
                expected_cabinet_state="requires ACQ gate fixture",
                expected_bot_behavior="not_seeded",
                notes=reason,
            )
        )

    return _seed


def _seed_new_no_referral(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_new_no_referral",
        agreed_to_terms=0,
        trial_used=0,
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="new_no_referral",
            support="full",
            tg_user_id=tid,
            username="qa_new_no_referral",
            expected_user_status="registered, terms not accepted, trial unused",
            expected_cabinet_state="terms_required",
            expected_bot_behavior="/start → terms prompt",
            config_mode="none",
        )
    )


def _seed_new_from_referral(ctx: _SeedCtx) -> None:
    inviter_tid = QA_TG_ID_MIN + 16
    invitee_tid = QA_TG_ID_MIN + 1
    _upsert_user(
        ctx.conn,
        telegram_id=inviter_tid,
        username="qa_referral_inviter",
        agreed_to_terms=1,
        ref_code=QA_REF_INVITER_CODE,
    )
    _upsert_user(
        ctx.conn,
        telegram_id=invitee_tid,
        username="qa_new_from_referral",
        agreed_to_terms=0,
        referred_by=QA_REF_INVITER_CODE,
    )
    _link_referral(ctx.conn, QA_REF_INVITER_CODE, invitee_tid)
    ctx.manifest.append(
        ScenarioManifest(
            name="new_from_referral",
            support="full",
            tg_user_id=invitee_tid,
            username="qa_new_from_referral",
            referred_by=QA_REF_INVITER_CODE,
            expected_user_status="new user with referred_by set",
            expected_cabinet_state="terms_required until /start",
            expected_bot_behavior="portal ?ref=QA_REF_INVITER then bot /start ref_*",
            config_mode="none",
            notes=f"inviter tg_id={inviter_tid} ref={QA_REF_INVITER_CODE}",
        )
    )


def _seed_existing_tg_user(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 2
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_existing_tg_user",
        agreed_to_terms=1,
        trial_used=1,
        balance=40.0,
    )
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=25,
        seed=f"existing-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="existing_tg_user",
            support="full",
            tg_user_id=tid,
            username="qa_existing_tg_user",
            expected_user_status="active returning bot user",
            expected_cabinet_state="ok with balance and active config",
            expected_bot_behavior="main menu available",
            config_mode="dummy_dry_run",
        )
    )


def _seed_web_lead_without_tg_bind(ctx: _SeedCtx) -> None:
    from shop_bot.data_manager.database import web_user_id_from_email

    email = _qa_email("web-lead-unbound")
    web_uid = web_user_id_from_email(email)
    _upsert_user(
        ctx.conn,
        telegram_id=web_uid,
        username="qa_web_lead_unbound",
        agreed_to_terms=0,
        trial_used=1,
    )
    _insert_web_claim(
        ctx.conn,
        contact_email=email,
        web_user_id=web_uid,
        panel_email=f"qa-web-lead@{QA_EMAIL_DOMAIN}",
        contact_phone=_qa_phone(4),
    )
    _insert_key(
        ctx.conn,
        user_id=web_uid,
        key_email=f"web{abs(web_uid)}-key1-trial@{QA_EMAIL_DOMAIN}",
        expiry_days=0.5,
        seed="web-lead-unbound",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="web_lead_without_tg_bind",
            support="full",
            tg_user_id=web_uid,
            username="qa_web_lead_unbound",
            email=email,
            phone=_qa_phone(4),
            expected_user_status="web-only surrogate, trial claimed",
            expected_cabinet_state="ok, needs_telegram_bind=true",
            expected_bot_behavior="portal setup/cabinet by email",
            config_mode="dummy_dry_run",
        )
    )


def _seed_trial_eligible_before_cap(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 4
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_trial_eligible",
        agreed_to_terms=1,
        trial_used=0,
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="trial_eligible_before_cap",
            support="partial",
            tg_user_id=tid,
            username="qa_trial_eligible",
            expected_user_status="trial_used=0, eligible in bot",
            expected_cabinet_state="ok, no config until trial issued",
            expected_bot_behavior="trial CTA available in bot",
            config_mode="none",
            notes="Trial cap gate (ACQ-TRIAL-CAP-001) not in DB — use portal fixture when available",
        )
    )


def _seed_temporary_1d_active(ctx: _SeedCtx) -> None:
    from shop_bot.data_manager.database import web_user_id_from_email

    email = _qa_email("temp-1d-active")
    web_uid = web_user_id_from_email(email)
    _upsert_user(
        ctx.conn,
        telegram_id=web_uid,
        username="qa_temp_1d_active",
        agreed_to_terms=0,
        trial_used=1,
    )
    _insert_web_claim(
        ctx.conn,
        contact_email=email,
        web_user_id=web_uid,
        panel_email=f"qa-temp-active@{QA_EMAIL_DOMAIN}",
        contact_phone=_qa_phone(7),
    )
    _insert_key(
        ctx.conn,
        user_id=web_uid,
        key_email=f"web{abs(web_uid)}-key1-trial@{QA_EMAIL_DOMAIN}",
        expiry_days=0.8,
        seed="temp-1d-active",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="temporary_1d_active",
            support="full",
            tg_user_id=web_uid,
            email=email,
            username="qa_temp_1d_active",
            expected_user_status="web temp access active (~1d)",
            expected_cabinet_state="ok with active trial config",
            expected_bot_behavior="portal cabinet by email",
            config_mode="dummy_dry_run",
        )
    )


def _seed_temporary_1d_expired(ctx: _SeedCtx) -> None:
    from shop_bot.data_manager.database import web_user_id_from_email

    email = _qa_email("temp-1d-expired")
    web_uid = web_user_id_from_email(email)
    _upsert_user(
        ctx.conn,
        telegram_id=web_uid,
        username="qa_temp_1d_expired",
        agreed_to_terms=0,
        trial_used=1,
    )
    _insert_web_claim(
        ctx.conn,
        contact_email=email,
        web_user_id=web_uid,
        panel_email=f"qa-temp-expired@{QA_EMAIL_DOMAIN}",
        contact_phone=_qa_phone(8),
    )
    _insert_key(
        ctx.conn,
        user_id=web_uid,
        key_email=f"web{abs(web_uid)}-key1-trial@{QA_EMAIL_DOMAIN}",
        expiry_days=-2,
        seed="temp-1d-expired",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="temporary_1d_expired",
            support="full",
            tg_user_id=web_uid,
            email=email,
            username="qa_temp_1d_expired",
            expected_user_status="web temp access expired",
            expected_cabinet_state="ok, expired configuration",
            expected_bot_behavior="portal pay/extend CTA",
            config_mode="dummy_expired",
        )
    )


def _seed_temporary_converted_to_paid(ctx: _SeedCtx) -> None:
    from shop_bot.data_manager.database import web_user_id_from_email

    email = _qa_email("temp-converted-paid")
    web_uid = web_user_id_from_email(email)
    _upsert_user(
        ctx.conn,
        telegram_id=web_uid,
        username="qa_temp_converted_paid",
        agreed_to_terms=0,
        trial_used=1,
        balance=120.0,
        total_spent=120.0,
    )
    _insert_web_claim(
        ctx.conn,
        contact_email=email,
        web_user_id=web_uid,
        panel_email=f"qa-temp-paid@{QA_EMAIL_DOMAIN}",
        contact_phone=_qa_phone(9),
    )
    _insert_key(
        ctx.conn,
        user_id=web_uid,
        key_email=f"web{abs(web_uid)}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=14,
        seed="temp-converted-paid",
    )
    _log_action(ctx.conn, web_uid, "topup")
    ctx.manifest.append(
        ScenarioManifest(
            name="temporary_converted_to_paid",
            support="partial",
            tg_user_id=web_uid,
            email=email,
            username="qa_temp_converted_paid",
            expected_user_status="post-conversion wallet state (seeded, not via webhook)",
            expected_cabinet_state="ok, wallet profile with active config",
            expected_bot_behavior="paid wallet UX on portal",
            config_mode="dummy_dry_run",
            notes="Payment webhook path (QA-PAYMENT-WEBHOOK-001) not simulated — balance seeded directly in QA DB",
        )
    )


def _seed_paid_wallet_user(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 9
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_paid_wallet_user",
        agreed_to_terms=1,
        trial_used=1,
        balance=200.0,
        total_spent=500.0,
    )
    _log_action(ctx.conn, tid, "topup")
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=20,
        seed=f"paid-wallet-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="paid_wallet_user",
            support="full",
            tg_user_id=tid,
            username="qa_paid_wallet_user",
            expected_user_status="wallet billing active",
            expected_cabinet_state="ok, billing_profile=wallet",
            expected_bot_behavior="top-up not required for near term",
            config_mode="dummy_dry_run",
        )
    )


def _seed_insufficient_balance_user(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 10
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_insufficient_balance",
        agreed_to_terms=1,
        trial_used=1,
        balance=3.0,
        total_spent=50.0,
    )
    _log_action(ctx.conn, tid, "topup")
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=5,
        seed=f"low-balance-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="insufficient_balance_user",
            support="full",
            tg_user_id=tid,
            username="qa_insufficient_balance",
            expected_user_status="balance below daily rate",
            expected_cabinet_state="ok, low days_left",
            expected_bot_behavior="top-up CTA / insufficient balance messaging",
            config_mode="dummy_dry_run",
        )
    )


def _seed_expired_stopped_user(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 11
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_expired_stopped",
        agreed_to_terms=1,
        trial_used=1,
        balance=0.0,
    )
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=-10,
        seed=f"expired-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="expired_stopped_user",
            support="full",
            tg_user_id=tid,
            username="qa_expired_stopped",
            expected_user_status="expired config, zero balance",
            expected_cabinet_state="ok, expired configuration",
            expected_bot_behavior="renew / top-up prompts",
            config_mode="dummy_expired",
        )
    )


def _seed_legacy_manual_user(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 12
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_legacy_manual",
        agreed_to_terms=1,
        trial_used=1,
        balance=0.0,
    )
    legacy_exp = datetime(2100, 6, 1, tzinfo=timezone.utc)
    ctx.conn.execute(
        """
        INSERT INTO vpn_keys (user_id, vless_uuid, key_email, expiry_date, created_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            tid,
            _qa_uuid(f"legacy-{tid}"),
            f"qa{tid}-legacy@{QA_EMAIL_DOMAIN}",
            legacy_exp.replace(tzinfo=None),
            _NOW.replace(tzinfo=None),
        ),
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="legacy_manual_user",
            support="full",
            tg_user_id=tid,
            username="qa_legacy_manual",
            expected_user_status="legacy panel expiry (2100)",
            expected_cabinet_state="ok, billing_profile=legacy",
            expected_bot_behavior="no daily balance debit",
            config_mode="dummy_dry_run",
        )
    )


def _seed_user_without_config(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 13
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_user_without_config",
        agreed_to_terms=1,
        trial_used=0,
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="user_without_config",
            support="full",
            tg_user_id=tid,
            username="qa_user_without_config",
            expected_user_status="terms accepted, no vpn_keys",
            expected_cabinet_state="ok, empty configurations",
            expected_bot_behavior="get setup / trial CTA",
            config_mode="none",
        )
    )


def _seed_user_one_active_config(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 14
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_user_one_config",
        agreed_to_terms=1,
        trial_used=1,
        balance=60.0,
    )
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=30,
        seed=f"one-config-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="user_one_active_config",
            support="full",
            tg_user_id=tid,
            username="qa_user_one_config",
            expected_user_status="single active configuration",
            expected_cabinet_state="ok, active_config_count=1",
            expected_bot_behavior="setup link for primary config",
            config_mode="dummy_dry_run",
        )
    )


def _seed_user_multiple_device_configs(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 15
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_user_multi_config",
        agreed_to_terms=1,
        trial_used=1,
        balance=80.0,
    )
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=20,
        seed=f"multi-a-{tid}",
    )
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key2@{QA_EMAIL_DOMAIN}",
        expiry_days=18,
        seed=f"multi-b-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="user_multiple_device_configs",
            support="full",
            tg_user_id=tid,
            username="qa_user_multi_config",
            expected_user_status="multiple active configs (anomaly)",
            expected_cabinet_state="ok, multiple_configs_anomaly=true",
            expected_bot_behavior="support-required messaging",
            config_mode="dummy_dry_run",
        )
    )


def _seed_referral_inviter_view(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 16
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_referral_inviter",
        agreed_to_terms=1,
        ref_code=QA_REF_INVITER_CODE,
        balance=30.0,
    )
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1@{QA_EMAIL_DOMAIN}",
        expiry_days=15,
        seed=f"inviter-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="referral_inviter_view",
            support="full",
            tg_user_id=tid,
            username="qa_referral_inviter",
            ref_code=QA_REF_INVITER_CODE,
            expected_user_status="inviter with QA_REF_INVITER",
            expected_cabinet_state="ok, referral stats via bot",
            expected_bot_behavior="invite link / referral count",
            config_mode="dummy_dry_run",
        )
    )


def _seed_referral_invitee_view(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 17
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_referral_invitee",
        agreed_to_terms=1,
        referred_by=QA_REF_INVITER_CODE,
        trial_used=1,
    )
    _link_referral(ctx.conn, QA_REF_INVITER_CODE, tid)
    _insert_key(
        ctx.conn,
        user_id=tid,
        key_email=f"qa{tid}-key1-trial@{QA_EMAIL_DOMAIN}",
        expiry_days=60,
        seed=f"invitee-{tid}",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="referral_invitee_view",
            support="full",
            tg_user_id=tid,
            username="qa_referral_invitee",
            referred_by=QA_REF_INVITER_CODE,
            expected_user_status="invitee with referred_by",
            expected_cabinet_state="ok, trial profile",
            expected_bot_behavior="portal ?ref= then cabinet",
            config_mode="dummy_dry_run",
        )
    )


def _seed_referrer_reward_not_live(ctx: _SeedCtx) -> None:
    tid = QA_TG_ID_MIN + 18
    _upsert_user(
        ctx.conn,
        telegram_id=tid,
        username="qa_referrer_reward_off",
        agreed_to_terms=1,
        ref_code="QA_REF_REWARD_OFF",
    )
    ctx.manifest.append(
        ScenarioManifest(
            name="referrer_reward_not_live",
            support="full",
            tg_user_id=tid,
            username="qa_referrer_reward_off",
            ref_code="QA_REF_REWARD_OFF",
            expected_user_status="referrer flags OFF in config",
            expected_cabinet_state="n/a — verify copy only",
            expected_bot_behavior="no hidden invitee +3d; REF-BONUS-001 deferred",
            config_mode="none",
            notes="REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED=0; REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_ENABLED=0",
        )
    )


SCENARIO_SEEDERS: dict[str, Callable[[_SeedCtx], None]] = {
    "new_no_referral": _seed_new_no_referral,
    "new_from_referral": _seed_new_from_referral,
    "new_referral": _seed_new_from_referral,
    "existing_tg_user": _seed_existing_tg_user,
    "web_lead_without_tg_bind": _seed_web_lead_without_tg_bind,
    "trial_eligible_before_cap": _seed_trial_eligible_before_cap,
    "after_trial_cap": _blocked(
        "after_trial_cap",
        "ACQ-TRIAL-CAP-001 gate not in schema — seed via portal fixture when implemented",
    ),
    "temporary_1d_active": _seed_temporary_1d_active,
    "temporary_1d_expired": _seed_temporary_1d_expired,
    "temporary_converted_to_paid": _seed_temporary_converted_to_paid,
    "paid_wallet_user": _seed_paid_wallet_user,
    "insufficient_balance_user": _seed_insufficient_balance_user,
    "expired_stopped_user": _seed_expired_stopped_user,
    "legacy_manual_user": _seed_legacy_manual_user,
    "user_without_config": _seed_user_without_config,
    "user_one_active_config": _seed_user_one_active_config,
    "user_multiple_device_configs": _seed_user_multiple_device_configs,
    "referral_inviter_view": _seed_referral_inviter_view,
    "referral_invitee_view": _seed_referral_invitee_view,
    "referrer_reward_not_live": _seed_referrer_reward_not_live,
    "slots_counter_states": _blocked(
        "slots_counter_states",
        "ACQ slot counter / gate API fixture table not in shop DB — QA-PORTAL-FIXTURES-001",
    ),
}

SCENARIO_ORDER = [
    "new_no_referral",
    "new_from_referral",
    "existing_tg_user",
    "web_lead_without_tg_bind",
    "trial_eligible_before_cap",
    "after_trial_cap",
    "temporary_1d_active",
    "temporary_1d_expired",
    "temporary_converted_to_paid",
    "paid_wallet_user",
    "insufficient_balance_user",
    "expired_stopped_user",
    "legacy_manual_user",
    "user_without_config",
    "user_one_active_config",
    "user_multiple_device_configs",
    "referral_inviter_view",
    "referral_invitee_view",
    "referrer_reward_not_live",
    "slots_counter_states",
]


def _qa_user_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        """
        SELECT telegram_id FROM users
        WHERE (telegram_id BETWEEN ? AND ?)
           OR ref_code LIKE 'QA_%'
           OR username LIKE 'qa_%'
        """,
        (QA_TG_ID_MIN, QA_TG_ID_MAX),
    ).fetchall()
    web_rows = conn.execute(
        """
        SELECT web_user_id FROM web_trial_claims
        WHERE contact_email LIKE ? OR contact_email LIKE ?
        """,
        (f"%@{QA_EMAIL_DOMAIN}", f"qa+%@{QA_EMAIL_DOMAIN}"),
    ).fetchall()
    ids = {int(r[0]) for r in rows}
    ids.update(int(r[0]) for r in web_rows)
    return sorted(ids)


def reset_qa_scenarios(conn: sqlite3.Connection) -> int:
    """Remove QA synthetic users and related rows only."""
    qa_ids = _qa_user_ids(conn)
    removed_users = 0
    if qa_ids:
        placeholders = ",".join("?" * len(qa_ids))
        conn.execute(
            f"DELETE FROM user_actions WHERE user_id IN ({placeholders})",
            qa_ids,
        )
        conn.execute(
            f"DELETE FROM renewal_attempts WHERE user_id IN ({placeholders})",
            qa_ids,
        )
        conn.execute(
            f"DELETE FROM vpn_keys WHERE user_id IN ({placeholders})",
            qa_ids,
        )
        conn.execute(
            f"DELETE FROM referrals WHERE referred_user_id IN ({placeholders})",
            qa_ids,
        )
        conn.execute(
            f"DELETE FROM referrals WHERE referrer_code LIKE 'QA_%'",
        )
        cur = conn.execute(
            f"DELETE FROM users WHERE telegram_id IN ({placeholders})",
            qa_ids,
        )
        removed_users = cur.rowcount
    conn.execute(
        "DELETE FROM web_trial_claims WHERE contact_email LIKE ? OR contact_email LIKE ?",
        (f"%@{QA_EMAIL_DOMAIN}", f"qa+%@{QA_EMAIL_DOMAIN}"),
    )
    conn.commit()
    return removed_users


def seed_scenario(conn: sqlite3.Connection, name: str) -> ScenarioManifest:
    key = name.strip().lower()
    if key not in SCENARIO_SEEDERS:
        raise ValueError(f"Unknown scenario {name!r}. Use --list for names.")
    ctx = _SeedCtx(conn=conn)
    SCENARIO_SEEDERS[key](ctx)
    conn.commit()
    if not ctx.manifest:
        raise RuntimeError(f"Scenario {name!r} produced no manifest entry")
    return ctx.manifest[-1]


def seed_all_scenarios(conn: sqlite3.Connection) -> list[ScenarioManifest]:
    manifest: list[ScenarioManifest] = []
    for name in SCENARIO_ORDER:
        entry = seed_scenario(conn, name)
        manifest.append(entry)
    return manifest


def write_manifest(manifest: list[ScenarioManifest], path: Path | None = None) -> Path:
    out = path or _MANIFEST_PATH
    payload = {
        "generated_at": _iso_dt(_NOW),
        "scenarios": [m.to_dict() for m in manifest],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def _apply_db_path(db_path: Path) -> None:
    import os

    os.environ["SHOP_BOT_DB_PATH"] = str(db_path)
    _bootstrap_shop_bot()
    from shop_bot.data_manager import database as dbmod

    dbmod.DB_FILE = db_path
    dbmod.DATA_DIR = db_path.parent


def _init_db(db_path: Path) -> sqlite3.Connection:
    _apply_db_path(db_path)
    from shop_bot.data_manager.database import initialize_db

    initialize_db()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_db_path(cli_db: str | None) -> Path:
    import os

    if cli_db:
        return Path(cli_db).expanduser().resolve()
    override = (os.getenv("SHOP_BOT_DB_PATH") or os.getenv("BVPN_QA_DB_PATH") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (ROOT / "data" / "shop_bot_qa.db").resolve()


def _print_summary(manifest: list[ScenarioManifest], db_path: Path, *, reset_count: int = 0) -> None:
    full = sum(1 for m in manifest if m.support == "full")
    partial = sum(1 for m in manifest if m.support == "partial")
    blocked = sum(1 for m in manifest if m.support == "blocked")
    print(f"QA seed target DB: {db_path}")
    if reset_count:
        print(f"QA reset removed {reset_count} synthetic user row(s)")
    print(f"Seeded {len(manifest)} scenario(s): full={full} partial={partial} blocked={blocked}")
    for entry in manifest:
        tid = entry.tg_user_id if entry.tg_user_id is not None else "-"
        print(
            f"  [{entry.support:7}] {entry.name:32} tg={tid} "
            f"config={entry.config_mode}"
        )


def list_scenarios() -> None:
    for name in SCENARIO_ORDER:
        fn = SCENARIO_SEEDERS[name]
        blocked = getattr(fn, "__name__", "") == "<lambda>" or name in (
            "after_trial_cap",
            "slots_counter_states",
        )
        status = "blocked" if blocked else "seedable"
        print(f"{name:32} {status}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA customer journey DB seed/reset")
    parser.add_argument("--db", help="SQLite path (default: SHOP_BOT_DB_PATH / data/shop_bot.db)")
    parser.add_argument("--reset", action="store_true", help="Remove QA synthetic users first")
    parser.add_argument("--seed", metavar="NAME", help="Seed one scenario by name")
    parser.add_argument("--seed-all", action="store_true", help="Seed full scenario matrix")
    parser.add_argument("--list", action="store_true", help="List scenario names")
    parser.add_argument("--manifest", help="Write manifest JSON path (default: ops/qa_scenario_manifest.json)")
    args = parser.parse_args(argv)

    if args.list:
        list_scenarios()
        return 0

    if not args.reset and not args.seed and not args.seed_all:
        parser.error("Specify --reset, --seed NAME, and/or --seed-all")

    db_path = _resolve_db_path(args.db)
    db_path = _ensure_guards(db_path)
    print(f"QA seed will write to: {db_path}")

    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = _init_db(db_path)
    reset_count = 0
    try:
        if args.reset:
            reset_count = reset_qa_scenarios(conn)
        manifest: list[ScenarioManifest] = []
        if args.seed_all:
            manifest = seed_all_scenarios(conn)
        elif args.seed:
            manifest = [seed_scenario(conn, args.seed)]
        if manifest:
            manifest_path = write_manifest(
                manifest,
                Path(args.manifest) if args.manifest else _MANIFEST_PATH,
            )
            print(f"Manifest written: {manifest_path}")
        _print_summary(manifest, db_path, reset_count=reset_count)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
