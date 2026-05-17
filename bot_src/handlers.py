import logging
import uuid
from io import BytesIO
from datetime import datetime, timedelta, timezone
import qrcode
from yookassa import Payment
import aiohttp
import os
import hashlib
import json
import tarfile
import shutil
from pathlib import Path

from aiogram import Bot, Router, F, types, html
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

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
from shop_bot.config import (
    PLANS, get_profile_text, get_vpn_active_text, VPN_INACTIVE_TEXT, VPN_NO_DATA_TEXT,
    get_key_info_text, CHOOSE_PAYMENT_METHOD_MESSAGE, get_purchase_success_text, ABOUT_TEXT, TERMS_URL, PRIVACY_URL, SUPPORT_USER, SUPPORT_TEXT,
    REMNA_TRIAL_DAYS, DAILY_RATE, TOPUP_PRESETS, CUSTOM_AMOUNT_UNAVAILABLE, KEY_EMAIL_DOMAIN,
    balance_to_days,
)
from shop_bot.config import TRAFFIC_PACKS
from shop_bot.modules.remnawave_api import add_extra_traffic

TELEGRAM_BOT_USERNAME = None
CRYPTO_API_KEY = None
CRYPTO_MERCHANT_ID = None
PAYMENT_METHODS = None
PLANS = None
ADMIN_ID = os.getenv("ADMIN_TELEGRAM_ID")

logger = logging.getLogger(__name__)

# Импорт красивого логгера
from shop_bot.utils.logger import bot_logger


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
    if idempotency_key and has_action(user_id, idempotency_key):
        logger.info("Duplicate topup ignored: user=%s key=%s", user_id, idempotency_key)
        return False

    add_balance(user_id, amount_rub)
    new_balance = get_balance(user_id)
    days_left = balance_to_days(new_balance)
    synced = await sync_panel_access_from_balance(user_id, new_balance)
    update_user_stats(user_id, amount_rub, 0)
    log_action(user_id, "topup", f"{amount_rub}")
    if idempotency_key:
        log_action(user_id, idempotency_key, f"{amount_rub}")

    if notify:
        sync_note = "" if synced else (
            "\n\n⚠️ Баланс зачислен; синхронизация с панелью не удалась — напишите в поддержку."
        )
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Баланс пополнен на {amount_rub:.0f} ₽\n\n"
                f"💰 Текущий баланс: {new_balance:.0f} ₽\n"
                f"📅 Хватит на: ~{days_left} дн. ({DAILY_RATE:.2f} ₽/день)"
                f"{sync_note}"
            ),
            parse_mode="HTML",
        )
    return synced


async def sync_panel_access_from_balance(user_id: int, balance: float) -> bool:
    """Продлить доступ на панели по текущему балансу (balance / DAILY_RATE дней)."""
    days = balance_to_days(balance)
    if days <= 0:
        return False
    keys = get_user_keys(user_id)
    email = None
    if keys:
        email = keys[0]["key_email"]
    else:
        key_number = get_next_key_number(user_id)
        email = f"user{user_id}-key{key_number}@{KEY_EMAIL_DOMAIN}"
    uri, expire_iso, vless_uuid, _sub_url = await remnawave_api.provision_key(
        email, days=days, telegram_id=str(user_id)
    )
    if not uri or not expire_iso or not vless_uuid:
        return False
    expiry_dt = datetime.fromisoformat(expire_iso.replace("Z", "+00:00"))
    expiry_ms = int(expiry_dt.timestamp() * 1000)
    if keys:
        update_key_info(keys[0]["key_id"], vless_uuid, expiry_ms)
    else:
        add_new_key(user_id, vless_uuid, email, expiry_ms)
    return True

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
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_part_aa"
        
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
        
        # Получаем реальный IP сервера
        server_ip = "168.100.11.140"  # Можно вынести в env переменную
        
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
    
    trial_available = not (user_db_data and user_db_data.get('trial_used'))
    is_admin = str(user_id) == ADMIN_ID

    text = "🏠 <b>Главное меню</b>\n\nВыберите действие:"
    auto_renew = get_auto_renew(user_id) if user_db_data else False
    keyboard = keyboards.create_main_menu_keyboard(user_keys, trial_available, is_admin, auto_renew=auto_renew)
    
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

@user_router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    # Referral parsing /start ref_<code>
    ref_code = None
    if message.text and ' ' in message.text:
        arg = message.text.split(' ',1)[1]
        if arg.startswith('ref_'):
            ref_code = arg[4:]
    register_user_if_not_exists(user_id, username)
    user_data = get_user(user_id)
    if ref_code and user_data and not user_data.get('referred_by'):
        if link_referral(ref_code, user_id):
            log_action(user_id, 'referral_linked', ref_code)

    if user_data and user_data.get('agreed_to_terms'):
        await message.answer(
            f"👋 Снова здравствуйте, {html.bold(message.from_user.full_name)}!",
            reply_markup=keyboards.main_reply_keyboard
        )
        await show_main_menu(message)
    else:
        terms_url = get_setting("terms_url")
        privacy_url = get_setting("privacy_url")
        if not terms_url or not privacy_url:
            await message.answer("❗️ Условия использования и политика конфиденциальности не установлены. Пожалуйста, обратитесь к администратору.")
            return
        agreement_text = (
            "<b>Добро пожаловать!</b>\n\n"
            "Перед началом использования бота, пожалуйста, ознакомьтесь и примите наши "
            f"<a href='{terms_url}'>Условия использования</a> и "
            f"<a href='{privacy_url}'>Политику конфиденциальности</a>.\n\n"
            "Нажимая кнопку 'Принимаю', вы подтверждаете свое согласие с этими документами."
        )
        await message.answer(agreement_text, reply_markup=keyboards.create_agreement_keyboard(), disable_web_page_preview=True)
        await state.set_state(UserAgreement.waiting_for_agreement)

@user_router.callback_query(UserAgreement.waiting_for_agreement, F.data == "agree_to_terms")
async def agree_to_terms_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    
    set_terms_agreed(user_id)
    
    await state.clear()
    
    await callback.message.delete()
    
    await callback.message.answer(
        f"✅ Спасибо! Приятного использования.",
        reply_markup=keyboards.main_reply_keyboard
    )
    await show_main_menu(callback.message)

@user_router.message(UserAgreement.waiting_for_agreement)
async def agreement_fallback_handler(message: types.Message):
    await message.answer("Пожалуйста, сначала примите условия использования, нажав на кнопку выше.")

@user_router.message(F.text == "🏠 Главное меню")
async def main_menu_handler(message: types.Message):
    await show_main_menu(message)

@user_router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(callback: types.CallbackQuery):
    await callback.answer()
    await show_main_menu(callback.message, edit_message=True)

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
    final_text = get_profile_text(username, total_spent, total_months, vpn_status_text) + f"\n\n👥 Ваш реф-код: <code>{ref_code}</code>\nПриглашено: {ref_count}"
    await callback.message.edit_text(final_text, reply_markup=keyboards.create_back_to_menu_keyboard())

@user_router.callback_query(F.data == "show_referrals")
async def referrals_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    ref_code = ensure_user_ref_code(user_id)
    ref_count = count_referrals(ref_code)
    
    text = f"👥 <b>Пригласите друга</b>\n\nКогда друг активирует подписку —\nвы оба получите +3 дня 🎁\n\n👥 Приглашено: {ref_count}"
    
    await callback.message.edit_text(text, reply_markup=keyboards.create_back_to_menu_keyboard())

@user_router.callback_query(F.data == "show_about")
async def about_handler(callback: types.CallbackQuery):
    await callback.answer()
    
    about_text = get_setting("about_text")
    terms_url = get_setting("terms_url")
    privacy_url = get_setting("privacy_url")

    if about_text == ABOUT_TEXT and terms_url == TERMS_URL and privacy_url == PRIVACY_URL:
        await callback.message.edit_text(
            "Информация о проекте не установлена. Установите её в админ-панели.",
            reply_markup=keyboards.create_back_to_menu_keyboard()
        )
    elif terms_url == TERMS_URL and privacy_url == PRIVACY_URL:
        await callback.message.edit_text(
            about_text,
            reply_markup=keyboards.create_back_to_menu_keyboard()
        )
    elif terms_url == TERMS_URL:
        await callback.message.edit_text(
            about_text,
            reply_markup=keyboards.create_about_keyboard_terms(privacy_url)
        )
    elif privacy_url == PRIVACY_URL:
        await callback.message.edit_text(
            about_text,
            reply_markup=keyboards.create_about_keyboard_privacy(terms_url)
        )
    else:
        await callback.message.edit_text(
        about_text,
        reply_markup=keyboards.create_about_keyboard(terms_url, privacy_url)
        )

@user_router.callback_query(F.data == "show_traffic")
async def traffic_status_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    keys = get_user_keys(user_id)
    if not keys:
        await callback.message.edit_text("У вас нет ключей для отображения трафика.", reply_markup=keyboards.create_back_to_menu_keyboard())
        return
    from shop_bot.modules.remnawave_api import get_user_by_telegram_id
    from shop_bot.config import build_progress_bar
    async with aiohttp.ClientSession() as session:
        lines = ["<b>📊 Использование трафика</b>"]
        
        # Получаем общую информацию о пользователе (теперь все ключи в одном профиле)
        remote = await get_user_by_telegram_id(session, str(user_id))
        if not remote:
            lines.append("❌ " + user_messages.ERR_TRAFFIC_REMOTE)
        else:
            used = remote.get('usedTrafficBytes', 0)
            base_limit = remote.get('trafficLimitBytes', 0)
            
            # Суммируем дополнительный трафик из всех ключей
            total_extra = sum(key.get('traffic_extra_bytes', 0) or 0 for key in keys)
            limit = base_limit + total_extra
            
            if limit > 0:
                percent = min(100, (used/limit)*100)
                bar = build_progress_bar(percent)
                used_gb = used / (1024**3)
                limit_gb = limit / (1024**3)
                
                lines.append(f"📊 Общее использование:")
                lines.append(f"{bar} {percent:.1f}%")
                lines.append(f"📈 {used_gb:.2f} ГБ из {limit_gb:.1f} ГБ")
                
                if total_extra > 0:
                    extra_gb = total_extra / (1024**3)
                    lines.append(f"➕ Доп. трафик: {extra_gb:.1f} ГБ")
            else:
                lines.append("♾️ Безлимитный трафик")
        
        # Показываем информацию о ключах
        lines.append(f"\n🔑 Активных ключей: {len(keys)}")
        for idx, key in enumerate(keys, start=1):
            expiry_date = datetime.fromisoformat(key['expiry_date'])
            status = "✅" if expiry_date > datetime.now() else "❌"
            lines.append(f"{status} Ключ #{idx}: до {expiry_date.strftime('%d.%m.%Y')}")
    
    # Добавляем timestamp для уникальности сообщения
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M:%S")
    lines.append(f"\nОбновлено: {current_time}")
    lines.append("Нажмите 'Обновить' для актуализации.")
    
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
async def toggle_autorenew_handler(callback: types.CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    current = get_auto_renew(uid)
    set_auto_renew(uid, not current)
    log_action(uid, 'auto_renew_toggle', str(not current))
    await show_main_menu(callback.message, edit_message=True)

@user_router.callback_query(F.data.startswith("traffic_packs_"))
async def show_traffic_packs(callback: types.CallbackQuery):
    await callback.answer()
    key_id = int(callback.data.split('_')[2])
    await callback.message.edit_text("Выберите пакет дополнительного трафика:", reply_markup=keyboards.create_traffic_packs_keyboard(TRAFFIC_PACKS, key_id))

@user_router.callback_query(F.data.startswith("buy_pack_"))
async def buy_traffic_pack(callback: types.CallbackQuery):
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
async def trial_period_handler(callback: types.CallbackQuery):
    await callback.answer("Проверяю доступность...", show_alert=False)
    user_id = callback.from_user.id
    user_db_data = get_user(user_id)
    if user_db_data and user_db_data.get('trial_used'):
        await callback.answer("Вы уже использовали бесплатный пробный период.", show_alert=True)
        return
    
    # Устанавливаем флаг использования пробного периода сразу, чтобы предотвратить повторное использование
    set_trial_used(user_id)
    
    await callback.message.edit_text(
        f"Отлично! Создаю бесплатную подписку на ~3 месяца ({REMNA_TRIAL_DAYS} дней)…"
    )
    try:
        key_number = get_next_key_number(user_id)
        email = f"user{user_id}-key{key_number}-trial@kitsura.fun"
        uri, expire_iso, vless_uuid, sub_url = await remnawave_api.provision_key(
            email, days=REMNA_TRIAL_DAYS, telegram_id=str(user_id))
        if not uri or not expire_iso or not vless_uuid:
            # Сбрасываем флаг при ошибке создания ключа
            reset_trial_used(user_id)
            await callback.message.edit_text("❌ " + user_messages.ERR_TRIAL_CREATE)
            return
        # convert ISO to timestamp ms for storage
        expiry_dt = datetime.fromisoformat(expire_iso.replace('Z', '+00:00'))
        expiry_ms = int(expiry_dt.timestamp() * 1000)
        new_key_id = add_new_key(user_id, vless_uuid, email, expiry_ms)
        
        # Показываем созданный ключ пользователю
        expiry_str = expiry_dt.strftime("%d.%m.%Y %H:%M")
        message_text = "\u2705 <b>Готово!</b> Сейчас даём <b>бесплатную подписку примерно на 3 месяца</b> "
        message_text += f"(до <b>{expiry_str}</b>). Дальше — платный доступ.\n\n"
        message_text += "<b>Ссылка для Happ:</b>\n"
        message_text += f"<code>{html.quote(sub_url or uri)}</code>\n\n"
        message_text += "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        message_text += "\U0001f4f1 Как установить:\n\n"
        message_text += "1\ufe0f\u20e3 Скачай приложение Happ (кнопка ниже)\n\n"
        message_text += "2\ufe0f\u20e3 Открой Happ\n\n"
        message_text += "3\ufe0f\u20e3 Нажми + в правом верхнем углу\n\n"
        message_text += '4\ufe0f\u20e3 Выбери "Из буфера обмена"\n\n'
        message_text += "5\ufe0f\u20e3 Нажми кнопку питания \u2014 готово! \U0001f389\n"
        message_text += "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        message_text += user_messages.MSG_TRIAL_PORTAL_HINT
        
        await callback.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboards.create_trial_success_keyboard(sub_url or uri),
        )
    except Exception as e:
        logger.error(f"Error creating trial key for user {user_id}: {e}", exc_info=True)
        # Сбрасываем флаг при любой ошибке
        reset_trial_used(user_id)
        await callback.message.edit_text("❌ " + user_messages.ERR_TRIAL_CREATE)

@user_router.callback_query(F.data == "open_admin_panel")
async def open_admin_panel_handler(callback: types.CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("У вас нет доступа.", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "Добро пожаловать в админ-панель!",
        reply_markup=keyboards.create_admin_keyboard()
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
    ref_code = ensure_user_ref_code(user_id)
    ref_count = count_referrals(ref_code)
    active_keys = [k for k in user_keys if datetime.fromisoformat(k["expiry_date"]) > now]
    balance_line = (
        f"💰 <b>Баланс:</b> {balance:.0f} ₽ (~{days_left} дн. при {DAILY_RATE:.2f} ₽/день)\n"
        if balance > 0
        else f"💰 <b>Баланс:</b> 0 ₽ — пополните, чтобы продлить доступ\n"
    )
    sub_url = None
    if active_keys:
        try:
            async with aiohttp.ClientSession() as session:
                remote = await remnawave_api.get_user_by_telegram_id(session, str(user_id))
                if remote:
                    sub_url = remote.get("subscriptionUrl")
        except Exception as e:
            logger.warning("subscriptionUrl fetch for account: %s", e)
        latest = max(active_keys, key=lambda k: datetime.fromisoformat(k["expiry_date"]))
        exp = datetime.fromisoformat(latest["expiry_date"])
        text = (
            f"👤 <b>Ваш аккаунт BenderVPN</b>\n\n"
            f"{balance_line}"
            f"📅 Подписка на панели: до {exp.strftime('%d.%m.%Y')}\n"
            f"👥 Приглашено друзей: {ref_count}"
        )
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=keyboards.create_account_keyboard(sub_url)
        )
    else:
        trial_available = not (user_db_data and user_db_data.get("trial_used"))
        text = (
            f"👤 <b>Ваш аккаунт BenderVPN</b>\n\n"
            f"{balance_line}"
            f"📅 Активного ключа нет\n"
            f"👥 Приглашено друзей: {ref_count}"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_account_no_sub_keyboard(trial_available))

@user_router.callback_query(F.data == "contact_support")
async def contact_support_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("💬 <b>Поддержка</b>\n\nНапишите ваш вопрос прямо здесь —\nмы ответим в самое ближайшее время 🙏", parse_mode="HTML")

@user_router.callback_query(F.data == "invite_friend")
async def invite_friend_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    ref_code = ensure_user_ref_code(user_id)
    ref_count = count_referrals(ref_code)
    bot_info = await callback.bot.get_me()
    text = f"👥 <b>Пригласите друга</b>\n\nКогда друг активирует подписку —\nвы оба получите +3 дня 🎁\n\n👥 Приглашено: {ref_count}"
    ref_url = f"https://t.me/{bot_info.username}?start=ref_{ref_code}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboards.create_invite_keyboard(ref_url))

@user_router.callback_query(F.data == "copy_ref_url")
async def copy_ref_url_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    ref_code = ensure_user_ref_code(user_id)
    bot_info = await callback.bot.get_me()
    ref_url = f"https://t.me/{bot_info.username}?start=ref_{ref_code}"
    await callback.message.answer(
        f"\U0001f465 Твоя реферальная ссылка \u2014 нажми чтобы скопировать:\n\n"
        f"`{ref_url}`",
        parse_mode="Markdown"
    )


@user_router.callback_query(F.data == "copy_sub_url")
async def copy_sub_url_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            user_data = await remnawave_api.get_user_by_telegram_id(session, str(user_id))
            if user_data and user_data.get("subscriptionUrl"):
                sub_url = user_data["subscriptionUrl"]
                await callback.message.answer(
                    f"\U0001f4cb Твоя ссылка подписки \u2014 нажми чтобы скопировать:\n\n"
                    f"`{sub_url}`",
                    parse_mode="Markdown"
                )
            else:
                await callback.message.answer("❌ " + user_messages.ERR_SUBSCRIPTION_URL_MISSING)
    except Exception as e:
        logger.error(f"Error in copy_sub_url: {e}")
        await callback.message.answer("❌ " + user_messages.ERR_GENERIC_RETRY)

@user_router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: types.CallbackQuery):
    if str(callback.from_user.id) != ADMIN_ID:
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
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer("Создаю бэкап...")
    
    # Изменяем сообщение, чтобы показать прогресс
    try:
        await callback.message.edit_text("⏳ Создание бэкапа...", reply_markup=None)
    except Exception:
        pass  # Игнорируем ошибки редактирования
    
    # Используем универсальную функцию для создания бэкапа
    success = await create_backup_and_send(callback.bot, ADMIN_ID, is_auto=False)
    
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
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await callback.message.edit_text("Управление промокодами:", reply_markup=keyboards.create_admin_promos_keyboard())

@user_router.callback_query(F.data == "admin_promo_create")
async def admin_promo_create_start(callback: types.CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True); return
    await callback.answer()
    await state.set_state(PromoCreate.waiting_for_code)
    await callback.message.edit_text("Введите код промокода (латиница/цифры):")

@user_router.message(PromoCreate.waiting_for_code)
async def admin_promo_code(message: types.Message, state: FSMContext):
    code = (message.text or '').strip()
    if not code or len(code) > 32:
        await message.answer("Некорректный код, попробуйте снова.")
        return
    await state.update_data(code=code)
    await state.set_state(PromoCreate.waiting_for_discount)
    await message.answer("Введите скидку % (0 если не нужна):")

@user_router.message(PromoCreate.waiting_for_discount)
async def admin_promo_discount(message: types.Message, state: FSMContext):
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
    if str(callback.from_user.id) != ADMIN_ID:
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
    if str(callback.from_user.id) != ADMIN_ID:
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
        import sqlite3
        from shop_bot.data_manager.database import DB_FILE
        restored = False
        try:
            with sqlite3.connect(DB_FILE) as conn:
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
        async with aiohttp.ClientSession() as session:
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
        async with aiohttp.ClientSession() as session:
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
async def buy_new_key_handler(callback: types.CallbackQuery):
    await show_topup_handler(callback)

@user_router.callback_query(F.data.startswith("extend_key_"))
async def extend_key_handler(callback: types.CallbackQuery):
    await show_topup_handler(callback)


@user_router.callback_query(F.data == "show_topup")
async def show_topup_handler(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    balance = get_balance(user_id)
    days_left = balance_to_days(balance)
    text = (
        f"💰 <b>Ваш баланс: {balance:.0f} ₽</b>\n"
        f"📅 Хватит на: ~{days_left} дн.\n\n"
        f"Тариф: <b>{DAILY_RATE:.2f} ₽/день</b> (без привязки к месяцу — пополняете на нужную сумму)\n\n"
        f"Выберите сумму пополнения:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.create_topup_keyboard(),
        parse_mode="HTML",
    )


@user_router.callback_query(F.data == "topup_custom")
async def topup_custom_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        CUSTOM_AMOUNT_UNAVAILABLE,
        reply_markup=keyboards.create_topup_keyboard(),
        parse_mode="HTML",
    )


@user_router.callback_query(F.data.in_({"topup_200", "topup_500", "topup_1000", "topup_2000"}))
async def topup_select_handler(callback: types.CallbackQuery):
    await callback.answer()
    topup_id = callback.data
    if topup_id not in TOPUP_PRESETS:
        return
    _name, _price_str, amount = TOPUP_PRESETS[topup_id]
    days = balance_to_days(amount)
    text = (
        f"💰 Пополнение на <b>{amount:.0f} ₽</b>\n"
        f"📅 ~{days} дн. по тарифу {DAILY_RATE:.2f} ₽/день\n\n"
        f"Выберите способ оплаты:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.create_topup_payment_keyboard(topup_id),
        parse_mode="HTML",
    )


@user_router.callback_query(F.data.startswith("pay_stars_topup_"))
async def pay_stars_topup_handler(callback: types.CallbackQuery, bot: Bot):
    await callback.answer("Создаю счёт...")
    topup_id = callback.data.replace("pay_stars_topup_", "")
    if topup_id not in TOPUP_PRESETS:
        await callback.message.edit_text("Ошибка: пресет не найден.")
        return
    _name, price_str, amount_rub = TOPUP_PRESETS[topup_id]
    user_id = callback.from_user.id
    stars_rate = float(os.getenv("STARS_RATE", "2.0"))
    stars_amount = max(1, int(float(price_str) * stars_rate))
    payload_data = json.dumps(
        {"u": user_id, "t": "topup", "a": amount_rub},
        separators=(",", ":"),
    )
    try:
        from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

        link = await bot.create_invoice_link(
            title=f"Пополнение {amount_rub:.0f} ₽",
            description=f"Баланс BenderVPN +{amount_rub:.0f} ₽",
            payload=payload_data,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{amount_rub:.0f} RUB", amount=stars_amount)],
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"⭐ Оплатить {stars_amount} Stars", url=link)]
            ]
        )
        await callback.message.edit_text(
            f"⭐ Оплата через Telegram Stars\n\n"
            f"Сумма: {stars_amount} Stars (~{amount_rub:.0f} ₽)\n\n"
            f"Нажмите кнопку ниже:",
            reply_markup=kb,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to create Stars topup invoice: {e}", exc_info=True)
        await callback.message.edit_text("❌ " + user_messages.ERR_TELEGRAM_STARS)

@user_router.callback_query(F.data.startswith("buy_") & F.data.contains("_month"))
async def choose_payment_method_handler(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    plan_id, action, key_id = "_".join(parts[:-2]), parts[-2], int(parts[-1])
    await callback.message.edit_text(
        CHOOSE_PAYMENT_METHOD_MESSAGE,
        reply_markup=keyboards.create_payment_method_keyboard(PAYMENT_METHODS, plan_id, action, key_id)
    )

@user_router.callback_query(F.data.startswith("pay_yookassa_"))
async def create_yookassa_payment_handler(callback: types.CallbackQuery, state: FSMContext):
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
            "capture": True, "description": description,
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

    # Отладка, чтобы убедиться, что все верно
    print(f"DEBUG [Final]: String for hashing: '{string_to_hash}'")
    
    return hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()

@user_router.callback_query(F.data.startswith("pay_crypto_"))
async def create_crypto_payment_handler(callback: types.CallbackQuery, state: FSMContext):
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
            
        async with aiohttp.ClientSession() as session:
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

@user_router.callback_query(F.data.startswith("pay_stars_"))
async def create_stars_payment_handler(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer("Создаю счет для оплаты звездами...")
    
    parts = callback.data.split("_")[2:]
    plan_id = "_".join(parts[:-2])
    action = parts[-2]
    key_id = int(parts[-1])
    
    if plan_id not in PLANS:
        await callback.message.answer("❌ " + user_messages.ERR_TARIFF_CHOICE)
        return

    name, price_rub, months = PLANS[plan_id]
    user_id = callback.from_user.id
    
    # Конвертируем рубли в звезды (примерно 1 рубль = 2 звезды)
    stars_rate = float(os.getenv("STARS_RATE", "2.0"))  # сколько звезд за 1 рубль
    
    data = await state.get_data()
    promo_code = data.get('promo_code')
    amount_value = float(price_rub)
    
    if promo_code:
        promo = get_promo(promo_code)
        if promo:
            disc = promo.get('discount_percent', 0)
            if disc and 0 < disc < 100:
                amount_value = round(float(price_rub) * (100-disc)/100, 2)
    
    stars_amount = int(amount_value * stars_rate)
    
    try:
        if months == 1:
            description = f"Оплата подписки на 1 месяц"
        elif months <= 4:
            description = f"Оплата подписки на {months} месяца"
        else:
            description = f"Оплата подписки на {months} месяцев"
        
        # Создаем инвойс для Telegram Stars
        from aiogram.types import LabeledPrice
        
        # Telegram Stars payload ограничен 128 байтами, поэтому минимизируем данные
        payload_data = {
            "u": user_id,  # user_id
            "m": months,   # months
            "p": amount_value,  # price
            "a": action,   # action
            "k": key_id,   # key_id
            "pl": plan_id, # plan_id
            "pr": promo_code[:10] if promo_code else None,  # promo_code (первые 10 символов)
            "c": callback.message.chat.id,  # chat_id
            "mid": callback.message.message_id  # message_id
        }
        
        invoice = await bot.create_invoice_link(
            title=f"VPN подписка - {name}",
            description=description,
            payload=json.dumps(payload_data, separators=(',', ':')),  # без пробелов
            provider_token="",  # Для Telegram Stars токен должен быть пустым
            currency="XTR",  # Telegram Stars currency
            prices=[LabeledPrice(label=name, amount=stars_amount)]
        )
        
        # Создаем инлайн-кнопку для оплаты
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💫 Оплатить {stars_amount} звездами", url=invoice)]
        ])
        
        await callback.message.edit_text(
            f"💫 Оплата звездами Telegram\n\n"
            f"Стоимость: {stars_amount} ⭐\n"
            f"Период: {months} мес.\n\n"
            f"Нажмите кнопку ниже для оплаты:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Failed to create Telegram Stars payment: {e}", exc_info=True)
        await callback.message.answer("❌ " + user_messages.ERR_TELEGRAM_STARS)

@user_router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    """Обрабатываем предварительную проверку платежа звездами"""
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
            email = f"user{user_id}-key{key_number}@kitsura.fun"
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
            if referrer_code:
                days_to_add += 3
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

