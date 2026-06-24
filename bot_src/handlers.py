import logging
import uuid
from io import BytesIO
from datetime import datetime, timedelta, timezone
import qrcode
import aiohttp
from yookassa import Payment
import os
import hashlib
import json
import tarfile
import shutil
from pathlib import Path

from aiogram import Bot, Router, F, types, html
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Универсальная функция для безопасного редактирования сообщений
async def safe_edit_message(message: types.Message, text: str, reply_markup=None):
    """
    Безопасно редактирует сообщение, обрабатывая ошибки Telegram
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Добавляем невидимый символ для принудительного обновления
            modified_text = text + "‎"  # Добавляем невидимый символ
            try:
                await message.edit_text(modified_text, reply_markup=reply_markup)
            except:
                # Если всё равно не получается, отправляем новое сообщение
                await message.answer(text, reply_markup=reply_markup)
        else:
            # Для других ошибок отправляем новое сообщение
            await message.answer(text, reply_markup=reply_markup)
    except Exception:
        # Для любых других ошибок отправляем новое сообщение
        await message.answer(text, reply_markup=reply_markup)


from shop_bot.bot import keyboards, user_messages
from shop_bot.modules import remnawave_api
from shop_bot.data_manager.database import (
    get_user, add_new_key, get_user_keys, update_user_stats,
    register_user_if_not_exists, get_next_key_number, get_key_by_id,
    update_key_info, set_trial_used, reset_trial_used, set_terms_agreed, get_setting,
    get_promo, apply_promo_usage, ensure_user_ref_code, link_referral, count_referrals,
    set_auto_renew, get_auto_renew, log_action, has_action, add_traffic_extra,
    create_promo, get_all_promos, get_balance, add_balance,
)
from shop_bot.yookassa_payment import yookassa_receipt
from shop_bot.config import (
    PLANS, get_profile_text, get_vpn_active_text, VPN_INACTIVE_TEXT, VPN_NO_DATA_TEXT,
    get_key_info_text, CHOOSE_PAYMENT_METHOD_MESSAGE, get_purchase_success_text, ABOUT_TEXT, TERMS_URL, PRIVACY_URL, SUPPORT_USER, SUPPORT_TEXT,
    REMNA_TRIAL_DAYS, DAILY_RATE, TOPUP_PRESETS, CUSTOM_AMOUNT_UNAVAILABLE, KEY_EMAIL_DOMAIN,
    balance_to_days,
    format_daily_rate_ru,
    DEFAULT_TERMS_URL, DEFAULT_PRIVACY_URL, DEFAULT_SUPPORT_USERNAME,
    effective_legal_url,
    REFERRAL_UI_ENABLED,
)
from shop_bot.config import TRAFFIC_PACKS
from shop_bot.modules.remnawave_api import add_extra_traffic

TELEGRAM_BOT_USERNAME = None
CRYPTO_API_KEY = None
CRYPTO_MERCHANT_ID = None
PAYMENT_METHODS = None
PLANS = None
from shop_bot.admin_auth import is_admin_telegram

ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")

logger = logging.getLogger(__name__)

# Импорт красивого логгера
from shop_bot.utils.logger import bot_logger


async def referral_invite_payload(bot: Bot, user_id: int) -> tuple[str, str]:
    ref_code = ensure_user_ref_code(user_id)
    ref_count = count_referrals(ref_code)
    # §4.1 portal-first: основная пригласительная ссылка ведёт на портал
    # (клиент делится порталом), а не на t.me. Портал сам проносит ref в бота.
    try:
        from shop_bot.public_urls import portal_page_url

        ref_url = portal_page_url("", query={"ref": ref_code})
    except Exception:
        bot_info = await bot.get_me()
        ref_url = f"https://t.me/{bot_info.username}?start=ref_{ref_code}"
    text = user_messages.msg_referral_invite(ref_count, ref_url)
    return text, ref_url


async def present_referral_invite(
    message: types.Message,
    bot: Bot,
    user_id: int,
    *,
    edit: bool = True,
) -> None:
    text, ref_url = await referral_invite_payload(bot, user_id)
    markup = keyboards.create_referral_keyboard(ref_url)
    if edit:
        try:
            await message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=markup)


async def process_topup_payment(
    bot: Bot,
    user_id: int,
    amount_rub: float,
    *,
    idempotency_key: str | None = None,
    notify: bool = True,
) -> bool:
    """Зачислить пополнение и синхронизировать expireAt на панели. True если обработано."""
    if amount_rub <= 0:
        return False
    from shop_bot.data_manager.database import try_acquire_topup_idempotency

    webhook_key = bool(
        idempotency_key
        and idempotency_key.startswith(("yk:", "crypto:", "cryptobot:"))
    )
    if idempotency_key:
        if webhook_key:
            if has_action(user_id, idempotency_key):
                logger.info("Duplicate topup ignored: user=%s key=%s", user_id, idempotency_key)
                return False
        elif not try_acquire_topup_idempotency(user_id, idempotency_key):
            logger.info("Duplicate topup ignored: user=%s key=%s", user_id, idempotency_key)
            return False

    add_balance(user_id, amount_rub)
    from shop_bot.balance_billing import waive_daily_charge_today

    waive_daily_charge_today(user_id)
    new_balance = get_balance(user_id)
    days_left = balance_to_days(new_balance)
    synced = await sync_panel_access_from_balance(user_id, new_balance)
    update_user_stats(user_id, amount_rub, 0)
    log_action(user_id, "topup", f"{amount_rub}")
    if idempotency_key and webhook_key:
        log_action(user_id, idempotency_key, f"{amount_rub}")

    if notify:
        sync_note = "" if synced else (
            "\n\n⚠️ Баланс зачислен; синхронизация с панелью не удалась — напишите в поддержку."
        )
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Оплата прошла!\n\n"
                f"VPN активен ещё ~{days_left} дней.\n"
                f"Баланс: {new_balance:.0f} ₽"
                f"{sync_note}"
            ),
            parse_mode="HTML",
        )
    return synced


async def sync_panel_access_from_balance(user_id: int, balance: float) -> bool:
    """Синхронизировать expireAt на панели с балансом (абсолютный срок, не +N к trial)."""
    from shop_bot.balance_billing import sync_panel_from_balance

    if balance_to_days(balance) <= 0:
        return await sync_panel_from_balance(user_id)
    keys = get_user_keys(user_id)
    if not keys:
        key_number = get_next_key_number(user_id)
        email = f"user{user_id}-key{key_number}@{KEY_EMAIL_DOMAIN}"
        days = balance_to_days(balance)
        uri, expire_iso, vless_uuid, _sub_url = await remnawave_api.provision_key(
            email, days=days, telegram_id=str(user_id)
        )
        if not uri or not expire_iso or not vless_uuid:
            return False
        expiry_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))
        add_new_key(user_id, vless_uuid, email, int(expiry_dt.timestamp() * 1000))
        from shop_bot.subscription_cache import invalidate_subscription_url_cache

        invalidate_subscription_url_cache(user_id)
        return True
    return await sync_panel_from_balance(user_id)

async def notify_backup_failure(
    bot: Bot, admin_id: str, title: str, detail: str, is_auto: bool = False
) -> None:
    """Telegram alert for backup failures only (no success spam)."""
    kind = "Auto" if is_auto else "Manual"
    text = (
        f"❌ <b>Backup failed</b> ({kind})\n\n"
        f"<b>{title}</b>\n"
        f"<code>{detail[:500]}</code>\n"
        f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    try:
        await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
    except Exception as e:
        bot_logger.backup("NOTIFY_FAILED", f"Could not alert admin: {e}", "ERROR")


async def create_backup_and_send(bot: Bot, admin_id: str, is_auto: bool = False) -> bool:
    """Create shop SQLite backup on disk. Telegram — failures only.
    
    Args:
        bot: Экземпляр бота
        admin_id: ID админа для отправки
        is_auto: True если автоматический бэкап, False если ручной
        
    Returns:
        bool: True если бэкап создан успешно, False в случае ошибки
    """
    backup_type = "🤖 Automatic" if is_auto else "📦 Manual"
    logger.info(f"🎯 Starting {backup_type.lower()} backup process...")
    
    try:
        # Получаем путь к базе данных
        from shop_bot.data_manager.database import DB_FILE, set_last_backup_timestamp
        db_path = Path(DB_FILE)
        
        # Создаем папку для бэкапов
        backups_dir = db_path.parent / 'backups'
        backups_dir.mkdir(exist_ok=True)
        bot_logger.backup("CREATE_DIR", f"Backup directory: {backups_dir}")
        
        # Генерируем имя файла бэкапа
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        
        # Создаем tar.gz архив
        backup_file = backups_dir / f"{backup_name}.tar.gz"
        bot_logger.backup("CREATE_ARCHIVE", f"Creating: {backup_file.name}")
        
        with tarfile.open(backup_file, "w:gz") as tar:
            tar.add(db_path, arcname=db_path.name)
        
        # Получаем информацию о файле
        file_size = backup_file.stat().st_size
        # Исправляем расчет размера - если меньше 1 МБ, показываем в КБ
        if file_size >= 1024 * 1024:
            file_size_str = f"{file_size / (1024 * 1024):.1f} MB"
        else:
            file_size_str = f"{file_size / 1024:.1f} KB"
        
        server_ip = (
            os.getenv("BACKUP_SERVER_IP", "").strip()
            or os.getenv("AMS_PANEL_HOST_IP", "").strip()
        )

        set_last_backup_timestamp(datetime.now(timezone.utc).isoformat())
        bot_logger.backup(
            "OK",
            f"{'Auto' if is_auto else 'Manual'} backup saved: {backup_file.name} ({file_size_str})",
            "OK",
        )
        return True
        
    except Exception as e:
        bot_logger.backup("CRITICAL_ERROR", f"Backup creation failed: {e}", "ERROR")
        await notify_backup_failure(
            bot, admin_id, "Shop bot SQLite backup", str(e), is_auto=is_auto
        )
        return False

admin_router = Router()
user_router = Router()

async def show_main_menu(message: types.Message, edit_message: bool = False):
    user_id = message.chat.id
    user_db_data = get_user(user_id)
    user_keys = get_user_keys(user_id)
    now = datetime.now()
    active_keys = [
        k for k in user_keys
        if datetime.fromisoformat(k["expiry_date"]) > now
    ]
    has_active_sub = len(active_keys) > 0

    trial_available = not (user_db_data and user_db_data.get('trial_used'))
    is_admin = is_admin_telegram(user_id)

    if has_active_sub:
        text = user_messages.MSG_MAIN_MENU_ACTIVE
    else:
        text = user_messages.MSG_MAIN_MENU_NEW
        if trial_available:
            text += user_messages.MSG_MAIN_MENU_TRIAL_HINT
    auto_renew = get_auto_renew(user_id) if user_db_data else False
    keyboard = keyboards.create_main_menu_keyboard(
        has_active_sub,
        trial_available,
        is_admin,
        telegram_id=user_id,
        auto_renew=auto_renew,
    )
    
    if edit_message:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    else:
        await message.answer(text, reply_markup=keyboard)

class UserAgreement(StatesGroup):
    waiting_for_agreement = State()

class PromoInput(StatesGroup):
    waiting_for_code = State()

class PromoCreate(StatesGroup):
    waiting_for_code = State()
    waiting_for_discount = State()
    waiting_for_days = State()
    waiting_for_limit = State()


class VpnSetupWizard(StatesGroup):
    picking_device = State()
    on_device = State()


class CustomTopup(StatesGroup):
    waiting_for_amount = State()


async def _fetch_subscription_url(user_id: int) -> str | None:
    from shop_bot.subscription_cache import get_subscription_url_cached

    try:
        return await get_subscription_url_cached(user_id)
    except Exception as exc:
        logger.warning("fetch_subscription_url: %s", exc)
    return None


async def _wizard_setup_url(user_id: int) -> tuple[str | None, str | None]:
    from shop_bot.setup_url_service import get_setup_url_for_user

    return await get_setup_url_for_user(user_id)

async def _apply_web_bind(message: types.Message, bind_token: str) -> bool:
    """Bind web trial to this Telegram chat. Returns True if bind attempted."""
    from shop_bot.web_tg_bind import bind_web_account_by_token

    token = (bind_token or "").strip()
    if not token:
        return False
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name or ""
    result = await bind_web_account_by_token(token, user_id, username)
    cid = html.quote(result.get("customer_id") or "")
    if result.get("ok"):
        if result.get("already_bound"):
            await message.answer(
                user_messages.MSG_WEB_BIND_ALREADY.format(customer_id=cid),
                parse_mode="HTML",
            )
        else:
            await message.answer(
                user_messages.MSG_WEB_BIND_OK.format(customer_id=cid),
                parse_mode="HTML",
            )
        log_action(user_id, "web_tg_bind", cid)
        return True
    err = result.get("error")
    if err == "invalid_token":
        await message.answer(user_messages.MSG_WEB_BIND_INVALID, parse_mode="HTML")
    elif err == "both_have_keys":
        await message.answer(
            user_messages.MSG_WEB_BIND_CONFLICT.format(customer_id=cid or "—"),
            parse_mode="HTML",
        )
    elif err == "already_bound_other":
        await message.answer(
            user_messages.MSG_WEB_BIND_OTHER_TG.format(customer_id=cid or "—"),
            parse_mode="HTML",
        )
    else:
        await message.answer(user_messages.MSG_WEB_BIND_INVALID, parse_mode="HTML")
    return True


async def _reply_telegram_id(message: types.Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name or ""
    register_user_if_not_exists(user_id, username)
    await message.answer(
        user_messages.msg_telegram_id(user_id),
        parse_mode="HTML",
    )


@user_router.message(Command("id"))
async def id_command_handler(message: types.Message):
    await _reply_telegram_id(message)


@user_router.message(Command("myid"))
async def myid_command_handler(message: types.Message):
    await _reply_telegram_id(message)


@user_router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    ref_code = None
    bind_token = None
    start_arg = None
    if message.text and " " in message.text:
        start_arg = message.text.split(" ", 1)[1].strip()
        if start_arg == "show_id":
            register_user_if_not_exists(user_id, username)
            log_action(user_id, "funnel_bot_start", "show_id")
            await _reply_telegram_id(message)
            user_data = get_user(user_id)
            if user_data and user_data.get("agreed_to_terms"):
                await message.answer(
                    f"👋 Снова здравствуйте, {html.bold(message.from_user.full_name)}!",
                    reply_markup=ReplyKeyboardRemove(),
                )
                await show_main_menu(message)
            return
        if start_arg.startswith("ref_"):
            ref_code = start_arg[4:]
        elif start_arg.startswith("bind_"):
            bind_token = start_arg[5:]
    register_user_if_not_exists(user_id, username)
    funnel_detail = "bind:***" if bind_token else (ref_code or "")
    log_action(user_id, "funnel_bot_start", funnel_detail)
    user_data = get_user(user_id)  # after register — fresh row
    if ref_code and user_data and not user_data.get("referred_by"):
        if link_referral(ref_code, user_id):
            log_action(user_id, "referral_linked", ref_code)
    if bind_token:
        await state.update_data(pending_web_bind=bind_token)

    if user_data and user_data.get("agreed_to_terms"):
        if bind_token:
            await _apply_web_bind(message, bind_token)
            await state.update_data(pending_web_bind=None)
        await message.answer(
            f"👋 Снова здравствуйте, {html.bold(message.from_user.full_name)}!",
            reply_markup=ReplyKeyboardRemove(),
        )
        await show_main_menu(message)
    else:
        await state.clear()
        try:
            from shop_bot.onboarding_copy import t as ob_t
            from shop_bot.onboarding_flow import start_onboarding

            if ref_code:
                await state.update_data(onboarding_ref_note=ob_t("ref_applied_note"))
            await start_onboarding(message, state)
        except Exception:
            logger.exception("onboarding start failed for user %s — legacy terms screen", user_id)
            await state.set_state(UserAgreement.waiting_for_agreement)
            await message.answer(
                "Для доступа к BenderVPN примите условия использования и политику конфиденциальности.",
                reply_markup=keyboards.create_agreement_keyboard(),
            )

@user_router.callback_query(F.data == "agree_to_terms")
async def agree_to_terms_handler(callback: types.CallbackQuery, state: FSMContext):
    """Legacy «Принимаю» — maps to rules+privacy accept (§5)."""
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name or ""
    await callback.answer()
    register_user_if_not_exists(user_id, username)

    user_data = get_user(user_id)
    if user_data and user_data.get("agreed_to_terms"):
        await state.clear()
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await show_main_menu(callback.message)
        return

    try:
        from shop_bot.onboarding_flow import legacy_agree_combined

        await legacy_agree_combined(callback, state)
    except Exception:
        logger.exception("legacy agree onboarding failed for user %s", user_id)
        set_terms_agreed(user_id)
        log_action(user_id, "terms_accepted", "legacy_fallback")
        await state.clear()
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer("👋", reply_markup=ReplyKeyboardRemove())
        await show_main_menu(callback.message)

@user_router.message(UserAgreement.waiting_for_agreement)
async def agreement_fallback_handler(message: types.Message):
    await message.answer("Выберите действие кнопками на экране выше.")


async def _send_terms_prompt(target_message: types.Message, state: FSMContext) -> bool:
    """Resume onboarding at rules step. Always returns False."""
    try:
        from shop_bot.onboarding_flow import prompt_rules

        await prompt_rules(target_message, state)
    except Exception:
        logger.exception("onboarding rules prompt failed")
        await state.set_state(UserAgreement.waiting_for_agreement)
        await target_message.answer(
            "Для доступа к BenderVPN примите условия использования и политику конфиденциальности.",
            reply_markup=keyboards.create_agreement_keyboard(),
        )
    return False


async def _ensure_terms_or_prompt(message: types.Message, state: FSMContext) -> bool:
    """Return True if user may use the bot (terms accepted)."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name or ""
    register_user_if_not_exists(user_id, username)
    user_data = get_user(user_id)
    if user_data and user_data.get("agreed_to_terms"):
        return True
    return await _send_terms_prompt(message, state)


async def _ensure_terms_callback(callback: types.CallbackQuery, state: FSMContext) -> bool:
    """Terms gate for inline callbacks (trial / payment / wizard entry points).

    Resolves identity from `callback.from_user` (callback.message.from_user is the
    bot), prompts via the callback message, and alerts the user. Returns True only
    when terms are accepted. BILL-TERMS-GUARD-001 / BILL-TERMS-GUARD-002.
    """
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name or ""
    register_user_if_not_exists(user_id, username)
    user_data = get_user(user_id)
    if user_data and user_data.get("agreed_to_terms"):
        return True
    try:
        await _send_terms_prompt(callback.message, state)
    except Exception:
        logger.warning("terms prompt send failed for user %s", user_id, exc_info=True)
    try:
        await callback.answer(
            "Сначала прими условия использования — кнопка «Принимаю» выше.",
            show_alert=True,
        )
    except Exception:
        pass
    return False


@user_router.message(F.text == "🏠 Главное меню")
async def main_menu_handler(message: types.Message, state: FSMContext):
    if not await _ensure_terms_or_prompt(message, state):
        return
    await show_main_menu(message)

@user_router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await show_main_menu(callback.message, edit_message=True)


@user_router.callback_query(F.data == "connect_vpn")
async def connect_vpn_wizard_start(callback: types.CallbackQuery, state: FSMContext):
    from shop_bot.vpn_setup_wizard import WIZARD_INTRO

    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer()
    await state.set_state(VpnSetupWizard.picking_device)
    log_action(callback.from_user.id, "wizard_start", "")
    await callback.message.edit_text(
        WIZARD_INTRO,
        reply_markup=keyboards.create_wizard_device_picker_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data.startswith("wizard_pick_"))
async def connect_vpn_wizard_device(callback: types.CallbackQuery, state: FSMContext):
    from shop_bot.vpn_setup_wizard import format_device_lead, get_device

    if not await _ensure_terms_callback(callback, state):
        return
    device_id = callback.data.replace("wizard_pick_", "", 1)
    if not get_device(device_id):
        await callback.answer("Неизвестное устройство", show_alert=True)
        return
    await callback.answer()
    await state.set_state(VpnSetupWizard.on_device)
    await state.update_data(wizard_device=device_id)
    user_id = callback.from_user.id
    user_db = get_user(user_id)
    trial_available = not (user_db and user_db.get("trial_used"))
    setup_url, setup_reason = await _wizard_setup_url(user_id)
    lead = format_device_lead(device_id)
    if not setup_url:
        lead += "\n\n" + user_messages.MSG_WIZARD_SETUP_UNAVAILABLE
        log_action(user_id, "wizard_setup_unavailable", setup_reason or "unknown")
    log_action(user_id, "wizard_device", device_id)
    await callback.message.edit_text(
        lead,
        reply_markup=keyboards.create_wizard_device_keyboard(
            device_id,
            trial_available=trial_available,
            setup_url=setup_url,
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data.startswith("wizard_chat_"))
async def connect_vpn_wizard_chat(callback: types.CallbackQuery, state: FSMContext):
    from shop_bot.vpn_setup_wizard import format_chat_steps, get_device

    if not await _ensure_terms_callback(callback, state):
        return
    device_id = callback.data.replace("wizard_chat_", "", 1)
    if not get_device(device_id):
        await callback.answer("Неизвестное устройство", show_alert=True)
        return
    await callback.answer()
    user_id = callback.from_user.id
    has_key = bool(get_user_keys(user_id))
    log_action(user_id, "wizard_chat", device_id)
    await callback.message.edit_text(
        format_chat_steps(device_id, has_active_key=has_key),
        reply_markup=keyboards.create_wizard_chat_keyboard(device_id),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == "wizard_stuck")
async def connect_vpn_wizard_stuck(callback: types.CallbackQuery):
    from shop_bot.vpn_setup_wizard import WIZARD_STUCK

    await callback.answer()
    await callback.message.edit_text(
        WIZARD_STUCK,
        reply_markup=keyboards.create_support_keyboard(get_setting("support_user")),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@user_router.callback_query(F.data == "show_profile")
async def profile_handler_callback(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user_db_data = get_user(user_id)
    user_keys = get_user_keys(user_id)
    if not user_db_data:
        await callback.answer(user_messages.ERR_PROFILE_ALERT, show_alert=True)
        return
    username = html.bold(user_db_data.get('username', 'Пользователь'))
    total_spent, total_months = user_db_data.get('total_spent', 0), user_db_data.get('total_months', 0)
    now = datetime.now()
    active_keys = [key for key in user_keys if datetime.fromisoformat(key['expiry_date']) > now]
    if active_keys:
        latest_key = max(active_keys, key=lambda k: datetime.fromisoformat(k['expiry_date']))
        latest_expiry_date = datetime.fromisoformat(latest_key['expiry_date'])
        time_left = latest_expiry_date - now
        vpn_status_text = get_vpn_active_text(time_left.days, time_left.seconds // 3600)
    elif user_keys: vpn_status_text = VPN_INACTIVE_TEXT
    else: vpn_status_text = VPN_NO_DATA_TEXT
    ref_code = ensure_user_ref_code(user_id)
    ref_count = count_referrals(ref_code)
    final_text = get_profile_text(username, total_spent, total_months, vpn_status_text)
    if REFERRAL_UI_ENABLED:
        final_text += (
            f"\n\n👥 Приглашено друзей: <b>{ref_count}</b>\n"
            "Ссылку для друга — кнопка «Пригласить друга» ниже."
        )
    await callback.message.edit_text(
        final_text,
        parse_mode="HTML",
        reply_markup=keyboards.create_profile_keyboard(),
    )

@user_router.callback_query(F.data == "show_referrals")
async def referrals_handler(callback: types.CallbackQuery):
    await callback.answer()
    await present_referral_invite(
        callback.message, callback.bot, callback.from_user.id, edit=True
    )

@user_router.callback_query(F.data == "show_about")
async def about_handler(callback: types.CallbackQuery):
    await callback.answer()
    await _present_info_menu(callback.message, edit=True)


@user_router.callback_query(F.data == "show_info")
async def show_info_handler(callback: types.CallbackQuery):
    await callback.answer()
    await _present_info_menu(callback.message, edit=True)


async def _present_info_menu(message: types.Message, *, edit: bool = False):
    from shop_bot.info_copy import info_block

    ib = info_block()
    title = ib.get("menu_title") or "ℹ️ Информация"
    lead = (
        ib.get("menu_lead")
        or "FAQ, правила, документы и статус — в разделе кабинета, не в чате бота."
    )
    text = f"<b>{title}</b>\n\n{lead}"
    kb = keyboards.create_info_menu_keyboard()
    if edit:
        try:
            await message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest:
            await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


@user_router.callback_query(F.data == "info_faq")
@user_router.callback_query(F.data.startswith("info_faq_page:"))
@user_router.callback_query(F.data.startswith("info_faq_item:"))
@user_router.callback_query(F.data == "info_rules")
@user_router.callback_query(F.data == "info_privacy")
@user_router.callback_query(F.data == "info_offer")
@user_router.callback_query(F.data == "info_status")
async def info_legacy_redirect_handler(callback: types.CallbackQuery):
    """Legacy inline info callbacks → portal hub (§15)."""
    await callback.answer()
    await _present_info_menu(callback.message, edit=True)

@user_router.callback_query(F.data == "show_traffic")
async def traffic_status_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    keys = get_user_keys(user_id)
    if not keys:
        await callback.message.edit_text(
            "Доступа пока нет. Активируйте бесплатный период или пополните баланс — статус появится здесь.",
            reply_markup=keyboards.create_back_to_menu_keyboard(),
        )
        return
    from shop_bot.modules.remnawave_api import get_user_by_telegram_id, get_nodes_health

    lines = ["<b>📊 Статус</b>", ""]
    async with remnawave_api.remna_client_session() as session:
        # Серверы — только агрегат, без отдельных локаций (канон §8.2).
        health = await get_nodes_health(session)
        if health is None:
            lines.append("🌍 Серверы: статус временно недоступен")
        else:
            up, total = health
            if total and up >= total:
                lines.append(f"🌍 Серверы: все в норме · {up}/{total}")
            elif total:
                lines.append(f"🌍 Серверы: {up}/{total} в норме")
            else:
                lines.append("🌍 Серверы: нет данных")

        # Трафик: канон K4 — без лимита; цифры показываем только если лимит реально задан.
        remote = await get_user_by_telegram_id(session, str(user_id))
        total_extra = sum(key.get('traffic_extra_bytes', 0) or 0 for key in keys)
        limit = ((remote or {}).get('trafficLimitBytes', 0) or 0) + total_extra
        if remote and limit > 0:
            used = remote.get('usedTrafficBytes', 0) or 0
            percent = min(100, (used / limit) * 100)
            lines.append(
                f"📈 Трафик: {used / 1024**3:.1f} из {limit / 1024**3:.1f} ГБ · {percent:.0f}%"
            )
        else:
            lines.append("📈 Трафик: без лимита")

    # Доступ — по ключам пользователя.
    now = datetime.now()
    active = sum(1 for k in keys if datetime.fromisoformat(k['expiry_date']) > now)
    latest = max(datetime.fromisoformat(k['expiry_date']) for k in keys)
    lines.append("")
    if active:
        lines.append(f"🔑 Доступ активен · устройств: {active}")
        lines.append(f"📅 Действует до {latest.strftime('%d.%m.%Y')}")
    else:
        lines.append("🔑 Доступ истёк — пополните баланс, чтобы продолжить")

    lines.append("")
    lines.append(f"<i>Обновлено в {now.strftime('%H:%M')}</i>")

    await safe_edit_message(callback.message, "\n".join(lines), keyboards.create_traffic_keyboard())

@user_router.callback_query(F.data == "refresh_traffic")
async def refresh_traffic_handler(callback: types.CallbackQuery):
    await callback.answer("🔄 Обновляю данные...")
    # Просто вызываем обновление данных
    await traffic_status_handler(callback)

@user_router.callback_query(F.data == "show_help")
async def about_handler(callback: types.CallbackQuery):
    await callback.answer()

    support_user = get_setting("support_user")
    support_text = get_setting("support_text")

    if support_user == SUPPORT_USER and support_text == SUPPORT_TEXT:
        await callback.message.edit_text(
            support_user,
            reply_markup=keyboards.create_back_to_menu_keyboard()
        )
    elif support_text == SUPPORT_TEXT:
        await callback.message.edit_text(
            "Для связи с поддержкой используйте кнопку ниже.",
            reply_markup=keyboards.create_support_keyboard(support_user)
        )
    else:
        await callback.message.edit_text(
            support_text + "\n\n" + "Для связи с поддержкой используйте кнопку ниже.",
            reply_markup=keyboards.create_support_keyboard(support_user)
        )

@user_router.callback_query(F.data == "manage_keys")
async def manage_keys_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user_keys = get_user_keys(user_id)
    await callback.message.edit_text(
        "Ваши ключи:" if user_keys else "У вас пока нет ключей, давайте создадим первый!",
        reply_markup=keyboards.create_keys_management_keyboard(user_keys)
    )

@user_router.callback_query(F.data == "toggle_autorenew")
async def toggle_autorenew_handler(callback: types.CallbackQuery, state: FSMContext):
    from shop_bot.data_manager.database import (
        get_yookassa_autopay,
        get_yookassa_payment_method_id,
        set_yookassa_autopay_enabled,
    )
    from shop_bot.yookassa_autopay import (
        autopay_amount_rub,
        autopay_interval_days,
        create_bind_payment,
    )

    uid = callback.from_user.id
    info = get_yookassa_autopay(uid)
    enabled = bool(info.get("yookassa_autopay_enabled"))

    if enabled:
        await callback.answer("Автоплатёж отключён")
        set_yookassa_autopay_enabled(uid, False)
        log_action(uid, "autopay_off", "user")
        await show_main_menu(callback.message, edit_message=True)
        return

    if not await _ensure_terms_callback(callback, state):
        return

    if not (PAYMENT_METHODS or {}).get("yookassa"):
        await callback.answer("Оплата картой недоступна", show_alert=True)
        return

    pm_id = get_yookassa_payment_method_id(uid)
    if pm_id:
        await callback.answer("Автоплатёж включён")
        set_yookassa_autopay_enabled(uid, True)
        from shop_bot.data_manager.database import schedule_yookassa_autopay_next

        schedule_yookassa_autopay_next(uid, days=autopay_interval_days())
        log_action(uid, "autopay_on", "existing_pm")
        await show_main_menu(callback.message, edit_message=True)
        return

    await callback.answer()
    amount = autopay_amount_rub()
    url, err = create_bind_payment(uid)
    if not url:
        await callback.message.answer(
            "❌ Не удалось создать платёж для автопродления.\n" + user_messages.ERR_PAYMENT_LINK
        )
        return
    log_action(uid, "autopay_bind_start", str(amount))
    await callback.message.edit_text(
        user_messages.msg_autopay_bind_offer(amount, autopay_interval_days()),
        reply_markup=keyboards.create_payment_keyboard(url),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@user_router.callback_query(F.data.startswith("traffic_packs_"))
async def show_traffic_packs(callback: types.CallbackQuery):
    await callback.answer()
    key_id = int(callback.data.split('_')[2])
    await callback.message.edit_text("Выберите пакет дополнительного трафика:", reply_markup=keyboards.create_traffic_packs_keyboard(TRAFFIC_PACKS, key_id))

@user_router.callback_query(F.data.startswith("buy_pack_"))
async def buy_traffic_pack(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer()
    parts = callback.data.split('_')
    pack_id = parts[2]
    key_id = int(parts[3])
    if pack_id not in TRAFFIC_PACKS:
        await callback.message.edit_text("Пакет не найден", reply_markup=keyboards.create_back_to_key_keyboard(key_id))
        return
    title, price_rub, gb = TRAFFIC_PACKS[pack_id]
    # Используем платеж только как "extend" с особыми метаданными action=pack
    payment_methods = PAYMENT_METHODS
    await callback.message.edit_text(
        f"Покупка пакета: {title}\nОбъем: {gb} ГБ\nЦена: {price_rub} RUB\nВыберите способ оплаты:",
        reply_markup=keyboards.create_payment_method_keyboard(payment_methods, pack_id, "pack", key_id)
    )

@user_router.callback_query(F.data == "enter_promo")
async def enter_promo_info(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Вы можете ввести промокод перед оплатой. Нажмите кнопку ниже.", reply_markup=keyboards.create_promo_enter_keyboard())

@user_router.callback_query(F.data == "enter_promo_start")
async def enter_promo_start(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer()
    await state.set_state(PromoInput.waiting_for_code)
    await callback.message.edit_text("Введите промокод одним сообщением:")

@user_router.message(PromoInput.waiting_for_code)
async def promo_code_received(message: types.Message, state: FSMContext):
    code = (message.text or '').strip()
    promo = get_promo(code)
    if not promo:
        await message.answer("❌ " + user_messages.MSG_PROMO_INVALID)
        return
    await state.update_data(promo_code=code)
    discount = promo.get('discount_percent', 0)
    free_days = promo.get('free_days', 0)
    parts = []
    if discount:
        parts.append(f"Скидка {discount}%")
    if free_days:
        parts.append(f"+{free_days} дней")
    await message.answer("✅ Промокод принят: " + ", ".join(parts) + "\nОн будет применён к следующей оплате.")
    await state.clear()
    await show_main_menu(message)

@user_router.callback_query(F.data == "get_trial")
async def trial_period_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer("Проверяю доступность...", show_alert=False)
    user_id = callback.from_user.id
    user_db_data = get_user(user_id)
    if user_db_data and user_db_data.get('trial_used'):
        await callback.answer("Вы уже использовали бесплатный пробный период.", show_alert=True)
        return

    await callback.message.edit_text("Создаю твой VPN… ⏳")
    try:
        key_number = get_next_key_number(user_id)
        email = f"user{user_id}-key{key_number}-trial@{KEY_EMAIL_DOMAIN}"
        uri, expire_iso, vless_uuid, sub_url = await remnawave_api.provision_key(
            email, days=REMNA_TRIAL_DAYS, telegram_id=str(user_id))
        if not uri or not expire_iso or not vless_uuid:
            await callback.message.edit_text("❌ " + user_messages.ERR_TRIAL_CREATE)
            return
        # convert ISO to timestamp ms for storage
        expiry_dt = datetime.fromisoformat(expire_iso.replace('Z', '+00:00'))
        expiry_ms = int(expiry_dt.timestamp() * 1000)
        new_key_id = add_new_key(user_id, vless_uuid, email, expiry_ms)
        # TRIAL-GRANT-ATOMIC-001: mark trial used only AFTER the key is persisted,
        # so a crash before this point never leaves trial_used=1 with no key.
        set_trial_used(user_id)
        from shop_bot.subscription_cache import invalidate_subscription_url_cache

        invalidate_subscription_url_cache(user_id)

        # Показываем созданный ключ пользователю
        expiry_str = expiry_dt.strftime("%d.%m.%Y")
        from shop_bot.onboarding_copy import t as ob_t

        message_text = (
            f"<b>{ob_t('trial_activated')}</b>\n\n"
            f"Доступ активен до <b>{expiry_str}</b>."
        )
        
        await callback.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboards.create_trial_success_keyboard(
                sub_url or uri, telegram_id=user_id
            ),
        )
        from shop_bot.onboarding_flow import prompt_email_after_trial

        await prompt_email_after_trial(callback.message, state)
    except Exception as e:
        logger.error(f"Error creating trial key for user {user_id}: {e}", exc_info=True)
        # TRIAL-GRANT-ATOMIC-001: trial_used is set only after a key is persisted,
        # so no reset is needed here — an early failure never consumed the trial,
        # and a late failure must not hand out a second trial for an existing key.
        await callback.message.edit_text("❌ " + user_messages.ERR_TRIAL_CREATE)

@user_router.callback_query(F.data == "open_admin_panel")
async def open_admin_panel_handler(callback: types.CallbackQuery):
    if not is_admin_telegram(callback.from_user.id):
        await callback.answer("У вас нет доступа.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "Добро пожаловать в админ-панель!",
        reply_markup=keyboards.create_admin_keyboard(),
    )


@user_router.callback_query(F.data == "my_account")
async def my_account_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user_db_data = get_user(user_id)
    user_keys = get_user_keys(user_id)
    now = datetime.now()
    balance = get_balance(user_id)
    days_left = balance_to_days(balance)
    active_keys = [k for k in user_keys if datetime.fromisoformat(k["expiry_date"]) > now]
    sub_url = None
    if active_keys:
        sub_url = await _fetch_subscription_url(user_id)
        latest = max(active_keys, key=lambda k: datetime.fromisoformat(k["expiry_date"]))
        exp = datetime.fromisoformat(latest["expiry_date"])
        text = (
            f"Активен до {exp.strftime('%d.%m.%Y')}.\n\n"
            f"Баланс: {balance:.0f} ₽ — примерно {days_left} дней.\n\n"
            "Конфигурация ниже. Если меняешь устройство или что-то перестало работать — напиши нам."
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboards.create_account_keyboard(sub_url, telegram_id=user_id),
        )
    else:
        trial_available = not (user_db_data and user_db_data.get("trial_used"))
        if trial_available:
            text = (
                "Попробовать можно бесплатно — 90 дней, 1 устройство, без лимита трафика.\n\n"
                "Нажми «Получить бесплатный VPN» или «Активировать бесплатно» в меню."
            )
        else:
            text = (
                "Пробный период завершился.\n\n"
                f"Пополни баланс, чтобы продолжить — {format_daily_rate_ru()} ₽ в день. "
                "Конфигурация сохранена, заново настраивать ничего не нужно."
            )
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=keyboards.create_account_no_sub_keyboard(trial_available)
        )

@user_router.callback_query(F.data == "menu_get_setup")
async def menu_get_setup_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user_keys = get_user_keys(user_id)
    user_db = get_user(user_id)
    trial_available = not (user_db and user_db.get("trial_used"))
    if not user_keys and trial_available:
        await callback.message.edit_text(
            user_messages.MSG_SETUP_NEED_TRIAL,
            reply_markup=keyboards.create_trial_before_setup_keyboard(),
        )
        return
    setup_url, _setup_reason = await _wizard_setup_url(user_id)
    if not setup_url:
        from shop_bot.bot import portal_links

        setup_url = portal_links.public_setup_url()
    await callback.message.edit_text(
        user_messages.MSG_SETUP_LINK,
        reply_markup=keyboards.create_setup_link_keyboard(setup_url),
        disable_web_page_preview=True,
    )


@user_router.callback_query(F.data == "menu_help")
async def menu_help_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    setup_url, _ = await _wizard_setup_url(user_id)
    text = (
        "<b>Помощь</b>\n\n"
        "Инструкция и частые вопросы — кнопки ниже.\n\n"
        "Если пишет «0 серверов» — не удаляй профиль: нажми 🔄 в Happ рядом с ним, "
        "узлы появятся сами.\n\n"
        "На LTE не коннектится — команда <code>/help_connect</code>."
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboards.create_help_menu_keyboard(setup_url=setup_url),
    )


@user_router.callback_query(F.data == "contact_support")
async def contact_support_handler(callback: types.CallbackQuery):
    await callback.answer()
    from shop_bot.bot import support_handler

    if support_handler._support_disabled_for_user():
        await callback.message.answer(
            support_handler.MSG_SUPPORT_DISABLED,
            parse_mode="HTML",
        )
        return
    await callback.message.answer(
        user_messages.MSG_SUPPORT_PROMPT,
        parse_mode="HTML",
    )

@user_router.callback_query(F.data == "invite_friend")
async def invite_friend_handler(callback: types.CallbackQuery):
    await callback.answer()
    if not REFERRAL_UI_ENABLED:
        await callback.message.edit_text(
            "Раздел приглашений пока недоступен.",
            reply_markup=keyboards.create_back_to_menu_keyboard(),
        )
        return
    await present_referral_invite(
        callback.message, callback.bot, callback.from_user.id, edit=True
    )


@user_router.message(Command("invite"))
async def invite_command_handler(message: types.Message):
    if not REFERRAL_UI_ENABLED:
        await message.answer(
            "Раздел приглашений пока недоступен.",
            reply_markup=keyboards.create_back_to_menu_keyboard(),
        )
        return
    await present_referral_invite(
        message, message.bot, message.chat.id, edit=False
    )


@user_router.message(Command("help_connect"))
async def help_connect_handler(message: types.Message):
    """VPN-AUD-370: TSPU/LTE recovery — alt nodes + full-matrix clients."""
    user_id = message.from_user.id
    register_user_if_not_exists(user_id, message.from_user.username or message.from_user.full_name)
    log_action(user_id, "help_connect", "cmd")
    user_data = get_user(user_id)
    if not user_data or not user_data.get("agreed_to_terms"):
        await message.answer(
            "Сначала нажми /start и прими условия — потом вернись сюда.",
            parse_mode="HTML",
        )
        return
    try:
        sub_url = await _fetch_subscription_url(user_id)
    except Exception as exc:
        logger.warning("help_connect fetch sub tid=%s: %s", user_id, exc)
        sub_url = None
    if not sub_url:
        from shop_bot.subscription_resolve import subscription_unavailable

        hint = subscription_unavailable(user_id)
        await message.answer(f"❌ {hint['message']}", parse_mode="HTML")
        return
    await message.answer(
        user_messages.msg_help_connect(sub_url),
        parse_mode="HTML",
        reply_markup=keyboards.create_help_connect_keyboard(),
    )


@user_router.callback_query(F.data == "copy_ref_url")
async def copy_ref_url_handler(callback: types.CallbackQuery):
    await callback.answer("Ссылка в следующем сообщении")
    text, ref_url = await referral_invite_payload(callback.bot, callback.from_user.id)
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboards.create_referral_keyboard(ref_url),
    )


@user_router.callback_query(F.data == "copy_sub_url")
async def copy_sub_url_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    try:
        sub_url = await _fetch_subscription_url(user_id)
        if sub_url:
            await callback.message.answer(
                f"Скопируй эту ссылку и вставь в Happ:\n(+ → «Из буфера обмена»)\n\n`{sub_url}`",
                parse_mode="Markdown",
            )
        else:
            from shop_bot.subscription_resolve import subscription_unavailable

            hint = subscription_unavailable(user_id)
            await callback.message.answer(f"❌ {hint['message']}")
    except Exception as e:
        logger.error(f"Error in copy_sub_url: {e}")
        await callback.message.answer("❌ " + user_messages.ERR_GENERIC_RETRY)


@user_router.callback_query(F.data == "show_sub_qr")
async def show_sub_qr_handler(callback: types.CallbackQuery):
    from shop_bot.subscription_qr import subscription_qr_png

    await callback.answer()
    user_id = callback.from_user.id
    try:
        sub_url = await _fetch_subscription_url(user_id)
        if not sub_url:
            from shop_bot.subscription_resolve import subscription_unavailable

            hint = subscription_unavailable(user_id)
            await callback.message.answer(f"❌ {hint['message']}")
            return
        png = subscription_qr_png(sub_url)
        await callback.message.answer_photo(
            BufferedInputFile(png, filename="happ_sub_qr.png"),
            caption=(
                "Открой камеру телефона → наведи на QR → нажми Connect в Happ.\n\n"
                "Или скопируй ссылку кнопкой ниже."
            ),
            parse_mode="HTML",
        )
        log_action(user_id, "show_sub_qr", "ok")
    except Exception as e:
        logger.error("show_sub_qr failed for %s: %s", user_id, e)
        await callback.message.answer("❌ " + user_messages.ERR_QR)

@user_router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: types.CallbackQuery):
    if not is_admin_telegram(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    from shop_bot.data_manager.database import get_admin_stats, get_last_backup_timestamp
    stats = get_admin_stats()
    last_backup = get_last_backup_timestamp() or '—'
    
    # Красивое форматирование статистики
    users_count = stats.get('users_count', 0)
    active_keys = stats.get('active_keys', 0)
    total_keys = stats.get('total_keys', 0)
    total_months = stats.get('total_months', 0)
    total_spent = stats.get('total_spent', 0)
    active_promos = stats.get('active_promos', 0)
    total_referrals = stats.get('total_referrals', 0)
    
    # Процент активных ключей
    keys_percentage = round((active_keys / total_keys * 100) if total_keys > 0 else 0, 1)
    
    text = (
        "📊 <b>СТАТИСТИКА БОТА</b>\n"
        "═══════════════════════\n\n"
        
        "👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        f"├ Всего пользователей: <code>{users_count:,}</code>\n"
        f"└ Рефералов привлечено: <code>{total_referrals:,}</code>\n\n"
        
        "🔑 <b>VPN КЛЮЧИ</b>\n"
        f"├ Активных: <code>{active_keys:,}</code> / <code>{total_keys:,}</code>\n"
        f"├ Процент активности: <code>{keys_percentage}%</code>\n"
        f"└ {'🟢' if keys_percentage > 50 else '🟡' if keys_percentage > 25 else '🔴'} "
        f"{'Отлично' if keys_percentage > 50 else 'Нормально' if keys_percentage > 25 else 'Требует внимания'}\n\n"
        
        "💰 <b>ПРОДАЖИ</b>\n"
        f"├ Общая выручка: <code>{total_spent:,.2f} RUB</code>\n"
        f"├ Продано месяцев: <code>{total_months:,}</code>\n"
        f"└ Средний чек: <code>{(total_spent/users_count if users_count > 0 else 0):,.2f} RUB</code>\n\n"
        
        "🎫 <b>ПРОМОКОДЫ</b>\n"
        f"└ Активных: <code>{active_promos:,}</code>\n\n"
        
        "💾 <b>СИСТЕМА</b>\n"
        f"└ Последний бэкап: <code>{last_backup}</code>\n\n"
        
        "═══════════════════════\n"
        f"📅 Обновлено: <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.create_admin_keyboard())

@user_router.callback_query(F.data == "admin_backup")
async def admin_backup_handler(callback: types.CallbackQuery):
    if not is_admin_telegram(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer("Создаю бэкап...")
    
    # Изменяем сообщение, чтобы показать прогресс
    try:
        await callback.message.edit_text("⏳ Создание бэкапа...", reply_markup=None)
    except Exception:
        pass  # Игнорируем ошибки редактирования
    
    # Используем универсальную функцию для создания бэкапа
    success = await create_backup_and_send(callback.bot, ADMIN_TELEGRAM_ID, is_auto=False)
    
    if success:
        final_text = "✅ Бэкап создан на сервере (в TG — только при ошибке)."
    else:
        final_text = "❌ " + user_messages.ERR_ADMIN_BACKUP
    
    try:
        await callback.message.edit_text(final_text, reply_markup=keyboards.create_admin_keyboard())
    except Exception:
        # Если не удается отредактировать, отправляем новое сообщение
        await callback.message.answer(final_text, reply_markup=keyboards.create_admin_keyboard())

@user_router.callback_query(F.data == "admin_promos")
async def admin_promos_menu(callback: types.CallbackQuery):
    if not is_admin_telegram(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await callback.message.edit_text("Управление промокодами:", reply_markup=keyboards.create_admin_promos_keyboard())

@user_router.callback_query(F.data == "admin_promo_create")
async def admin_promo_create_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin_telegram(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await state.set_state(PromoCreate.waiting_for_code)
    await callback.message.edit_text("Введите код промокода (латиница/цифры):")

@user_router.message(PromoCreate.waiting_for_code)
async def admin_promo_code(message: types.Message, state: FSMContext):
    if not is_admin_telegram(message.from_user.id):
        await state.clear()
        return
    code = (message.text or '').strip()
    if not code or len(code) > 32:
        await message.answer("Некорректный код, попробуйте снова.")
        return
    await state.update_data(code=code)
    await state.set_state(PromoCreate.waiting_for_discount)
    await message.answer("Введите скидку % (0 если не нужна):")

@user_router.message(PromoCreate.waiting_for_discount)
async def admin_promo_discount(message: types.Message, state: FSMContext):
    if not is_admin_telegram(message.from_user.id):
        await state.clear()
        return
    try:
        disc = int(message.text)
        if disc < 0 or disc > 90:
            raise ValueError
    except Exception:
        await message.answer("Укажите число 0-90.")
        return
    await state.update_data(discount=disc)
    await state.set_state(PromoCreate.waiting_for_days)
    await message.answer("Введите бесплатные дни (0 если нет):")

@user_router.message(PromoCreate.waiting_for_days)
async def admin_promo_days(message: types.Message, state: FSMContext):
    if not is_admin_telegram(message.from_user.id):
        await state.clear()
        return
    try:
        days = int(message.text)
        if days < 0 or days > 365:
            raise ValueError
    except Exception:
        await message.answer("Укажите число 0-365.")
        return
    await state.update_data(free_days=days)
    await state.set_state(PromoCreate.waiting_for_limit)
    await message.answer("Введите лимит использований (0 = без лимита):")

@user_router.message(PromoCreate.waiting_for_limit)
async def admin_promo_limit(message: types.Message, state: FSMContext):
    if not is_admin_telegram(message.from_user.id):
        await state.clear()
        return
    try:
        limit = int(message.text)
        if limit < 0 or limit > 10000:
            raise ValueError
    except Exception:
        await message.answer("Укажите число 0-10000.")
        return
    data = await state.get_data()
    code = data['code']; disc = data['discount']; free_days = data['free_days']
    ok = create_promo(code, disc, free_days, limit)
    await state.clear()
    if ok:
        await message.answer(f"✅ Промокод '{code}' создан. Скидка {disc}%, +{free_days} дн., лимит {limit or '∞'}.")
    else:
        await message.answer("❌ " + user_messages.ERR_ADMIN_PROMO)
    await message.answer("Меню промокодов:", reply_markup=keyboards.create_admin_promos_keyboard())

@user_router.callback_query(F.data == "admin_promo_list")
async def admin_promo_list(callback: types.CallbackQuery):
    if not is_admin_telegram(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    promos = get_all_promos()
    if not promos:
        text = "Промокодов нет."
    else:
        lines = ["<b>Список промокодов</b>"]
        for p in promos:
            lines.append(f"{p['code']}: {p['discount_percent']}% / +{p['free_days']}д / использовано {p['uses_count']}/{p['uses_limit'] or '∞'} {'✅' if p['active'] else '⛔'}")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=keyboards.create_admin_promos_keyboard())

@user_router.callback_query(F.data.startswith("admin_promo_toggle_"))
async def admin_promo_toggle(callback: types.CallbackQuery):
    if not is_admin_telegram(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True); return
    code = callback.data.split("admin_promo_toggle_")[1]
    from shop_bot.data_manager.database import get_promo, set_promo_active
    p = get_promo(code)
    was_active = bool(p)
    # Если активен, выключаем; если не найден активный, пробуем включить (существует ли в общем списке)
    if was_active:
        set_promo_active(code, False)
        await callback.answer("Выключено")
    else:
        # нужен доступ к неактивным - получим напрямую
        from shop_bot.data_manager.database import db_connection
        restored = False
        try:
            with db_connection() as conn:
                c = conn.cursor(); c.execute("SELECT code FROM promo_codes WHERE code = ?", (code,))
                if c.fetchone():
                    set_promo_active(code, True); restored = True
        except Exception:
            pass
        await callback.answer("Включено" if restored else "Нет такого кода", show_alert=not restored)
    # Обновим список
    promos = get_all_promos()
    lines = ["<b>Список промокодов</b>"]
    for p in promos:
        lines.append(f"{p['code']}: {p['discount_percent']}% / +{p['free_days']}д / {p['uses_count']}/{p['uses_limit'] or '∞'} {'✅' if p['active'] else '⛔'}")
    await callback.message.edit_text("\n".join(lines), reply_markup=keyboards.create_admin_promos_keyboard())

@user_router.callback_query(F.data.startswith("show_key_"))
async def show_key_handler(callback: types.CallbackQuery):
    key_id_to_show = int(callback.data.split("_")[2])
    await callback.message.edit_text("Загружаю информацию о ключе...")
    user_id = callback.from_user.id
    key_data = get_key_by_id(key_id_to_show)

    if not key_data or key_data['user_id'] != user_id:
        await callback.message.edit_text("❌ " + user_messages.ERR_KEY_WRONG_USER)
        return
        
    try:
        # We cannot re-build original without inbound each time; fetch inbound once
        from shop_bot.modules.remnawave_api import get_inbound, build_vless_uri
        import aiohttp
        async with remnawave_api.remna_client_session() as session:
            inbound = await get_inbound(session)
            if not inbound:
                await callback.message.edit_text("❌ " + user_messages.ERR_INBOUND)
                return
            user_uuid = key_data['vless_uuid']
            email = key_data['key_email']
            connection_string = build_vless_uri(inbound, user_uuid, email)
            if not connection_string:
                await callback.message.edit_text("❌ " + user_messages.ERR_VLESS_BUILD)
                return
        expiry_date = datetime.fromisoformat(key_data['expiry_date'])
        created_date = datetime.fromisoformat(key_data['created_date'])
        all_user_keys = get_user_keys(user_id)
        key_number = next((i + 1 for i, key in enumerate(all_user_keys) if key['key_id'] == key_id_to_show), 0)
        final_text = get_key_info_text(key_number, expiry_date, created_date, connection_string)
        await callback.message.edit_text(text=final_text, reply_markup=keyboards.create_key_info_keyboard(key_id_to_show))
    except Exception as e:
        logger.error(f"Error showing key {key_id_to_show}: {e}")
        await callback.message.edit_text("❌ " + user_messages.ERR_KEY_FETCH)

@user_router.callback_query(F.data.startswith("show_qr_"))
async def show_qr_handler(callback: types.CallbackQuery):
    await callback.answer("Генерирую QR-код...")
    key_id = int(callback.data.split("_")[2])
    key_data = get_key_by_id(key_id)
    if not key_data or key_data['user_id'] != callback.from_user.id: return
    
    try:
        from shop_bot.modules.remnawave_api import get_inbound, build_vless_uri
        import aiohttp
        async with remnawave_api.remna_client_session() as session:
            inbound = await get_inbound(session)
            if not inbound: return
            connection_string = build_vless_uri(inbound, key_data['vless_uuid'], key_data['key_email'])
            if not connection_string: return

        qr_img = qrcode.make(connection_string)
        bio = BytesIO(); qr_img.save(bio, "PNG"); bio.seek(0)
        qr_code_file = BufferedInputFile(bio.read(), filename="vpn_qr.png")
        await callback.message.answer_photo(photo=qr_code_file)
    except Exception as e:
        logger.error(f"Error showing QR for key {key_id}: {e}")
        await callback.message.answer("❌ " + user_messages.ERR_QR)

@user_router.callback_query(F.data.startswith("show_instruction_"))
async def show_instruction_handler(callback: types.CallbackQuery):
    await callback.answer()
    key_id = int(callback.data.split("_")[2])

    instruction_text = (
        "<b>\U0001f4f1 Как установить:</b>\n\n"
        "1\ufe0f\u20e3 Скачай приложение Happ (кнопка ниже)\n\n"
        "2\ufe0f\u20e3 Открой Happ\n\n"
        "3\ufe0f\u20e3 Нажми + в правом верхнем углу\n\n"
        '4\ufe0f\u20e3 Выбери "Из буфера обмена"\n\n'
        "5\ufe0f\u20e3 Нажми кнопку питания \u2014 готово! \U0001f389\n\n"
        "Что-то не так? Напиши нам \U0001f447"
    )
    
    await callback.message.edit_text(
        instruction_text,
        reply_markup=keyboards.create_back_to_key_keyboard(key_id),
        disable_web_page_preview=True
    )

@user_router.callback_query(F.data == "buy_new_key")
async def buy_new_key_handler(callback: types.CallbackQuery, state: FSMContext):
    await show_topup_handler(callback, state)

@user_router.callback_query(F.data.startswith("extend_key_"))
async def extend_key_handler(callback: types.CallbackQuery, state: FSMContext):
    await show_topup_handler(callback, state)


@user_router.callback_query(F.data == "show_topup")
async def show_topup_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer()
    user_id = callback.from_user.id
    from shop_bot.onboarding_flow import prompt_email_before_payment, user_needs_contact_email

    if user_needs_contact_email(user_id):
        await prompt_email_before_payment(callback.message, state, edit=True)
        return
    await present_topup_screen(callback.message, user_id, edit=True)


async def present_topup_screen(
    message: types.Message, user_id: int, *, edit: bool = False
) -> None:
    balance = get_balance(user_id)
    days_left = balance_to_days(balance)
    text = (
        f"<b>Баланс: {balance:.0f} ₽</b> — примерно {days_left} дней доступа.\n"
        f"Списание: {format_daily_rate_ru()} ₽ в день, пока есть деньги на балансе.\n\n"
        "Выбери сумму пополнения:"
    )
    kb = keyboards.create_topup_keyboard()
    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@user_router.callback_query(F.data == "topup_custom")
async def topup_custom_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer()
    await state.set_state(CustomTopup.waiting_for_amount)
    await callback.message.edit_text(
        "Введи любую сумму — от 50 до 20 000 ₽.\n\n"
        f"Деньги зачислятся на баланс, а доступ будет списываться по {format_daily_rate_ru()} ₽ в день.\n\n"
        "200 ₽ — 30 дней, 2 000 ₽ — примерно 10 месяцев.",
        reply_markup=keyboards.create_back_to_menu_keyboard(),
        parse_mode="HTML",
    )


@user_router.message(CustomTopup.waiting_for_amount)
async def custom_topup_amount_handler(message: types.Message, state: FSMContext):
    raw = (message.text or "").strip().replace(",", ".").replace(" ", "").replace(" ", "")
    try:
        amount = float(raw)
    except (ValueError, AttributeError):
        await message.answer("Введи число — например: 500")
        return
    if amount < 50:
        await message.answer("Минимальная сумма — 50 ₽ (примерно 7 дней доступа).")
        return
    if amount > 20000:
        await message.answer("Максимальная сумма — 20 000 ₽.")
        return
    amount_int = int(round(amount))
    days = balance_to_days(amount_int)
    await state.clear()
    custom_topup_id = f"custom_{amount_int}"
    text = (
        f"Пополнение на <b>{amount_int} ₽</b> — примерно {days} дней доступа.\n\n"
        "Выбери способ оплаты:"
    )
    await message.answer(
        text,
        reply_markup=keyboards.create_topup_payment_keyboard(custom_topup_id, PAYMENT_METHODS),
        parse_mode="HTML",
    )
    log_action(message.from_user.id, "topup_custom_amount", str(amount_int))


@user_router.callback_query(F.data.in_({"topup_200", "topup_500", "topup_1000", "topup_2000"}))
async def topup_select_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer()
    topup_id = callback.data
    if topup_id not in TOPUP_PRESETS:
        return
    _name, _price_str, amount = TOPUP_PRESETS[topup_id]
    days = balance_to_days(amount)
    text = (
        f"Пополнение на <b>{amount:.0f} ₽</b> — примерно {days} дней доступа.\n\n"
        "Выбери способ оплаты:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.create_topup_payment_keyboard(topup_id, PAYMENT_METHODS),
        parse_mode="HTML",
    )


@user_router.callback_query(F.data.startswith("pay_stars_topup_"))
async def pay_stars_topup_disabled_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        user_messages.MSG_STARS_DISABLED,
        reply_markup=keyboards.create_topup_keyboard(),
        parse_mode="HTML",
    )


@user_router.callback_query(F.data.startswith("pay_yookassa_topup_"))
async def pay_yookassa_topup_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer("Создаю ссылку на оплату...")
    topup_id = callback.data.replace("pay_yookassa_topup_", "", 1)
    if topup_id.startswith("custom_"):
        try:
            amount_rub = float(topup_id[7:])
            price_str = f"{amount_rub:.2f}"
        except (ValueError, IndexError):
            await callback.message.edit_text(user_messages.ERR_GENERIC_RETRY)
            return
    elif topup_id in TOPUP_PRESETS:
        _name, price_str, amount_rub = TOPUP_PRESETS[topup_id]
    else:
        await callback.message.edit_text(user_messages.ERR_GENERIC_RETRY)
        return
    user_id = callback.from_user.id
    bot_username = TELEGRAM_BOT_USERNAME or os.getenv("TELEGRAM_BOT_USERNAME", "")
    return_url = f"https://t.me/{bot_username}" if bot_username else "https://t.me/"
    amount_value = f"{float(amount_rub):.2f}"
    description = f"Пополнение баланса BenderVPN {amount_rub:.0f} ₽"
    try:
        payment = Payment.create(
            {
                "amount": {"value": amount_value, "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": return_url},
                "capture": True,
                "description": description,
                "receipt": yookassa_receipt(description, amount_value, user_id),
                "metadata": {
                    "t": "topup",
                    "u": user_id,
                    "user_id": user_id,
                    "a": amount_value,
                    "amount": amount_value,
                },
            },
            uuid.uuid4(),
        )
        await callback.message.edit_text(
            f"💳 Оплата картой\n\n"
            f"<b>{amount_rub:.0f} ₽</b> — примерно {balance_to_days(amount_rub)} дней доступа.\n\n"
            "Нажми кнопку ниже:",
            reply_markup=keyboards.create_payment_keyboard(payment.confirmation.confirmation_url),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Failed to create YooKassa topup payment: %s", e, exc_info=True)
        await callback.message.edit_text("❌ " + user_messages.ERR_PAYMENT_LINK)


@user_router.callback_query(F.data.startswith("buy_") & F.data.contains("_month"))
async def choose_payment_method_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer()
    parts = callback.data.split("_")
    plan_id, action, key_id = "_".join(parts[:-2]), parts[-2], int(parts[-1])
    await callback.message.edit_text(
        CHOOSE_PAYMENT_METHOD_MESSAGE,
        reply_markup=keyboards.create_payment_method_keyboard(PAYMENT_METHODS, plan_id, action, key_id)
    )

@user_router.callback_query(
    F.data.startswith("pay_yookassa_") & ~F.data.startswith("pay_yookassa_topup_")
)
async def create_yookassa_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer("Создаю ссылку на оплату...")
    
    parts = callback.data.split("_")[2:]
    plan_id = "_".join(parts[:-2])
    action = parts[-2]
    key_id = int(parts[-1])
    
    if plan_id not in PLANS:
        await callback.message.answer("❌ " + user_messages.ERR_TARIFF_CHOICE)
        return

    name, price_rub, months = PLANS[plan_id]
    user_id = callback.from_user.id
    chat_id_to_delete = callback.message.chat.id
    message_id_to_delete = callback.message.message_id
    
    try:
        if months == 1:
            description = f"Оплата подписки на 1 месяц"
        elif months <= 5:
            description = f"Оплата подписки на {months} месяца"
        else:
            description = f"Оплата подписки на {months} месяцев"
        data = await state.get_data()
        promo_code = data.get('promo_code')
        amount_value = price_rub
        if promo_code:
            promo = get_promo(promo_code)
            if promo:
                disc = promo.get('discount_percent', 0)
                if disc and 0 < disc < 100:
                    amount_value = f"{float(price_rub) * (100-disc)/100:.2f}"
        payment = Payment.create({
            "amount": {"value": amount_value, "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": f"https://t.me/{TELEGRAM_BOT_USERNAME}"},
            "capture": True,
            "description": description,
            "receipt": yookassa_receipt(description, amount_value, user_id),
            "metadata": {
                "user_id": user_id, "months": months, "price": amount_value,
                "action": action, "key_id": key_id,
                "chat_id": chat_id_to_delete, "message_id": message_id_to_delete,
                "plan_id": plan_id,
                "promo_code": promo_code
            }
        }, uuid.uuid4())
        await callback.message.edit_text(
            "Нажмите на кнопку ниже для оплаты:",
            reply_markup=keyboards.create_payment_keyboard(payment.confirmation.confirmation_url)
        )
    except Exception as e:
        logger.error(f"Failed to create YooKassa payment: {e}", exc_info=True)
        await callback.message.answer("❌ " + user_messages.ERR_PAYMENT_LINK)

def create_heleket_signature(payload: dict, api_key: str) -> str:
    """
    Создает сигнатуру для API Heleket на основе рабочего примера.
    Использует жестко заданный, отсортированный список ключей для 100% надежности.
    """
    # 1. Жестко заданный список ключей в алфавитном порядке, как в рабочем примере.
    # Это гарантирует правильный порядок и исключает лишние поля вроде 'metadata'.
    keys_for_sign = [
        'amount', 
        'callback_url', 
        'currency', 
        'description', 
        'fail_url', 
        'merchant_id', 
        'order_id', 
        'success_url'
    ]
    
    # 2. Собираем список значений в правильном порядке.
    # Используем простое преобразование в строку str(), как в примере.
    values = [str(payload[key]) for key in keys_for_sign]
    
    # 3. Соединяем значения через двоеточие.
    sign_string = ":".join(values)
    
    # 4. Добавляем API-ключ и хэшируем.
    string_to_hash = sign_string + api_key
    return hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()

@user_router.callback_query(F.data.startswith("pay_crypto_"))
async def create_crypto_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    if not await _ensure_terms_callback(callback, state):
        return
    await callback.answer("Создаю счет для оплаты в криптовалюте...")
    
    # Ваша логика парсинга callback.data остается без изменений
    parts = callback.data.split("_")[2:]
    plan_id = "_".join(parts[:-2])
    action = parts[-2]
    key_id = int(parts[-1])

    if plan_id not in PLANS:
        await callback.message.answer("❌ " + user_messages.ERR_TARIFF_CHOICE)
        return

    name, price_rub, months = PLANS[plan_id]
    user_id = callback.from_user.id
    
    # Получаем URL для вебхуков и имя бота из переменных окружения
    crypto_webhook_url = os.getenv("CRYPTO_WEBHOOK_URL")
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME") # Убедитесь, что эта переменная есть

    try:
        if months == 1:
            description = f"Оплата подписки на 1 месяц"
        elif months <= 4:
            description = f"Оплата подписки на {months} месяца"
        else:
            description = f"Оплата подписки на {months} месяцев"
            
        async with remnawave_api.remna_client_session() as session:
            # 1. Формируем payload со всеми необходимыми полями
            data_state = await state.get_data()
            promo_code = data_state.get('promo_code')
            amount_value = float(price_rub)
            if promo_code:
                promo = get_promo(promo_code)
                if promo:
                    disc = promo.get('discount_percent', 0)
                    if disc and 0 < disc < 100:
                        amount_value = round(float(price_rub) * (100-disc)/100, 2)
            payload = {
                # ---- Поля, участвующие в подписи ----
                "merchant_id": CRYPTO_MERCHANT_ID,
                "amount": amount_value, # со скидкой при наличии
                "currency": "RUB",
                "order_id": str(uuid.uuid4()),
                "description": description,
                "callback_url": crypto_webhook_url,
                "success_url": f"https://t.me/{bot_username}",
                "fail_url": f"https://t.me/{bot_username}",
                # ---- Поля, НЕ участвующие в подписи ----
                "metadata": {
                    "user_id": user_id, "months": months, "price": amount_value, 
                    "action": action, "key_id": key_id,
                    "chat_id": callback.message.chat.id, 
                    "message_id": callback.message.message_id,
                    "plan_id": plan_id,
                    "promo_code": promo_code
                }
            }

            # 2. Создаем подпись с помощью нашей новой, надежной функции
            signature = create_heleket_signature(payload, CRYPTO_API_KEY)

            # 3. Добавляем подпись в payload для отправки
            payload["sign"] = signature
            
            headers = {"Content-Type": "application/json"}
            api_url = "https://api.heleket.com/v1/payment"
            
            # Отладочный вывод финального payload перед отправкой
            # logger.info(f"Sending payload to Heleket: {payload}")
            
            async with session.post(api_url, json=payload, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 201:
                    data = json.loads(response_text)
                    payment_url = data.get("pay_url")
                    
                    if not payment_url:
                        logger.error(f"Heleket API success, but no pay_url in response: {response_text}")
                        await callback.message.edit_text("❌ " + user_messages.ERR_PAYMENT_LINK)
                        return

                    await callback.message.edit_text(
                        "✅ Счет создан!\n\nНажмите на кнопку ниже для оплаты криптовалютой:",
                        reply_markup=keyboards.create_payment_keyboard(payment_url)
                    )
                else:
                    logger.error(f"Heleket API error: {response.status} - {response_text}")
                    await callback.message.edit_text("❌ " + user_messages.ERR_PAY_CRYPTO_GATEWAY)

    except Exception as e:
        logger.error(f"Exception during crypto payment creation: {e}", exc_info=True)
        await callback.message.edit_text("❌ " + user_messages.ERR_PAYMENT_CRITICAL)

@user_router.callback_query(
    F.data.startswith("pay_stars_") & ~F.data.startswith("pay_stars_topup_")
)
async def pay_stars_plan_disabled_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        user_messages.MSG_STARS_DISABLED,
        reply_markup=keyboards.create_back_to_menu_keyboard(),
        parse_mode="HTML",
    )


@user_router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    if pre_checkout_query.currency == "XTR":
        await pre_checkout_query.answer(
            ok=False,
            error_message="Оплата звёздами отключена. Пополни баланс картой в боте.",
        )
        return
    await pre_checkout_query.answer(ok=True)

@user_router.message(F.successful_payment)
async def successful_payment_handler(message: types.Message, bot: Bot):
    """Обрабатываем успешную оплату звездами"""
    payment = message.successful_payment
    
    try:
        user_id = message.from_user.id
        bot_logger.payment(user_id, "TELEGRAM_STARS", payment.total_amount, "RECEIVED")
        
        payload_data = json.loads(payment.invoice_payload)
        
        # Конвертируем сокращенные ключи обратно в полные для совместимости с process_successful_payment
        metadata = {
            "user_id": payload_data.get("u"),
            "months": payload_data.get("m"),
            "price": payload_data.get("p"),
            "action": payload_data.get("a"),
            "key_id": payload_data.get("k"),
            "plan_id": payload_data.get("pl"),
            "promo_code": payload_data.get("pr"),
            "chat_id": payload_data.get("c"),
            "message_id": payload_data.get("mid")
        }
        
        logger.info(f"Converted metadata: {metadata}")

        if payload_data.get("t") == "topup":
            amount_rub = float(payload_data.get("a", 0))
            charge_id = getattr(payment, "telegram_payment_charge_id", None) or payment.provider_payment_charge_id
            idem = f"topup_charge:{charge_id}" if charge_id else None
            await process_topup_payment(
                bot, user_id, amount_rub, idempotency_key=idem, notify=True
            )
            bot_logger.payment(user_id, "TELEGRAM_STARS", payment.total_amount, "SUCCESS")
            return

        await process_successful_payment(bot, metadata)
        bot_logger.payment(user_id, "TELEGRAM_STARS", payment.total_amount, "SUCCESS")
    except Exception as e:
        bot_logger.payment(message.from_user.id, "TELEGRAM_STARS", payment.total_amount, "FAILED")
        logger.error(f"Error processing stars payment: {e}", exc_info=True)
        await message.answer("❌ " + user_messages.ERR_PAYMENT_PROCESS_SUPPORT)

async def process_successful_payment(bot: Bot, metadata: dict):
    webhook_idem = metadata.get("webhook_idempotency_key")
    user_id, months, price, action, key_id = map(metadata.get, ['user_id', 'months', 'price', 'action', 'key_id'])
    user_id, months, price, key_id = int(user_id), int(months or 0), float(price), int(key_id)
    if webhook_idem and has_action(user_id, webhook_idem):
        logger.info("Duplicate webhook payment ignored: user=%s key=%s", user_id, webhook_idem)
        return
    promo_code = metadata.get('promo_code')
    plan_id_meta = metadata.get('plan_id')
    chat_id_to_delete = metadata.get('chat_id')
    message_id_to_delete = metadata.get('message_id')
    
    bot_logger.user_action(user_id, "PAYMENT_PROCESSING", f"{action} {months}m {price}₽")
    
    if chat_id_to_delete and message_id_to_delete:
        try:
            await bot.delete_message(chat_id=chat_id_to_delete, message_id=message_id_to_delete)
        except TelegramBadRequest as e:
            logger.warning(f"Could not delete payment message: {e}")

    processing_message = await bot.send_message(chat_id=user_id, text="✅ Оплата получена! Обрабатываю ваш запрос...")
    try:
        if action == 'pack':
            # find GB amount from TRAFFIC_PACKS
            pack = TRAFFIC_PACKS.get(metadata.get('plan_id') or metadata.get('pack_id') or metadata.get('action_id') or '')
            if not pack:
                # fallback parse plan id from metadata (YooKassa doesn't add plan id separately, so months misused). We encoded pack id as plan_id
                pack_id = metadata.get('plan_id') or metadata.get('pack_id') or metadata.get('action')
                pack = TRAFFIC_PACKS.get(pack_id, None)
            if not pack:
                await processing_message.edit_text("❌ " + user_messages.ERR_TRAFFIC_PACK_MISSING)
                return
            title, price_label, gb = pack
            key_data = get_key_by_id(key_id)
            if not key_data or key_data['user_id'] != user_id:
                await processing_message.edit_text("❌ " + user_messages.ERR_KEY_WRONG_USER)
                return
            email = key_data['key_email']
            server_ok = await add_extra_traffic(email, gb)
            if server_ok:
                add_traffic_extra(key_id, gb)
                log_action(user_id, 'traffic_pack', f"{key_id}:{gb}")
                await processing_message.delete()
                await bot.send_message(user_id, f"✅ Доп. трафик {gb} ГБ добавлен к ключу #{key_id}.")
            else:
                await processing_message.edit_text("❌ " + user_messages.ERR_EXTRA_TRAFFIC_PANEL)
            return
        days_to_add = months * 30
        email = ""
        key_number = 0
        if action == "new":
            key_number = get_next_key_number(user_id)
            email = f"user{user_id}-key{key_number}@{KEY_EMAIL_DOMAIN}"
        elif action == "extend":
            key_data = get_key_by_id(key_id)
            if not key_data or key_data['user_id'] != user_id:
                await processing_message.edit_text("❌ " + user_messages.ERR_KEY_WRONG_USER)
                return
            all_user_keys = get_user_keys(user_id)
            key_number = next((i + 1 for i, key in enumerate(all_user_keys) if key['key_id'] == key_id), 0)
            email = key_data['key_email']
        # Promo / referral adjustments
        if promo_code:
            promo = get_promo(promo_code)
            if promo:
                free_days = promo.get('free_days', 0)
                discount_percent = promo.get('discount_percent', 0)
                if free_days:
                    days_to_add += free_days
                if discount_percent and discount_percent > 0 and discount_percent < 100:
                    discounted = round(price * (100 - discount_percent) / 100, 2)
                    log_action(user_id, 'price_discount_applied', f"{price}->{discounted}({discount_percent}%)")
                    price = discounted
                apply_promo_usage(promo_code)
                log_action(user_id, 'promo_used', promo_code)
        if not has_action(user_id, 'first_purchase'):
            log_action(user_id, 'first_purchase')
            u = get_user(user_id)
            referrer_code = u.get('referred_by') if u else None
            # P1-REF-002: legacy invitee bonus gated OFF on prod hot-patch (helper not in live config).
            invitee_bonus_days = 0
            if invitee_bonus_days:
                days_to_add += invitee_bonus_days
                log_action(user_id, 'ref_bonus_received', referrer_code)
        uri, expire_iso, vless_uuid, sub_url = await remnawave_api.provision_key(
            email, 
            days=days_to_add, 
            telegram_id=str(user_id)
        )
        if not uri or not expire_iso or not vless_uuid:
            await processing_message.edit_text("❌ " + user_messages.ERR_SERVER_KEY_UPDATE)
            return
        expiry_dt = datetime.fromisoformat(expire_iso.replace('Z', '+00:00'))
        expiry_ms = int(expiry_dt.timestamp() * 1000)
        if action == "new":
            key_id = add_new_key(user_id, vless_uuid, email, expiry_ms)
            if plan_id_meta:
                from shop_bot.data_manager.database import set_key_plan
                set_key_plan(key_id, plan_id_meta)
        elif action == "extend":
            update_key_info(key_id, vless_uuid, expiry_ms)
            if plan_id_meta:
                from shop_bot.data_manager.database import set_key_plan
                set_key_plan(key_id, plan_id_meta)
        update_user_stats(user_id, price, months)
        from shop_bot.subscription_cache import invalidate_subscription_url_cache

        invalidate_subscription_url_cache(user_id)
        if promo_code:
            log_action(user_id, 'purchase_with_promo', f"{promo_code}:{price}:{months}")
        else:
            log_action(user_id, 'purchase', f"{price}:{months}")
        if webhook_idem:
            log_action(user_id, webhook_idem, f"{price}:{months}")
        await processing_message.delete()
        final_text = get_purchase_success_text(action=action, key_number=key_number, expiry_date=expiry_dt, connection_string=uri)
        await bot.send_message(chat_id=user_id, text=final_text, reply_markup=keyboards.create_key_info_keyboard(key_id))
    # FSM промокода очищается после применения при вводе; отдельное хранение не требуется.
    except Exception as e:
        logger.error(f"Error processing payment for user {user_id}: {e}", exc_info=True)
        await processing_message.edit_text("❌ " + user_messages.ERR_SERVER_KEY_UPDATE)

