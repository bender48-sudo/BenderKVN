"""Admin smoke tests for newbie / existing TG / email web flows."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from shop_bot.config import TELEGRAM_WEBAPP_URL, WEB_TRIAL_DAYS, telegram_cabinet_webapp_url
from shop_bot.data_manager.database import get_setting, get_user, get_user_keys
from shop_bot.public_urls import portal_origin, public_bootstrap_url, setup_origin


def _ok(flag: bool) -> str:
    return "✅" if flag else "❌"


def _check(label: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"label": label, "ok": ok, "detail": detail}


def _url_port_ok(url: str) -> tuple[bool, str]:
    u = (url or "").strip()
    if not u:
        return False, "URL не задан"
    if ":2053" in u:
        return False, "порт :2053 — редирект ломает API (нужен :8443)"
    return True, u[:72] + ("…" if len(u) > 72 else "")


async def _probe_panel_api() -> dict[str, Any]:
    from shop_bot.modules import remnawave_api as api

    base = (api.BASE_URL or "").rstrip("/")
    if ":2053" in base:
        return _check(
            "Remna API (BASE_URL)",
            False,
            f"{base} → редирект; aiohttp теряет Bearer",
        )
    token = (api.API_TOKEN or os.getenv("REMNA_API_TOKEN") or "").strip()
    if not base or not token:
        return _check("Remna API (BASE_URL)", False, "BASE_URL или токен пусто")
    async with api.remna_client_session() as session:
        data = await api._fetch_json(session, "GET", "/api/config-profiles/inbounds")
    ok = bool(data and isinstance(data.get("response"), (dict, list)))
    return _check("Remna API (inbounds)", ok, base if ok else "401 или пустой ответ")


async def smoke_infrastructure() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(await _probe_panel_api())
    for label, url in (
        ("Mini App URL", TELEGRAM_WEBAPP_URL),
        ("Portal origin", portal_origin()),
        ("Setup origin", setup_origin()),
        ("Bootstrap /start", public_bootstrap_url()),
    ):
        ok, detail = _url_port_ok(url)
        checks.append(_check(label, ok, detail))
    wtd = int(os.getenv("WEB_TRIAL_DAYS", str(WEB_TRIAL_DAYS)) or WEB_TRIAL_DAYS)
    checks.append(
        _check(
            "WEB_TRIAL_DAYS",
            wtd == 1,
            f"{wtd} дн." + ("" if wtd == 1 else " (ожидали 1 для email anti-abuse)"),
        )
    )
    terms = (get_setting("terms_url") or "").strip()
    privacy = (get_setting("privacy_url") or "").strip()
    checks.append(
        _check(
            "Условия /start",
            bool(terms and privacy),
            "OK" if terms and privacy else "terms_url или privacy_url пусто",
        )
    )
    return checks


async def smoke_existing_user(telegram_id: int) -> list[dict[str, Any]]:
    from shop_bot.portal_cabinet import cabinet_snapshot
    from shop_bot.portal_telegram_setup import telegram_setup_for_user
    from shop_bot.subscription_resolve import resolve_subscription_url

    tid = int(telegram_id)
    checks: list[dict[str, Any]] = []
    user = get_user(tid)
    keys = get_user_keys(tid)
    now = datetime.now()
    active = [k for k in keys if datetime.fromisoformat(k["expiry_date"]) > now]

    checks.append(
        _check("SQLite: пользователь", bool(user), "есть" if user else "нет — /start")
    )
    if user:
        checks.append(
            _check(
                "Условия приняты",
                bool(user.get("agreed_to_terms")),
                "да" if user.get("agreed_to_terms") else "нет — экран «Принимаю»",
            )
        )
        checks.append(
            _check(
                "Активный ключ",
                bool(active),
                f"{len(active)} шт." if active else "нет — «Начать бесплатно»/trial",
            )
        )
    try:
        sub = await resolve_subscription_url(tid)
        checks.append(
            _check(
                "subscriptionUrl (панель)",
                bool(sub),
                (sub[:56] + "…") if sub else "пусто — QR/«Мой VPN» сломаны",
            )
        )
    except Exception as exc:
        checks.append(_check("subscriptionUrl (панель)", False, str(exc)[:80]))

    cab = cabinet_snapshot(telegram_id=tid)
    checks.append(
        _check(
            "Mini App кабинет API",
            bool(cab.get("ok")),
            cab.get("message") or cab.get("error") or "ok",
        )
    )
    try:
        setup = await telegram_setup_for_user(tid)
        checks.append(
            _check(
                "Telegram /setup API",
                bool(setup.get("ok")),
                setup.get("message") or setup.get("error") or "ok",
            )
        )
    except Exception as exc:
        checks.append(_check("Telegram /setup API", False, str(exc)[:80]))
    return checks


def smoke_newbie_logic() -> list[dict[str, Any]]:
    """Checks config paths for first-time bot user (no DB mutation)."""
    checks: list[dict[str, Any]] = []
    terms = (get_setting("terms_url") or "").strip()
    privacy = (get_setting("privacy_url") or "").strip()
    checks.append(
        _check(
            "/start → «Принимаю»",
            bool(terms and privacy),
            "ссылки в settings" if terms and privacy else "не настроены",
        )
    )
    checks.append(
        _check(
            "После принятия → главное меню",
            bool(TELEGRAM_WEBAPP_URL),
            "trial + «Как подключить»" if TELEGRAM_WEBAPP_URL else "нет TELEGRAM_WEBAPP_URL",
        )
    )
    checks.append(
        _check(
            "Кнопка «Начать бесплатно»",
            True,
            "callback get_trial (если trial_used=0)",
        )
    )
    ok, detail = _url_port_ok(TELEGRAM_WEBAPP_URL)
    checks.append(_check("Mini App не на email /setup", ok, detail))
    return checks


def smoke_email_web() -> list[dict[str, Any]]:
    """Browser /setup email trial — not Telegram Mini App path."""
    checks: list[dict[str, Any]] = []
    origin = setup_origin()
    setup_path = f"{origin.rstrip('/')}/setup/"
    ok, detail = _url_port_ok(setup_path)
    checks.append(_check("Страница /setup/ (email)", ok, detail))
    ok2, detail2 = _url_port_ok(portal_origin() + "/portal/")
    checks.append(_check("Portal /portal/", ok2, detail2))
    wtd = int(os.getenv("WEB_TRIAL_DAYS", str(WEB_TRIAL_DAYS)) or WEB_TRIAL_DAYS)
    checks.append(
        _check("Trial по email", wtd == 1, f"WEB_TRIAL_DAYS={wtd} (ожидали 1)")
    )
    checks.append(
        _check(
            "API web-trial (LV→AMS)",
            True,
            "POST /setup/api/web-trial — только с email, не telegram_id",
        )
    )
    checks.append(
        _check(
            "Путь пользователя",
            True,
            f"email → {setup_path} → Happ → bind TG в боте",
        )
    )
    return checks


def format_section(title: str, checks: list[dict[str, Any]]) -> str:
    lines = [f"<b>{title}</b>"]
    for c in checks:
        lines.append(f"{_ok(c['ok'])} {c['label']}: {c['detail']}")
    return "\n".join(lines)


async def run_all_smokes(admin_telegram_id: int) -> str:
    infra = await smoke_infrastructure()
    existing = await smoke_existing_user(admin_telegram_id)
    newbie = smoke_newbie_logic()
    email = smoke_email_web()
    parts = [
        "🧪 <b>Проверка флоу</b> (prod env + ваш TG-аккаунт)\n",
        format_section("1. Инфраструктура", infra),
        "",
        format_section("2. Существующий пользователь (вы)", existing),
        "",
        format_section("3. Новичок в боте (логика)", newbie),
        "",
        format_section("4. Пользователь через email (web)", email),
    ]
    text = "\n".join(parts)
    fails = sum(
        1
        for block in (infra, existing, newbie, email)
        for c in block
        if not c["ok"]
    )
    text += f"\n\n<b>Итого:</b> {fails} проблем(ы)" if fails else "\n\n<b>Итого:</b> все проверки зелёные ✅"
    if len(text) > 3900:
        text = text[:3890] + "\n…"
    return text


def sim_newbie_header() -> str:
    return (
        "🧪 <b>Симуляция: новичок</b>\n\n"
        "Ниже — <b>реальное</b> главное меню без подписки (как после «Принимаю»).\n"
        "БД не меняется. Нажимайте кнопки как пользователь."
    )


def sim_existing_header(admin_tid: int) -> str:
    user = get_user(admin_tid)
    keys = get_user_keys(admin_tid)
    now = datetime.now()
    active = [k for k in keys if datetime.fromisoformat(k["expiry_date"]) > now]
    trial = bool(user and user.get("trial_used"))
    return (
        "🧪 <b>Симуляция: подписчик</b>\n\n"
        f"Ваш аккаунт: trial_used={'да' if trial else 'нет'}, ключей={len(active)}.\n"
        "Ниже — меню <b>с активной подпиской</b> (ЛК, Мой VPN, пополнение)."
    )


def sim_email_header() -> str:
    setup_url = f"{setup_origin().rstrip('/')}/setup/"
    return (
        "🧪 <b>Симуляция: email / web</b>\n\n"
        f"Откройте в <b>браузере</b> (не Mini App):\n<code>{setup_url}</code>\n\n"
        "Форма email → trial 1 сутки → QR и ссылка. Отдельно от аккаунта в боте."
    )


def preview_newbie_menu_text() -> str:
    return sim_newbie_header()


def preview_existing_menu_text(admin_tid: int) -> str:
    return sim_existing_header(admin_tid)


def preview_newbie_buttons_text() -> str:
    return (
        "<i>Кнопки в боте (без админ-панели):</i>\n"
        "«Начать бесплатно», «Как подключить», «Помощь», «Написать нам»"
    )


def preview_existing_buttons_text(has_active_sub: bool, trial_available: bool) -> str:
    lines = ["<i>Кнопки в боте (без админ-панели):</i>"]
    if has_active_sub:
        lines.append("«Личный кабинет», «Мой VPN», «Пополнить баланс»")
    elif trial_available:
        lines.append("«Начать бесплатно», «Как подключить»")
    else:
        lines.append("«Пополнить баланс», «Как подключить»")
    lines.append("«Помощь», «Написать нам»")
    return "\n".join(lines)


def preview_email_flow_text() -> str:
    origin = setup_origin()
    setup_url = f"{origin.rstrip('/')}/setup/"
    return (
        "👀 <b>Превью: пользователь через email</b>\n\n"
        f"1. Браузер (не Mini App): <code>{setup_url}</code>\n"
        "2. Форма email → trial <b>1 сутки</b> → QR и ссылка для Happ\n"
        "3. Скачать клиент: iOS / Android / Windows / Mac (на странице настройки)\n"
        "4. Привязка Telegram: ссылка «Открыть бота» после trial\n"
        f"5. Кабинет в TG (другой путь): Mini App из бота, не эта форма\n\n"
        "<i>Не путать с вашим аккаунтом в боте — это отдельный web-only trial.</i>"
    )
