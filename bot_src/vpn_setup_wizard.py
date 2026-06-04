"""P3-FLOW-04: in-bot VPN setup wizard (device pick → Mini App or chat fallback)."""
from __future__ import annotations

import os

from shop_bot.public_urls import public_status_url

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

WIZARD_INTRO = "На каком устройстве настраиваем?"

WIZARD_DEVICE_LEAD = (
    "<b>{icon} {label}</b>\n\n"
    "Три шага:\n"
    "1. Скачай Happ — кнопка ниже.\n"
    "2. Нажми «📷 Мой QR» или «📋 Скопировать ссылку».\n"
    "3. В Happ включи VPN — профиль <b>BenderVPN Auto</b> (сервер выбирается сам)."
)

CHAT_STEPS_TEMPLATE = (
    "<b>{icon} {label} — инструкция</b>\n\n"
    "<b>1.</b> Скачай Happ → {store_label}\n"
    "<b>2.</b> {config_step}\n"
    "<b>3.</b> В Happ нажми + → «Из буфера обмена»\n"
    "<b>4.</b> Включи VPN (BenderVPN Auto)\n\n"
    "Готово. Если что-то не получается — напиши, разберёмся."
)

CONFIG_STEP_TRIAL = (
    "Вернись в главное меню → нажми «Получить бесплатный VPN»."
)
CONFIG_STEP_HAS_KEY = (
    "Нажми «📷 Мой QR-код» выше — отсканируй в Happ."
)

WIZARD_STUCK = (
    "<b>Что-то не получается?</b>\n\n"
    "<b>Happ пишет «0 серверов»</b> — если VPN включён, это нормально.\n"
    "Нажми 🔄 в Happ рядом с профилем BenderVPN Auto.\n\n"
    "<b>На LTE не подключается</b> — в Happ нет выбора узла: профиль "
    "<b>BenderVPN Auto</b> сам переключает маршрут. Нажми 🔄, выключи/включи VPN; "
    "если на Wi‑Fi работает — напиши оператора в поддержку. "
    "Жёсткий блок LTE → <b>Hiddify</b> / <b>Streisand</b> с той же ссылкой.\n\n"
    "<b>Windows: Telegram / ChatGPT не открываются</b> — включи <b>TUN</b> "
    "(Настройки → Дополнительно) и обнови подписку.\n\n"
    f"• <a href=\"{public_status_url()}\">Статус сервиса</a>\n"
    "• Напиши нам — кнопка ниже."
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
    if device_id == "windows":
        text += (
            "\n\n<b>Windows:</b> Настройки Happ → Дополнительно → включите <b>TUN</b>. "
            "Обновите подписку (🔄) — профиль маршрутизации подтянется сам."
        )
    return text
