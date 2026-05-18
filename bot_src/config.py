import os

server_name = os.getenv("SERVER_NAME")

# Новый пробный период (дней с момента первой выдачи ключа через бота).
# Совпадает с REMNA_TRIAL_DAYS / TRIAL_DAYS в docker env.
REMNA_TRIAL_DAYS = int(
    os.getenv("REMNA_TRIAL_DAYS", os.getenv("TRIAL_DAYS", os.getenv("REMNA_DEFAULT_DAYS", "90")))
)

# Оплата в боте (ЮKassa/TG Stars и т.д.). Если false — напоминания об окончании
# пробного периода без кнопки «Оформить подписку», только поддержка / ожидание кассы.
BOT_PAYMENTS_LIVE = os.getenv("BOT_PAYMENTS_LIVE", "").strip().lower() in ("1", "true", "yes")

# Тарификация: пополнение баланса, списание 6.67 ₽/день (не привязка к «месяцам»).
DAILY_RATE = 6.67  # ₽/день за одно устройство

TOPUP_PRESETS = {
    "topup_200": ("200 ₽", "200.00", 200),
    "topup_500": ("500 ₽", "500.00", 500),
    "topup_1000": ("1000 ₽", "1000.00", 1000),
    "topup_2000": ("2000 ₽", "2000.00", 2000),
}

# Legacy: периодные планы (старые webhook / YooKassa metadata); UI — только TOPUP.
PLANS = {
    "buy_1_month": ("Подписка 1 месяц", "200.00", 1),
    "buy_3_months": ("Подписка 3 месяца", "540.00", 3),
    "buy_6_months": ("Подписка 6 месяцев", "999.00", 6),
    "buy_12_months": ("Подписка 12 месяцев", "1899.00", 12),
}


def balance_to_days(balance: float) -> int:
    if balance <= 0:
        return 0
    return max(1, int(balance / DAILY_RATE))


def topup_button_label(amount_rub: float) -> str:
    days = balance_to_days(amount_rub)
    return f"{amount_rub:.0f} ₽ — ~{days} дн."

# Дополнительные пакеты трафика (id: (Название, Цена, ГБ))
TRAFFIC_PACKS = {
    "traffic_100_gb": ("Доп. трафик +100 ГБ", "100.00", 100),
    "traffic_300_gb": ("Доп. трафик +300 ГБ", "250.00", 300),
}

WELCOME_MESSAGE = "Здесь вы можете приобрести быстрый и надежный VPN."
CHOOSE_PLAN_MESSAGE = "Выберите подходящий тариф:"
CHOOSE_TOPUP_MESSAGE = "Выберите сумму пополнения:"
CHOOSE_PAYMENT_METHOD_MESSAGE = "Выберите удобный способ оплаты:"
CUSTOM_AMOUNT_UNAVAILABLE = (
    "Произвольная сумма будет доступна после подключения оплаты картой или криптой."
)
KEY_EMAIL_DOMAIN = os.getenv("KEY_EMAIL_DOMAIN", "kitsura.fun")

# P3-FLOW-12: same URL as site portal (BotFather Menu Button + inline WebApp)
TELEGRAM_WEBAPP_URL = (
    os.getenv("TELEGRAM_WEBAPP_URL", "https://k9x2m1.conntest.xyz:2053/portal/")
    .strip()
    .rstrip("/")
    + "/"
)


def telegram_cabinet_webapp_url() -> str:
    """Mini App deep-link to portal #cabinet (balance + setup links)."""
    return TELEGRAM_WEBAPP_URL.rstrip("/") + "#cabinet"


_PORTAL_DEVICE_IDS = frozenset({"iphone", "android", "windows", "mac"})


def telegram_portal_webapp_url(device_id: str | None = None) -> str:
    """Mini App URL; optional #devices or #device=<id> (P3-FLOW-04)."""
    base = TELEGRAM_WEBAPP_URL.rstrip("/")
    if device_id == "devices":
        return f"{base}#devices"
    if device_id in _PORTAL_DEVICE_IDS:
        return f"{base}#device={device_id}"
    return TELEGRAM_WEBAPP_URL


TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "Bender_KVN_bot").strip().lstrip("@")


def telegram_bind_url(bind_token: str) -> str:
    """Deep link: open bot and attach web trial to this Telegram account."""
    token = (bind_token or "").strip()
    if not token:
        return f"https://t.me/{TELEGRAM_BOT_USERNAME}"
    return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start=bind_{token}"

ABOUT_TEXT = "Настройки не установлены. Установите их в админ-панели."
TERMS_URL = "Ссылка на условия использования не установлена. Установите её в админ-панели."
PRIVACY_URL = "Ссылка на политику конфиденциальности не установлена. Установите её в админ-панели."
SUPPORT_USER = "Ссылка на поддержку не установлена. Установите её в админ-панели."
CHANNEL_URL = "Ссылка на канал не установлена. Установите её в админ-панели."
SUPPORT_TEXT = "Текст поддержки не установлен. Установите его в админ-панели."

def get_profile_text(username, total_spent, total_months, vpn_status_text):
    return (
        f"👤 <b>Профиль:</b> {username}\n\n"
        f"💰 <b>Потрачено всего:</b> {total_spent:.0f} RUB\n"
        f"📅 <b>Приобретено месяцев:</b> {total_months}\n\n"
        f"{vpn_status_text}"
    )

def get_vpn_active_text(days_left, hours_left):
    return (
        f"✅ <b>Статус VPN:</b> Активен\n"
        f"⏳ <b>Осталось:</b> {days_left} д. {hours_left} ч."
    )

VPN_INACTIVE_TEXT = "❌ <b>Статус VPN:</b> Неактивен (срок истек)"
VPN_NO_DATA_TEXT = "ℹ️ <b>Статус VPN:</b> У вас пока нет активных ключей."

def get_key_info_text(key_number, expiry_date, created_date, connection_string):
    expiry_formatted = expiry_date.strftime('%d.%m.%Y в %H:%M')
    created_formatted = created_date.strftime('%d.%m.%Y в %H:%M')
    
    return (
        f"<b>🔑 Информация о ключе #{key_number}</b>\n\n"
        f"➕ <b>Приобретён:</b> {created_formatted}\n"
        f"⏳ <b>Действителен до:</b> {expiry_formatted}\n\n"
        f"<code>{connection_string}</code>"
    )

def get_purchase_success_text(action: str, key_number: int, expiry_date, connection_string: str):
    
    action_text = "обновлен" if action == "extend" else "готов"
    expiry_formatted = expiry_date.strftime('%d.%m.%Y в %H:%M')

    return (
        f"🎉 <b>Ваш ключ #{key_number} {action_text}!</b>\n\n"
        f"⏳ <b>Он будет действовать до:</b> {expiry_formatted}\n\n"
        f"<code>{connection_string}</code>"
    )

def build_progress_bar(percent: float, width: int = 20) -> str:
    filled = int(width * percent / 100)
    return '▰' * filled + '▱' * (width - filled)