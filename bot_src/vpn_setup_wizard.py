"""P3-FLOW-04: in-bot VPN setup wizard (device pick → Mini App or chat fallback)."""
from __future__ import annotations

HAPP_STORES = {
    "ios": (
        "App Store (iPhone / iPad)",
        "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973",
    ),
    "android": (
        "Google Play",
        "https://play.google.com/store/apps/details?id=com.happproxy.happ",
    ),
    "windows": (
        "Скачать Happ для Windows",
        "https://www.happ.su/happ",
    ),
    "mac": (
        "Mac App Store",
        "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973",
    ),
}

DEVICES: dict[str, dict[str, str]] = {
    "iphone": {
        "label": "iPhone или iPad",
        "icon": "\U0001f4f1",
        "store_key": "ios",
    },
    "android": {
        "label": "Android",
        "icon": "\U0001f916",
        "store_key": "android",
    },
    "windows": {
        "label": "Windows",
        "icon": "\U0001f4bb",
        "store_key": "windows",
    },
    "mac": {
        "label": "Mac",
        "icon": "\U0001f34e",
        "store_key": "mac",
    },
}

WIZARD_INTRO = (
    "<b>\U0001f50c Подключить VPN</b>\n\n"
    "Выберите устройство. Дальше — пошаговая инструкция в Mini App "
    "(как на сайте) или короткие подсказки здесь в чате."
)

WIZARD_DEVICE_LEAD = (
    "<b>{icon} {label}</b>\n\n"
    "Удобнее всего — кнопка <b>«Инструкция в Mini App»</b>: те же шаги, что на сайте.\n"
    "Если Mini App не открывается — «Подсказки в чате»."
)

CHAT_STEPS_TEMPLATE = (
    "<b>{icon} {label} — подсказки в чате</b>\n\n"
    "<b>1.</b> Установите Happ: {store_label}\n"
    "<b>2.</b> {config_step}\n"
    "<b>3.</b> В Happ: + → «Из буфера обмена» (или QR со страницы настройки).\n"
    "<b>4.</b> Включите VPN переключателем.\n"
    "<b>5.</b> Проверьте: откройте любой сайт (например ya.ru).\n\n"
    "Не получается — «Написать нам» или статус: /status"
)

CONFIG_STEP_TRIAL = (
    "Получите настройку: «Бесплатно 3 месяца» в меню "
    "или «Моя настройка», если ключ уже есть."
)
CONFIG_STEP_HAS_KEY = "Откройте «Моя настройка» — QR и ссылка для Happ."

WIZARD_STUCK = (
    "<b>Не получается?</b>\n\n"
    "• Проверьте <a href=\"https://k9x2m1.conntest.xyz:2053/status\">статус сервиса</a>\n"
    "• Напишите в поддержку — кнопка ниже\n"
    "• Для настройки без Telegram: страница «Получить VPN» на сайте"
)


def device_ids() -> tuple[str, ...]:
    return tuple(DEVICES.keys())


def get_device(device_id: str) -> dict[str, str] | None:
    return DEVICES.get(device_id)


def store_for_device(device_id: str) -> tuple[str, str]:
    dev = DEVICES[device_id]
    key = dev["store_key"]
    return HAPP_STORES.get(key, HAPP_STORES["ios"])


def format_device_lead(device_id: str) -> str:
    dev = DEVICES[device_id]
    return WIZARD_DEVICE_LEAD.format(icon=dev["icon"], label=dev["label"])


def format_chat_steps(device_id: str, *, has_active_key: bool) -> str:
    dev = DEVICES[device_id]
    store_label, store_url = store_for_device(device_id)
    config_step = CONFIG_STEP_HAS_KEY if has_active_key else CONFIG_STEP_TRIAL
    text = CHAT_STEPS_TEMPLATE.format(
        icon=dev["icon"],
        label=dev["label"],
        store_label=f'<a href="{store_url}">{store_label}</a>',
        config_step=config_step,
    )
    return text
