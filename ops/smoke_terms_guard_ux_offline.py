#!/usr/bin/env python3
"""Offline terms-guard UX smoke (QA DB + handler harness).

Simulates Telegram callbacks without Telegram API, YooKassa charges, or Remna
provisioning. Use before owner live taps; complements structural AST tests.

LIVE-TERMS-UX-SMOKE offline matrix — does NOT replace owner Telegram smoke.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "ops") not in sys.path:
    sys.path.insert(0, str(ROOT / "ops"))

from qa_bot_fake_tg import (  # noqa: E402
    CapturingBot,
    CapturingCallback,
    CapturingMessage,
    SCENARIO_TG_ID,
    _apply_db_path,
    _bootstrap_shop_bot,
    _ensure_guards,
    _make_fsm_context,
    _CaptureSink,
)

TERMS_MARKERS = ("Принимаю", "Условиями использования", "Политикой конфиденциальности")


@dataclass
class CaseResult:
    case_id: str
    label: str
    passed: bool
    detail: str
    terms_prompt: bool
    side_effect_blocked: bool


def _has_terms_prompt(sink: _CaptureSink) -> bool:
    for msg in sink.outbound:
        text = msg.text or ""
        if any(m in text for m in TERMS_MARKERS):
            return True
    return False


def _default_db() -> Path:
    return (ROOT / "data" / "shop_bot_qa_terms_smoke.db").resolve()


async def _invoke_callback(
    tg_id: int,
    username: str,
    callback_data: str,
    *,
    side_effect_tracker: dict[str, bool],
) -> _CaptureSink:
    _bootstrap_shop_bot()
    from shop_bot.bot import handlers

    sink = _CaptureSink()
    bot = CapturingBot(sink)
    message = CapturingMessage(bot, tg_id, username, sink=sink)
    state = await _make_fsm_context(tg_id)
    cb = CapturingCallback(bot, message, callback_data, sink)

    fake_sub = "https://sandbox.invalid/sub/qa-terms-smoke"

    with (
        patch(
            "shop_bot.subscription_cache.get_subscription_url_cached",
            new=AsyncMock(return_value=fake_sub),
        ),
        patch(
            "shop_bot.subscription_resolve.resolve_subscription_url",
            new=AsyncMock(return_value=fake_sub),
        ),
        patch(
            "shop_bot.modules.remnawave_api.provision_key",
            new=AsyncMock(side_effect=_mark(side_effect_tracker, "remna_provision")),
        ),
        patch(
            "shop_bot.yookassa_autopay.create_bind_payment",
            side_effect=_mark(side_effect_tracker, "bind_payment"),
        ),
    ):
        if callback_data == "get_trial":
            await handlers.trial_period_handler(cb, state)
        elif callback_data == "show_topup":
            await handlers.show_topup_handler(cb, state)
        elif callback_data == "toggle_autorenew":
            await handlers.toggle_autorenew_handler(cb, state)
        elif callback_data == "enter_promo_start":
            await handlers.enter_promo_start(cb, state)
        elif callback_data == "connect_vpn":
            await handlers.connect_vpn_wizard_start(cb, state)
        elif callback_data.startswith("wizard_pick_"):
            await handlers.connect_vpn_wizard_device(cb, state)
        elif callback_data == "agree_to_terms":
            await handlers.agree_to_terms_handler(cb, state)
        else:
            raise ValueError(f"unsupported callback {callback_data!r}")

    return sink


def _mark(tracker: dict[str, bool], key: str):
    def _fn(*_a, **_k):
        tracker[key] = True
        raise RuntimeError(f"blocked side effect: {key}")

    return _fn


async def _user_flags(tg_id: int) -> dict[str, int | None]:
    from shop_bot.data_manager.database import get_user, get_user_keys

    user = get_user(tg_id) or {}
    keys = get_user_keys(tg_id) or []
    return {
        "agreed_to_terms": int(user.get("agreed_to_terms") or 0),
        "trial_used": int(user.get("trial_used") or 0),
        "key_count": len(keys),
    }


async def run_matrix(db_path: Path) -> list[CaseResult]:
    _ensure_guards(db_path)

    import qa_seed_scenarios as seed

    conn = seed._init_db(db_path)
    seed.seed_scenario(conn, "new_no_referral")
    _apply_db_path(db_path)
    tg_id = SCENARIO_TG_ID["new_no_referral"]
    username = "qa_new_no_referral"
    results: list[CaseResult] = []

    unaccepted_cases = (
        ("CASE-1", "Unaccepted: get_trial", "get_trial"),
        ("CASE-2", "Unaccepted: show_topup", "show_topup"),
        ("CASE-3", "Unaccepted: toggle_autorenew enable", "toggle_autorenew"),
        ("CASE-4", "Unaccepted: enter_promo_start", "enter_promo_start"),
        ("CASE-5a", "Unaccepted: connect_vpn wizard", "connect_vpn"),
        ("CASE-5b", "Unaccepted: wizard_pick step", "wizard_pick_android"),
    )

    for case_id, label, cb_data in unaccepted_cases:
        tracker: dict[str, bool] = {}
        before = await _user_flags(tg_id)
        sink = await _invoke_callback(tg_id, username, cb_data, side_effect_tracker=tracker)
        after = await _user_flags(tg_id)
        terms = _has_terms_prompt(sink)
        blocked = not tracker
        unchanged = before == after
        passed = terms and blocked and unchanged
        detail = f"terms_prompt={terms} side_effects={list(tracker) or 'none'} db_unchanged={unchanged}"
        results.append(CaseResult(case_id, label, passed, detail, terms, blocked))

    # CASE-5 accepted pass-through: accept terms, then get_trial reaches trial path (Remna blocked)
    tracker = {}
    await _invoke_callback(tg_id, username, "agree_to_terms", side_effect_tracker=tracker)
    accepted = await _user_flags(tg_id)
    tracker.clear()
    sink = await _invoke_callback(tg_id, username, "get_trial", side_effect_tracker=tracker)
    terms_after_accept = _has_terms_prompt(sink)
    after_trial = await _user_flags(tg_id)
    remna_attempted = "remna_provision" in tracker
    passed5 = (
        accepted["agreed_to_terms"] == 1
        and not terms_after_accept
        and remna_attempted
        and after_trial["trial_used"] == 0
        and after_trial["key_count"] == 0
    )
    results.append(
        CaseResult(
            "CASE-5",
            "Accepted: agree then get_trial (stop before Remna persist)",
            passed5,
            f"agreed={accepted['agreed_to_terms']} terms_reprompt={terms_after_accept} "
            f"remna_attempted={remna_attempted} trial_used={after_trial['trial_used']}",
            terms_after_accept,
            after_trial["trial_used"] == 0,
        )
    )

    # CASE-6 disable autorenew without terms re-prompt — paid user with autopay on
    seed.seed_scenario(conn, "paid_wallet_user")
    _apply_db_path(db_path)
    from qa_bot_fake_tg import _normalize_vpn_key_expiry_for_handlers

    tg_paid = SCENARIO_TG_ID["paid_wallet_user"]
    _normalize_vpn_key_expiry_for_handlers(tg_paid)
    from shop_bot.data_manager.database import set_yookassa_autopay_enabled

    set_yookassa_autopay_enabled(tg_paid, True)
    tracker = {}
    sink = await _invoke_callback(
        tg_paid,
        "qa_paid_wallet_user",
        "toggle_autorenew",
        side_effect_tracker=tracker,
    )
    terms_on_disable = _has_terms_prompt(sink)
    passed6 = not terms_on_disable and "bind_payment" not in tracker
    results.append(
        CaseResult(
            "CASE-6",
            "Disable autorenew without terms re-prompt",
            passed6,
            f"terms_prompt={terms_on_disable} bind_payment={ 'bind_payment' in tracker}",
            terms_on_disable,
            "bind_payment" not in tracker,
        )
    )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline terms-guard UX smoke (QA DB)")
    parser.add_argument("--db", type=Path, default=_default_db(), help="QA SQLite path")
    args = parser.parse_args()

    db_path = args.db.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    results = asyncio.run(run_matrix(db_path))
    failed = [r for r in results if not r.passed]
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{r.case_id} {status} — {r.label}: {r.detail}")
    if failed:
        print(f"TERMS_GUARD_UX_OFFLINE_FAIL count={len(failed)}", file=sys.stderr)
        return 1
    print("TERMS_GUARD_UX_OFFLINE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
