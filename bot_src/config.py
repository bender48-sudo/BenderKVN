import logging
import os

from shop_bot.public_urls import portal_page_url, telegram_webapp_url

_logger = logging.getLogger(__name__)

server_name = os.getenv("SERVER_NAME")

# Remna panel HTTP (aiohttp ClientTimeout: connect + total seconds).
REMNA_API_CONNECT_TIMEOUT = int(os.getenv("REMNA_API_CONNECT_TIMEOUT", "5"))
REMNA_API_TIMEOUT = int(os.getenv("REMNA_API_TIMEOUT", "30"))
REMNA_API_RETRY_ATTEMPTS = int(os.getenv("REMNA_API_RETRY_ATTEMPTS", "4"))
REMNA_HTTP_CONN_LIMIT = int(os.getenv("REMNA_HTTP_CONN_LIMIT", "20"))

# Sub refresh notify jitter (seconds); must match prod env / subscription_refresh.py.
SUB_REFRESH_JITTER_MAX_SEC = int(os.getenv("SUB_REFRESH_JITTER_MAX_SEC", "300"))

SCHEDULER_CONCURRENT_API_CALLS = int(os.getenv("SCHEDULER_CONCURRENT_API_CALLS", "10"))

# Новый пробный период (дней с момента первой выдачи ключа через бота).
# Совпадает с REMNA_TRIAL_DAYS / TRIAL_DAYS в docker env.
REMNA_TRIAL_DAYS = int(
    os.getenv("REMNA_TRIAL_DAYS", os.getenv("TRIAL_DAYS", os.getenv("REMNA_DEFAULT_DAYS", "90")))
)

# Browser /email trial: short access only to complete Happ setup + bind Telegram (anti-abuse).
WEB_TRIAL_DAYS = int(os.getenv("WEB_TRIAL_DAYS", "1"))

# P1-REF-002: legacy hidden invitee +Nd on first legacy plan purchase (deprecated path).
# Owner decision: target reward is +1 month to REFERRER after invitee paid conversion — not
# extra days to invitee. Keep gated OFF; do not enable in production.
REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED = os.getenv(
    "REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED", ""
).strip().lower() in ("1", "true", "yes")
REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS = int(
    os.getenv("REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS", "3")
)

# Referrer reward model is the ₽/% one below (REF-LEDGER-001): +30% of the invitee's first
# top-up to the referrer, credited via balance_ledger. The dead "+1 month" model
# (REFERRAL_REFERRER_FIRST_PAYMENT_REWARD_*) was removed — it was never implemented and
# contradicted canon.

# K6: referral/partner UI hidden until bonuses are implemented and approved.
REFERRAL_UI_ENABLED = os.getenv("REFERRAL_UI_ENABLED", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

# P3 Mini App referral — ADVERTISED program terms shown on the Referral screen.
# Display-only: no balance accrual is wired (referral_rewards_active() default OFF), so the
# snapshot reports rewards_active=false and earned_rub=0 — never a fabricated number. These
# values are the product intent from MINI-APP-MIGRATION-PLAN-2026-06-25 (P3); real accrual
# (+₽ to friend on register, % to referrer on first payment) is a separate owner OK + ledger
# task (REF-BONUS-001, see DEC-IMPL-006/007). All overridable via env without a code change.
REFERRAL_FRIEND_BONUS_RUB = int(os.getenv("REFERRAL_FRIEND_BONUS_RUB", "100"))
REFERRAL_REFERRER_PCT = int(os.getenv("REFERRAL_REFERRER_PCT", "30"))
REFERRAL_PARTNER_FIRST_PCT = int(os.getenv("REFERRAL_PARTNER_FIRST_PCT", "50"))
REFERRAL_PARTNER_RECURRING_PCT = int(os.getenv("REFERRAL_PARTNER_RECURRING_PCT", "10"))
REFERRAL_PARTNER_MIN_WITHDRAW_RUB = int(os.getenv("REFERRAL_PARTNER_MIN_WITHDRAW_RUB", "5000"))


def referral_rewards_active() -> bool:
    """True only when real referral balance accrual is wired (REF-BONUS-001). Default OFF.

    While OFF the Mini App shows the program terms and real invitee facts (who paid /
    who only registered) but never an earned ₽ figure — there is no reward ledger yet.
    """
    return os.getenv("REFERRAL_REWARDS_ACTIVE", "").strip().lower() in ("1", "true", "yes")


def referral_invitee_first_purchase_bonus_days(referred_by: str | None) -> int:
    """Legacy invitee bonus gate (P1-REF-002). Returns 0 unless explicitly enabled — default OFF."""
    if not referred_by:
        return 0
    if not REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_ENABLED:
        return 0
    if REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS <= 0:
        return 0
    return REFERRAL_INVITEE_FIRST_PURCHASE_BONUS_DAYS

# Оплата в боте (ЮKassa; Stars отключены). Если false — напоминания об окончании
# пробного периода без кнопки пополнения, только поддержка.
BOT_PAYMENTS_LIVE = os.getenv("BOT_PAYMENTS_LIVE", "").strip().lower() in ("1", "true", "yes")

# Тарификация: пополнение баланса (BILL-BALANCE-KOPEKS-001).
# 200 ₽ = ровно 30 дней в целых копейках; display/charge 6,66 ₽/день.
DAYS_PER_REFERENCE_TOPUP = 30
REFERENCE_TOPUP_KOPEKS = 20_000  # 200 ₽
DAILY_RATE_KOPEKS = REFERENCE_TOPUP_KOPEKS // DAYS_PER_REFERENCE_TOPUP  # 666
DAILY_RATE = DAILY_RATE_KOPEKS / 100.0  # 6.66 ₽/день за одно устройство

TOPUP_PRESETS = {
    "topup_200": ("200 ₽", "200.00", 200),
    "topup_500": ("500 ₽", "500.00", 500),
    "topup_1000": ("1000 ₽", "1000.00", 1000),
    "topup_2000": ("2000 ₽", "2000.00", 2000),
}

# In-app Mini App balance presets (MINI-APP-BUILD-001). Round ₽ amounts — пользователь
# платит круглую сумму, дни считает сервер от ставки (без фейк-скидок). UI ставку не хардкодит.
PORTAL_TOPUP_PRESETS_RUB = (200, 600, 1200, 2400)
PORTAL_TOPUP_MIN_RUB = 200
PORTAL_TOPUP_MAX_RUB = 10_000

# Legacy: периодные планы (старые webhook / YooKassa metadata); UI — только TOPUP.
PLANS = {
    "buy_1_month": ("Подписка 1 месяц", "200.00", 1),
    "buy_3_months": ("Подписка 3 месяца", "540.00", 3),
    "buy_6_months": ("Подписка 6 месяцев", "999.00", 6),
    "buy_12_months": ("Подписка 12 месяцев", "1899.00", 12),
}


def rub_to_kopeks(rub: float) -> int:
    return int(round(float(rub) * 100))


def kopeks_to_rub(kopeks: int) -> float:
    return kopeks / 100.0


def daily_charge_rub() -> float:
    """Rubles deducted per UTC day (wallet profile)."""
    return DAILY_RATE


def format_daily_rate_ru() -> str:
    """User-facing ₽/day string (Russian decimal comma)."""
    return f"{DAILY_RATE:.2f}".replace(".", ",")


def balance_covers_one_day(balance: float) -> bool:
    return rub_to_kopeks(balance) >= DAILY_RATE_KOPEKS


def balance_to_days(balance: float) -> int:
    """Whole days of VPN left at current balance (floor; 0 if below one day rate)."""
    kopeks = rub_to_kopeks(balance)
    if kopeks < DAILY_RATE_KOPEKS:
        return 0
    return kopeks // DAILY_RATE_KOPEKS


def topup_button_label(amount_rub: float) -> str:
    days = balance_to_days(amount_rub)
    return f"{amount_rub:.0f} ₽ — ~{days} дн."

# Дополнительные пакеты трафика (id: (Название, Цена, ГБ))
TRAFFIC_PACKS = {
    "traffic_100_gb": ("Доп. трафик +100 ГБ", "100.00", 100),
    "traffic_300_gb": ("Доп. трафик +300 ГБ", "250.00", 300),
}

WELCOME_MESSAGE = "Начни бесплатный период — 90 дней без ограничений."
CHOOSE_PLAN_MESSAGE = "Выбери вариант:"
CHOOSE_TOPUP_MESSAGE = "Выбери сумму пополнения баланса:"
CHOOSE_PAYMENT_METHOD_MESSAGE = "Выбери способ оплаты:"
CUSTOM_AMOUNT_UNAVAILABLE = (
    "Что-то пошло не так. Попробуй выбрать сумму из предложенных вариантов или напиши нам."
)
KEY_EMAIL_DOMAIN = os.getenv("KEY_EMAIL_DOMAIN", "kitsura.fun").strip().lstrip("@")

# P3-FLOW-12: same URL as site portal (BotFather Menu Button + inline WebApp)
TELEGRAM_WEBAPP_URL = telegram_webapp_url()


def telegram_cabinet_webapp_url(telegram_id: int | None = None) -> str:
    """Mini App deep-link to /portal/cabinet.html (never /portal/ landing)."""
    query: dict[str, str] = {"wv": "26"}
    if telegram_id and int(telegram_id) > 0:
        query["tid"] = str(int(telegram_id))
    return portal_page_url("cabinet.html", query=query)


def telegram_guide_webapp_url(platform: str | None = None) -> str:
    """Mini App deep-link to /portal/guide.html."""
    query: dict[str, str] = {"wv": "26"}
    key = (platform or "").strip().lower()
    if key in ("ios", "iphone", "ipad"):
        query["device"] = "iphone"
    elif key == "android":
        query["device"] = "android"
    return portal_page_url("guide.html", query=query)


def telegram_info_webapp_url() -> str:
    """Mini App deep-link to /portal/info.html (§15 information hub)."""
    return portal_page_url("info.html", query={"wv": "35"})


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


def telegram_show_id_url() -> str:
    """Deep link: bot replies with the user's Telegram numeric ID."""
    return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start=show_id"

ABOUT_TEXT = "Настройки не установлены. Установите их в админ-панели."
TERMS_URL = "Ссылка на условия использования не установлена. Установите её в админ-панели."
PRIVACY_URL = "Ссылка на политику конфиденциальности не установлена. Установите её в админ-панели."
SUPPORT_USER = "Ссылка на поддержку не установлена. Установите её в админ-панели."

# P3-UX-LEGAL-FALLBACK-01: env overrides when bot_settings empty or placeholder
DEFAULT_TERMS_URL = os.getenv("DEFAULT_TERMS_URL", "").strip()
DEFAULT_PRIVACY_URL = os.getenv("DEFAULT_PRIVACY_URL", "").strip()
DEFAULT_SUPPORT_USERNAME = os.getenv("DEFAULT_SUPPORT_USERNAME", "@BenderVPN_support").strip()


def _is_http_url(value: str | None) -> bool:
    u = (value or "").strip()
    return u.startswith("http://") or u.startswith("https://")


def effective_legal_url(db_value: str | None, default_env: str, placeholder: str) -> str | None:
    raw = (db_value or "").strip()
    if _is_http_url(raw):
        return raw
    if _is_http_url(default_env):
        return default_env
    if raw and raw != placeholder:
        return raw if _is_http_url(raw) else None
    return None
CHANNEL_URL = "Ссылка на канал не установлена. Установите её в админ-панели."
SUPPORT_TEXT = "Текст поддержки не установлен. Установите его в админ-панели."

def get_profile_text(username, total_spent, total_months, vpn_status_text):
    return (
        f"<b>Профиль:</b> {username}\n\n"
        f"Потрачено: {total_spent:.0f} ₽\n\n"
        f"{vpn_status_text}"
    )

def get_vpn_active_text(days_left, hours_left):
    return (
        f"✅ <b>Доступ активен</b>\n"
        f"Осталось: {days_left} д. {hours_left} ч."
    )

VPN_INACTIVE_TEXT = "Доступ неактивен — срок истёк."
VPN_NO_DATA_TEXT = "Активных ключей пока нет."

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
    action_text = "обновлён" if action == "extend" else "активирован"
    expiry_formatted = expiry_date.strftime('%d.%m.%Y')

    return (
        f"✅ <b>Доступ {action_text}</b> до {expiry_formatted}\n\n"
        f"<code>{connection_string}</code>"
    )

def build_progress_bar(percent: float, width: int = 20) -> str:
    filled = int(width * percent / 100)
    return '▰' * filled + '▱' * (width - filled)


def validate_required_config() -> None:
    """Fail fast on missing critical env (P2-RED-BOT-ENV-01)."""
    missing: list[str] = []
    if not os.getenv("TELEGRAM_BOT_TOKEN", "").strip():
        missing.append("TELEGRAM_BOT_TOKEN")
    if not os.getenv("TELEGRAM_BOT_USERNAME", "").strip():
        missing.append("TELEGRAM_BOT_USERNAME")
    if not os.getenv("REMNA_BASE_URL", "").strip():
        missing.append("REMNA_BASE_URL")
    if not os.getenv("REMNA_API_TOKEN", "").strip():
        missing.append("REMNA_API_TOKEN")
    if not os.getenv("PORTAL_SETUP_HMAC_SECRET", "").strip():
        missing.append("PORTAL_SETUP_HMAC_SECRET")
    if not os.getenv("PORTAL_WEB_TRIAL_SECRET", "").strip():
        missing.append("PORTAL_WEB_TRIAL_SECRET")
    if missing:
        raise RuntimeError("Missing required environment: " + ", ".join(missing))
    sg = os.getenv("SUPPORT_GROUP_ID", "0").strip()
    if sg in ("", "0"):
        _logger.warning("SUPPORT_GROUP_ID=0 — support group disabled")