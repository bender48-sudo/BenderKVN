#!/usr/bin/env python3
"""QA fake Telegram handler harness (QA-BOT-FAKE-TG-001).

Invokes real bot handlers with synthetic identities from QA seed DB.
Captures outbound messages/buttons locally — never calls Telegram send API.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
BOT = ROOT / "bot_src"
OPS = ROOT / "ops"

SCENARIO_TG_ID: dict[str, int] = {
    "new_no_referral": 900_000_001,
    "new_from_referral": 900_000_002,
    "existing_tg_user": 900_000_003,
    "trial_eligible_before_cap": 900_000_005,
    "paid_wallet_user": 900_000_010,
    "insufficient_balance_user": 900_000_011,
    "expired_stopped_user": 900_000_012,
    "legacy_manual_user": 900_000_013,
    "user_without_config": 900_000_014,
    "user_one_active_config": 900_000_015,
    "user_multiple_device_configs": 900_000_016,
    "referral_inviter_view": 900_000_017,
    "referral_invitee_view": 900_000_018,
    "referrer_reward_not_live": 900_000_019,
}

COVERED_SCENARIOS = tuple(SCENARIO_TG_ID.keys())

ACTIONS = (
    "start",
    "start_with_ref",
    "menu",
    "get_setup",
    "topup",
    "cabinet",
    "cabinet_link",
    "help",
    "status",
    "invite",
)

ACTION_NEXT_HINT: dict[str, str] = {
    "start": "If terms not accepted → tap «Принимаю»; else main menu",
    "start_with_ref": "Check referred_by linked; then terms or menu",
    "menu": "Use inline buttons from captured keyboard",
    "get_setup": "Open setup URL or start trial if no config",
    "topup": "Select preset amount (dry-run payment in QA)",
    "cabinet": "Read cabinet_snapshot fields",
    "cabinet_link": "Open Mini App URL with ?tid= (staging only)",
    "help": "Follow help submenu buttons",
    "status": "Review account balance / trial state",
    "invite": "Copy referral link from message",
}

SEED_SIMULATION_NOTE = (
    "Harness uses **seeded DB rows** (not empty DB). "
    "`new_no_referral` = user row exists, `agreed_to_terms=0` → /start shows terms flow. "
    "Use `--fresh-start` to delete the QA user row before `start` to simulate first contact."
)


@dataclass
class CapturedButton:
    label: str
    kind: str  # callback | url | web_app
    value: str


@dataclass
class CapturedOutbound:
    method: str
    text: str
    parse_mode: str | None = None
    buttons: list[CapturedButton] = field(default_factory=list)


@dataclass
class HarnessResult:
    scenario: str | None
    tg_user_id: int
    username: str
    action: str
    db_mode: str
    outbound: list[CapturedOutbound] = field(default_factory=list)
    cabinet_snapshot: dict[str, Any] | None = None
    cabinet_link: str | None = None
    expected_next: str = ""
    blocked_notes: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "outbound": [asdict(o) for o in self.outbound],
        }


def _bootstrap_shop_bot() -> None:
    if str(BOT) not in sys.path:
        sys.path.insert(0, str(BOT))
    if str(OPS) not in sys.path:
        sys.path.insert(0, str(OPS))
    import types

    if "shop_bot" not in sys.modules:
        pkg = types.ModuleType("shop_bot")
        pkg.__path__ = [str(BOT)]  # type: ignore[attr-defined]
        sys.modules["shop_bot"] = pkg

    def _alias(mod_name: str, alias: str) -> Any:
        mod = importlib.import_module(mod_name)
        sys.modules[alias] = mod
        return mod

    _alias("database", "shop_bot.data_manager.database")
    dm = types.ModuleType("shop_bot.data_manager")
    dm.database = sys.modules["shop_bot.data_manager.database"]
    sys.modules["shop_bot.data_manager"] = dm
    sys.modules["shop_bot"].data_manager = dm

    for mod_name in (
        "schema_migrations",
        "config",
        "runtime_env",
        "public_urls",
        "admin_auth",
        "local_env",
    ):
        _alias(mod_name, f"shop_bot.{mod_name}")

    utils_pkg = types.ModuleType("shop_bot.utils")
    logger_mod = types.ModuleType("shop_bot.utils.logger")
    logger_mod.bot_logger = SimpleNamespace(
        startup=lambda *a, **k: None,
        system=lambda *a, **k: None,
        user=lambda *a, **k: None,
        error=lambda *a, **k: None,
    )
    sys.modules["shop_bot.utils"] = utils_pkg
    sys.modules["shop_bot.utils.logger"] = logger_mod
    utils_pkg.logger = logger_mod

    modules_pkg = types.ModuleType("shop_bot.modules")
    modules_pkg.remnawave_api = _alias("remnawave_api", "shop_bot.modules.remnawave_api")
    sys.modules["shop_bot.modules"] = modules_pkg
    sys.modules["shop_bot"].modules = modules_pkg

    bot_pkg = types.ModuleType("shop_bot.bot")
    sys.modules["shop_bot.bot"] = bot_pkg
    sys.modules["shop_bot"].bot = bot_pkg
    bot_pkg.portal_links = _alias("portal_links", "shop_bot.bot.portal_links")
    bot_pkg.user_messages = _alias("user_messages", "shop_bot.bot.user_messages")
    bot_pkg.keyboards = _alias("keyboards", "shop_bot.bot.keyboards")
    bot_pkg.support_handler = _alias("support_handler", "shop_bot.bot.support_handler")

    for mod_name in (
        "web_trial_db",
        "subscription_profile",
        "subscription_resolve",
        "subscription_cache",
        "setup_url_service",
        "portal_cabinet",
        "yookassa_payment",
        "balance_billing",
        "vpn_setup_wizard",
    ):
        _alias(mod_name, f"shop_bot.{mod_name}")

    for optional in ("qrcode", "aiohttp"):
        if optional not in sys.modules:
            sys.modules[optional] = types.ModuleType(optional)

    bot_pkg.handlers = _alias("handlers", "shop_bot.bot.handlers")


def _ensure_guards(db_path: Path) -> Path:
    _bootstrap_shop_bot()
    from shop_bot.runtime_env import (
        assert_db_path_allowed_for_qa,
        require_non_production,
        require_qa_tooling_enabled,
    )

    require_non_production("qa_bot_fake_tg")
    require_qa_tooling_enabled("qa_bot_fake_tg")
    resolved = db_path.expanduser().resolve()
    assert_db_path_allowed_for_qa(resolved, "qa_bot_fake_tg")
    return resolved


def _apply_db_path(db_path: Path) -> None:
    os.environ["SHOP_BOT_DB_PATH"] = str(db_path)
    _bootstrap_shop_bot()
    from shop_bot.data_manager import database as dbmod

    dbmod.DB_FILE = db_path
    dbmod.DATA_DIR = db_path.parent


def _resolve_db_path(cli_db: str | None) -> Path:
    if cli_db:
        return Path(cli_db).expanduser().resolve()
    override = (os.getenv("SHOP_BOT_DB_PATH") or os.getenv("BVPN_QA_DB_PATH") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (ROOT / "data" / "shop_bot_qa.db").resolve()


def _extract_buttons(markup: Any) -> list[CapturedButton]:
    if markup is None:
        return []
    buttons: list[CapturedButton] = []
    inline = getattr(markup, "inline_keyboard", None) or []
    for row in inline:
        for btn in row:
            text = getattr(btn, "text", "") or ""
            if getattr(btn, "callback_data", None):
                buttons.append(CapturedButton(text, "callback", btn.callback_data))
            elif getattr(btn, "url", None):
                buttons.append(CapturedButton(text, "url", btn.url))
            elif getattr(btn, "web_app", None):
                wa = btn.web_app
                buttons.append(CapturedButton(text, "web_app", getattr(wa, "url", "") or ""))
    reply = getattr(markup, "keyboard", None) or []
    for row in reply:
        for btn in row:
            text = getattr(btn, "text", "") or ""
            buttons.append(CapturedButton(text, "reply", text))
    return buttons


class _CaptureSink:
    def __init__(self) -> None:
        self.outbound: list[CapturedOutbound] = []

    def record(self, method: str, text: str, *, parse_mode: str | None = None, markup: Any = None) -> None:
        self.outbound.append(
            CapturedOutbound(
                method=method,
                text=str(text or ""),
                parse_mode=parse_mode,
                buttons=_extract_buttons(markup),
            )
        )


class CapturingBot:
    """Minimal Bot stand-in — records outbound, never hits Telegram API."""

    def __init__(self, sink: _CaptureSink) -> None:
        self._sink = sink
        self.id = 1

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> SimpleNamespace:
        self._sink.record("send_message", text, parse_mode=kwargs.get("parse_mode"), markup=kwargs.get("reply_markup"))
        return SimpleNamespace(message_id=1, chat=SimpleNamespace(id=chat_id))

    async def get_me(self) -> SimpleNamespace:
        return SimpleNamespace(username="BenderVPN_QA_bot", id=self.id)


class CapturingMessage:
    def __init__(
        self,
        bot: CapturingBot,
        tg_id: int,
        username: str,
        *,
        text: str = "/start",
        sink: _CaptureSink,
    ) -> None:
        self.bot = bot
        self._sink = sink
        self.message_id = 1
        self.text = text
        self.chat = SimpleNamespace(id=tg_id, type="private")
        self.from_user = SimpleNamespace(
            id=tg_id,
            username=username,
            full_name=f"QA {username}",
            is_bot=False,
        )

    async def answer(self, text: str, **kwargs: Any) -> "CapturingMessage":
        self._sink.record("answer", text, parse_mode=kwargs.get("parse_mode"), markup=kwargs.get("reply_markup"))
        return self

    async def edit_text(self, text: str, **kwargs: Any) -> "CapturingMessage":
        self._sink.record("edit_text", text, parse_mode=kwargs.get("parse_mode"), markup=kwargs.get("reply_markup"))
        return self

    async def delete(self) -> None:
        return None


class CapturingCallback:
    def __init__(self, bot: CapturingBot, message: CapturingMessage, data: str, sink: _CaptureSink) -> None:
        self.bot = bot
        self.message = message
        self.from_user = message.from_user
        self.data = data
        self._sink = sink

    async def answer(self, text: str | None = None, **kwargs: Any) -> None:
        if text:
            self._sink.record("callback_answer", text)


async def _make_fsm_context(tg_id: int) -> Any:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    from aiogram.fsm.storage.memory import MemoryStorage

    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=tg_id, user_id=tg_id)
    return FSMContext(storage=storage, key=key)


def _normalize_vpn_key_expiry_for_handlers(tg_id: int) -> None:
    """Handlers compare naive datetime.now() to expiry_date — normalize seeded ISO-Z values."""
    from shop_bot.data_manager.database import db_connection

    with db_connection() as conn:
        rows = conn.execute(
            "SELECT key_id, expiry_date FROM vpn_keys WHERE user_id = ?",
            (tg_id,),
        ).fetchall()
        for key_id, raw in rows:
            if not raw:
                continue
            text = str(raw).replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                continue
            if dt.tzinfo is not None:
                naive = dt.replace(tzinfo=None).isoformat(sep=" ")
                conn.execute(
                    "UPDATE vpn_keys SET expiry_date = ? WHERE key_id = ?",
                    (naive, key_id),
                )
        conn.commit()


def _lookup_username(tg_id: int) -> str:
    from shop_bot.data_manager.database import get_user

    user = get_user(tg_id)
    if user and user.get("username"):
        return str(user["username"])
    return f"qa_user_{tg_id}"


def _maybe_fresh_start(tg_id: int) -> str:
    from shop_bot.data_manager.database import db_connection

    with db_connection() as conn:
        conn.execute("DELETE FROM user_actions WHERE user_id = ?", (tg_id,))
        conn.execute("DELETE FROM vpn_keys WHERE user_id = ?", (tg_id,))
        conn.execute("DELETE FROM users WHERE telegram_id = ?", (tg_id,))
        conn.commit()
    return "fresh_start: QA user row removed before /start"


async def _invoke_action(
    action: str,
    tg_id: int,
    username: str,
    *,
    fresh_start: bool = False,
) -> HarnessResult:
    from shop_bot.bot import handlers
    from shop_bot.config import telegram_cabinet_webapp_url
    from shop_bot.portal_cabinet import cabinet_snapshot

    sink = _CaptureSink()
    bot = CapturingBot(sink)
    message = CapturingMessage(bot, tg_id, username, sink=sink)
    state = await _make_fsm_context(tg_id)
    db_mode = "seeded_row"
    blocked = ""

    if fresh_start and action in ("start", "start_with_ref"):
        blocked = _maybe_fresh_start(tg_id)
        db_mode = "fresh_no_row"

    result = HarnessResult(
        scenario=None,
        tg_user_id=tg_id,
        username=username,
        action=action,
        db_mode=db_mode,
        outbound=sink.outbound,
        expected_next=ACTION_NEXT_HINT.get(action, ""),
        blocked_notes=blocked,
    )

    fake_sub = f"https://sandbox.invalid/sub/qa-{tg_id}"

    with (
        patch(
            "shop_bot.subscription_cache.get_subscription_url_cached",
            new=AsyncMock(return_value=fake_sub),
        ),
        patch(
            "shop_bot.subscription_resolve.resolve_subscription_url",
            new=AsyncMock(return_value=fake_sub),
        ),
    ):
        try:
            if action == "start":
                message.text = "/start"
                await handlers.start_handler(message, state)
            elif action == "start_with_ref":
                message.text = "/start ref_QA_REF_INVITER"
                await handlers.start_handler(message, state)
            elif action == "menu":
                message.text = "🏠 Главное меню"
                await handlers.main_menu_handler(message, state)
            elif action == "get_setup":
                cb = CapturingCallback(bot, message, "menu_get_setup", sink)
                await handlers.menu_get_setup_handler(cb)
            elif action == "topup":
                cb = CapturingCallback(bot, message, "show_topup", sink)
                await handlers.show_topup_handler(cb)
            elif action == "help":
                cb = CapturingCallback(bot, message, "menu_help", sink)
                await handlers.menu_help_handler(cb)
            elif action == "status":
                cb = CapturingCallback(bot, message, "my_account", sink)
                await handlers.my_account_handler(cb)
            elif action == "invite":
                cb = CapturingCallback(bot, message, "invite_friend", sink)
                await handlers.invite_friend_handler(cb)
            elif action == "cabinet":
                result.cabinet_snapshot = cabinet_snapshot(telegram_id=tg_id)
            elif action == "cabinet_link":
                result.cabinet_link = telegram_cabinet_webapp_url(tg_id)
            else:
                raise ValueError(f"Unknown action {action!r}")
        except Exception as exc:
            result.errors.append(f"{type(exc).__name__}: {exc}")

    result.outbound = sink.outbound
    return result


def render_transcript(result: HarnessResult, *, simulation_note: str = SEED_SIMULATION_NOTE) -> str:
    lines = [
        f"# QA bot preview — {result.scenario or 'custom'}",
        "",
        f"- **tg_user_id:** `{result.tg_user_id}`",
        f"- **username:** `{result.username}`",
        f"- **action:** `{result.action}`",
        f"- **db_mode:** {result.db_mode}",
        f"- **generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Simulation note",
        simulation_note,
        "",
    ]
    if result.blocked_notes:
        lines.extend([f"**Harness note:** {result.blocked_notes}", ""])
    if result.cabinet_link:
        lines.extend([f"**cabinet_link:** `{result.cabinet_link}`", ""])
    if result.cabinet_snapshot is not None:
        lines.extend(["## cabinet_snapshot", "```json", json.dumps(result.cabinet_snapshot, ensure_ascii=False, indent=2), "```", ""])
    if result.errors:
        lines.extend(["## errors", *[f"- {e}" for e in result.errors], ""])
    lines.append("## Outbound messages")
    if not result.outbound:
        lines.append("_No captured outbound messages._")
    for idx, msg in enumerate(result.outbound, 1):
        lines.append(f"### {idx}. `{msg.method}`")
        lines.append(msg.text or "_(empty)_")
        if msg.buttons:
            lines.append("")
            lines.append("**Buttons:**")
            for btn in msg.buttons:
                lines.append(f"- `{btn.label}` → `{btn.kind}`: `{btn.value}`")
        lines.append("")
    if result.expected_next:
        lines.extend(["## Expected next action", result.expected_next, ""])
    return "\n".join(lines).rstrip() + "\n"


def list_actions() -> None:
    for action in ACTIONS:
        print(f"{action:16} {ACTION_NEXT_HINT.get(action, '')}")


def list_scenarios() -> None:
    for name in COVERED_SCENARIOS:
        tid = SCENARIO_TG_ID.get(name, "-")
        print(f"{name:32} tg={tid}")


async def run_harness(
    *,
    scenario: str | None,
    tg_id: int | None,
    action: str,
    db_path: Path,
    fresh_start: bool = False,
) -> HarnessResult:
    _apply_db_path(db_path)
    from shop_bot.data_manager.database import initialize_db

    initialize_db()

    if scenario:
        key = scenario.strip().lower()
        if key not in SCENARIO_TG_ID:
            raise ValueError(f"Unknown scenario {scenario!r}. Use --list.")
        tid = SCENARIO_TG_ID[key]
        scen_name = key
    elif tg_id is not None:
        tid = int(tg_id)
        scen_name = None
    else:
        raise ValueError("Specify --scenario NAME or --tg-id ID")

    if 0 < tid < QA_TG_ID_MIN:
        raise ValueError(
            f"tg_id {tid} outside QA synthetic range ({QA_TG_ID_MIN}+). "
            "Use seeded scenario ids only."
        )

    username = _lookup_username(tid)
    _normalize_vpn_key_expiry_for_handlers(tid)
    result = await _invoke_action(action, tid, username, fresh_start=fresh_start)
    result.scenario = scen_name
    return result


QA_TG_ID_MIN = 900_000_001


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA fake Telegram bot handler harness")
    parser.add_argument("--db", help="SQLite path (SHOP_BOT_DB_PATH)")
    parser.add_argument("--scenario", help="Seeded scenario name")
    parser.add_argument("--tg-id", type=int, help="Synthetic telegram_id (900000001+)")
    parser.add_argument("--action", choices=ACTIONS, default="menu")
    parser.add_argument("--fresh-start", action="store_true", help="Delete QA user row before start")
    parser.add_argument("--out", help="Write markdown transcript to path")
    parser.add_argument("--list", action="store_true", help="List covered scenarios")
    parser.add_argument("--list-actions", action="store_true", help="List actions")
    args = parser.parse_args(argv)

    if args.list:
        list_scenarios()
        return 0
    if args.list_actions:
        list_actions()
        return 0

    db_path = _resolve_db_path(args.db)
    db_path = _ensure_guards(db_path)
    print(f"QA bot harness target DB: {db_path}")
    print("Telegram send API: DISABLED (capture-only)")

    result = asyncio.run(
        run_harness(
            scenario=args.scenario,
            tg_id=args.tg_id,
            action=args.action,
            db_path=db_path,
            fresh_start=args.fresh_start,
        )
    )

    transcript = render_transcript(result)
    print(transcript)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(transcript, encoding="utf-8")
        print(f"Transcript written: {out_path}")
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
