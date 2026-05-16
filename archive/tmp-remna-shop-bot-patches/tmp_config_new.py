import os

server_name = os.getenv("SERVER_NAME")

PLANS = {
    "buy_1_month": ("Подписка 1 месяц", "200.00", 1),
    "buy_3_months": ("Подписка 3 месяца — 180 ₽/мес", "540.00", 3),
    "buy_6_months": ("Подписка 6 месяцев — 167 ₽/мес", "999.00", 6),
    "buy_12_months": ("Подписка 12 месяцев — 158 ₽/мес", "1899.00", 12),
}

# Дополнительные пакеты трафика (id: (Название, Цена, ГБ))
TRAFFIC_PACKS = {
    "traffic_100_gb": ("Доп. трафик +100 ГБ", "100.00", 100),
    "traffic_300_gb": ("Доп. трафик +300 ГБ", "250.00", 300),
}

WELCOME_MESSAGE = (
    "👋 Добро пожаловать в BenderVPN\n\n"
    "Невидимый VPN для России.\n"
    "Работает там, где другие заблокированы.\n\n"
    "⚡️ Один клик — всё настраивается автоматически\n"
    "🛡 Невидим для DPI и блокировщиков\n"
    "🌍 Серверы в РФ + Европе\n"
    "🎁 30 дней бесплатно\n\n"
    "Чтобы начать — нажми «Попробовать бесплатно»."
)
CHOOSE_PLAN_MESSAGE = "Выберите подходящий тариф:"
CHOOSE_PAYMENT_METHOD_MESSAGE = "Выберите удобный способ оплаты:"

ABOUT_TEXT = "BenderVPN — невидимый VPN для России. Работает там, где другие заблокированы. Технология VLESS Reality делает трафик неотличимым от обычного HTTPS. Серверы в РФ и Европе, автоматический выбор лучшего."
TERMS_URL = "https://telegra.ph/Usloviya-ispolzovaniya-BenderVPN-04-16"
PRIVACY_URL = "https://telegra.ph/Politika-konfidencialnosti-BenderVPN-04-16"
SUPPORT_USER = "@Bender_KVN_bot"
CHANNEL_URL = ""
SUPPORT_TEXT = "Опишите проблему — мы ответим в течение часа. Если VPN не подключается, укажите: какое устройство, какой оператор связи, и скриншот ошибки."

KEY_EMAIL_DOMAIN = os.getenv("KEY_EMAIL_DOMAIN", "kitsura.fun")

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
