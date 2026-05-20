from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from shop_bot.config import (
    TELEGRAM_WEBAPP_URL,
    telegram_cabinet_webapp_url,
    telegram_portal_webapp_url,
)
from shop_bot.vpn_setup_wizard import device_ids
from shop_bot.bot import portal_links

from shop_bot.config import DAILY_RATE, TOPUP_PRESETS, topup_button_label


main_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="\U0001f3e0 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e")]],
    resize_keyboard=True
)


def _add_portal_link_buttons(builder: InlineKeyboardBuilder, setup_url: str | None = None) -> None:
    """Instruction / browser / video links — use in help submenu, not main menu."""
    if TELEGRAM_WEBAPP_URL:
        builder.button(
            text="\U0001f4f1 \u0418\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u044f (Mini App)",
            web_app=WebAppInfo(url=TELEGRAM_WEBAPP_URL),
        )
    if portal_links.PUBLIC_BOOTSTRAP_URL:
        builder.button(
            text="\U0001f310 \u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0432 \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0435",
            url=portal_links.PUBLIC_BOOTSTRAP_URL,
        )
    guide_url = portal_links.public_guide_url()
    if guide_url:
        builder.button(
            text="\U0001f3ac \u0412\u0438\u0434\u0435\u043e: \u043a\u0430\u043a \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c",
            url=guide_url,
        )
    errors_url = portal_links.public_errors_url()
    if errors_url:
        builder.button(
            text="\u2753 \u0427\u0430\u0441\u0442\u044b\u0435 \u043e\u0448\u0438\u0431\u043a\u0438",
            url=errors_url,
        )
    if setup_url:
        builder.button(
            text="\U0001f517 \u041c\u043e\u044f \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430",
            url=setup_url,
        )


def create_help_menu_keyboard(setup_url: str | None = None):
    builder = InlineKeyboardBuilder()
    _add_portal_link_buttons(builder, setup_url=setup_url)
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_main_menu_keyboard(
    has_active_sub=False,
    trial_available=True,
    is_admin=False,
    telegram_id: int | None = None,
    for_simulation: bool = False,
    **kwargs,
):
    builder = InlineKeyboardBuilder()
    if has_active_sub:
        if TELEGRAM_WEBAPP_URL and not for_simulation:
            builder.button(
                text="\U0001f3e0 \u041b\u0438\u0447\u043d\u044b\u0439 \u043a\u0430\u0431\u0438\u043d\u0435\u0442",
                web_app=WebAppInfo(url=telegram_cabinet_webapp_url(telegram_id)),
            )
        builder.button(
            text="\U0001f50c \u041c\u043e\u0439 VPN",
            callback_data="my_account",
        )
        builder.button(
            text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441",
            callback_data="show_topup",
        )
    else:
        if trial_available:
            builder.button(
                text="\U0001f381 \u041d\u0430\u0447\u0430\u0442\u044c \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e",
                callback_data="get_trial",
            )
        builder.button(
            text="\U0001f4d6 \u041a\u0430\u043a \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c",
            callback_data="menu_help",
        )
        builder.button(
            text="\U0001f50c \u041c\u0430\u0441\u0442\u0435\u0440 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
            callback_data="connect_vpn",
        )
        if not trial_available:
            builder.button(
                text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441",
                callback_data="show_topup",
            )
    builder.button(text="\u2753 \u041f\u043e\u043c\u043e\u0449\u044c", callback_data="menu_help")
    builder.button(text="\U0001f4ac \u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u043d\u0430\u043c", callback_data="contact_support")
    if is_admin:
        builder.button(
            text="\u2699\ufe0f \u0410\u0434\u043c\u0438\u043d-\u043f\u0430\u043d\u0435\u043b\u044c",
            callback_data="open_admin_panel",
        )
    builder.adjust(1)
    return builder.as_markup()


def create_trial_success_keyboard(sub_url, telegram_id: int | None = None):
    """После trial: QR + кабинет, без лишних ссылок."""
    builder = InlineKeyboardBuilder()
    if TELEGRAM_WEBAPP_URL and telegram_id:
        builder.button(
            text="\U0001f3e0 \u041b\u0438\u0447\u043d\u044b\u0439 \u043a\u0430\u0431\u0438\u043d\u0435\u0442",
            web_app=WebAppInfo(url=telegram_cabinet_webapp_url(telegram_id)),
        )
    if sub_url:
        builder.button(text="\U0001f4f7 QR \u0434\u043b\u044f Happ", callback_data="show_sub_qr")
    builder.button(text="\U0001f4d6 \u041a\u0430\u043a \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c", callback_data="connect_vpn")
    builder.button(text="\U0001f519 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_account_keyboard(sub_url=None, telegram_id: int | None = None):
    builder = InlineKeyboardBuilder()
    if TELEGRAM_WEBAPP_URL and telegram_id:
        builder.button(
            text="\U0001f3e0 \u041b\u0438\u0447\u043d\u044b\u0439 \u043a\u0430\u0431\u0438\u043d\u0435\u0442",
            web_app=WebAppInfo(url=telegram_cabinet_webapp_url(telegram_id)),
        )
    if sub_url:
        builder.button(
            text="\U0001f4cb \u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0441\u044b\u043b\u043a\u0443 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0438",
            callback_data="copy_sub_url",
        )
    builder.button(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441", callback_data="show_topup")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_account_no_sub_keyboard(trial_available):
    builder = InlineKeyboardBuilder()
    if trial_available:
        builder.button(
            text="🎁 Бесплатно 3 месяца",
            callback_data="get_trial",
        )
    else:
        builder.button(text="\U0001f4b0 \u041f\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0430\u043b\u0430\u043d\u0441", callback_data="show_topup")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_topup_keyboard():
    builder = InlineKeyboardBuilder()
    for topup_id, (_name, _price_str, amount) in TOPUP_PRESETS.items():
        builder.button(text=topup_button_label(amount), callback_data=topup_id)
    builder.button(text="\U0001f4ac \u0414\u0440\u0443\u0433\u0430\u044f \u0441\u0443\u043c\u043c\u0430", callback_data="topup_custom")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_topup_payment_keyboard(topup_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="\u2b50 Telegram Stars", callback_data=f"pay_stars_topup_{topup_id}")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="show_topup")
    builder.adjust(1)
    return builder.as_markup()


def create_invite_keyboard(ref_url):
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f4cb \u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0440\u0435\u0444\u0435\u0440\u0430\u043b\u044c\u043d\u0443\u044e \u0441\u0441\u044b\u043b\u043a\u0443", callback_data="copy_ref_url")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="my_account")
    builder.adjust(1)
    return builder.as_markup()


def create_back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    return builder.as_markup()


def create_wizard_device_picker_keyboard():
    builder = InlineKeyboardBuilder()
    from shop_bot.vpn_setup_wizard import DEVICES

    for dev_id in device_ids():
        dev = DEVICES[dev_id]
        builder.button(
            text=f"{dev['icon']} {dev['label']}",
            callback_data=f"wizard_pick_{dev_id}",
        )
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_wizard_device_keyboard(
    device_id: str,
    *,
    trial_available: bool = True,
    setup_url: str | None = None,
):
    builder = InlineKeyboardBuilder()
    if TELEGRAM_WEBAPP_URL:
        builder.button(
            text="\U0001f4f1 \u0418\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u044f \u0432 Mini App",
            web_app=WebAppInfo(url=telegram_portal_webapp_url(device_id)),
        )
    builder.button(
        text="\U0001f4dd \u041f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0438 \u0432 \u0447\u0430\u0442\u0435",
        callback_data=f"wizard_chat_{device_id}",
    )
    if trial_available:
        builder.button(text="\U0001f381 \u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e 3 \u043c\u0435\u0441\u044f\u0446\u0430", callback_data="get_trial")
    if setup_url:
        builder.button(
            text="\U0001f517 \u041c\u043e\u044f \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430",
            url=setup_url,
        )
    builder.button(text="\U0001f4f7 QR \u0434\u043b\u044f Happ", callback_data="show_sub_qr")
    if device_id in ("iphone", "android"):
        builder.button(
            text="\U0001f3ac \u0412\u0438\u0434\u0435\u043e \u0434\u043b\u044f \u044d\u0442\u043e\u0433\u043e \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0430",
            url=portal_links.public_guide_url(device_id),
        )
    store_key = device_id
    from shop_bot.vpn_setup_wizard import DEVICES, HAPP_STORES

    sk = DEVICES.get(device_id, {}).get("store_key", device_id)
    if sk in HAPP_STORES:
        label, url = HAPP_STORES[sk]
        builder.button(text=f"\u2193 {label[:40]}", url=url)
    builder.button(text="\u2753 \u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442\u0441\u044f", callback_data="wizard_stuck")
    builder.button(text="\U0001f519 \u041a \u0432\u044b\u0431\u043e\u0440\u0443 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0430", callback_data="connect_vpn")
    builder.button(text="\U0001f3e0 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_wizard_chat_keyboard(device_id: str):
    builder = InlineKeyboardBuilder()
    if TELEGRAM_WEBAPP_URL:
        builder.button(
            text="\U0001f4f1 \u041e\u0442\u043a\u0440\u044b\u0442\u044c Mini App",
            web_app=WebAppInfo(url=telegram_portal_webapp_url(device_id)),
        )
    builder.button(
        text="\U0001f519 \u041a \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0443",
        callback_data=f"wizard_pick_{device_id}",
    )
    builder.button(text="\U0001f519 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f39f \u041f\u0440\u043e\u043c\u043e\u043a\u043e\u0434\u044b", callback_data="admin_promos")
    builder.button(text="\U0001f4c8 \u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430", callback_data="admin_stats")
    builder.button(text="\U0001f4be \u0411\u044d\u043a\u0430\u043f", callback_data="admin_backup")
    builder.button(
        text="\U0001f9ea \u0422\u0435\u0441\u0442 \u0444\u043b\u043e\u0443",
        callback_data="admin_flow_test_menu",
    )
    builder.button(text="\u2b05\ufe0f \u0412\u044b\u0439\u0442\u0438", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_admin_flow_test_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\U0001f9ed \u0413\u0438\u0434: \u043d\u043e\u0432\u0438\u043a \u0432 \u0431\u043e\u0442\u0435",
        callback_data="admin_flow_g_nb_1",
    )
    builder.button(
        text="\U0001f9ed \u0413\u0438\u0434: \u043f\u043e\u0434\u043f\u0438\u0441\u0447\u0438\u043a",
        callback_data="admin_flow_g_ex_1",
    )
    builder.button(
        text="\U0001f9ed \u0413\u0438\u0434: email / \u0441\u0430\u0439\u0442 (web)",
        callback_data="admin_flow_g_web_1",
    )
    builder.button(
        text="\U0001f527 \u0414\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430 \u0441\u0435\u0440\u0432\u0435\u0440\u0430",
        callback_data="admin_flow_smoke_all",
    )
    builder.button(text="\u2b05\ufe0f \u0412 \u0430\u0434\u043c\u0438\u043d-\u043f\u0430\u043d\u0435\u043b\u044c", callback_data="open_admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def create_admin_demo_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\u2705 \u041f\u0440\u0438\u043d\u0438\u043c\u0430\u044e (\u0434\u0435\u043c\u043e)",
        callback_data="admin_demo_agree",
    )
    return builder.as_markup()


def create_admin_guide_nb_step1_keyboard():
    """Новичок шаг 1 — без merge двух markup (Telegram иногда ломает edit)."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\u2705 \u041f\u0440\u0438\u043d\u0438\u043c\u0430\u044e (\u0434\u0435\u043c\u043e \u2192 \u0448\u0430\u0433 2)",
        callback_data="admin_demo_agree",
    )
    builder.button(text="\u0414\u0430\u043b\u0435\u0435 \u25b6\ufe0f", callback_data="admin_flow_g_nb_2")
    builder.button(
        text="\U0001f519 \u041a \u0442\u0435\u0441\u0442\u0430\u043c \u0444\u043b\u043e\u0443",
        callback_data="admin_flow_test_menu",
    )
    builder.adjust(1)
    return builder.as_markup()


def create_admin_guide_nb_step2_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="\U0001f381 \u041d\u0430\u0447\u0430\u0442\u044c \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e (\u0434\u0435\u043c\u043e)",
        callback_data="admin_demo_hint_trial",
    )
    builder.button(
        text="\U0001f4d6 \u041a\u0430\u043a \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c (\u0434\u0435\u043c\u043e)",
        callback_data="admin_demo_hint_help",
    )
    builder.button(text="\u25c0\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="admin_flow_g_nb_1")
    builder.button(text="\u0414\u0430\u043b\u0435\u0435 \u25b6\ufe0f", callback_data="admin_flow_g_nb_3")
    builder.button(
        text="\U0001f519 \u041a \u0442\u0435\u0441\u0442\u0430\u043c \u0444\u043b\u043e\u0443",
        callback_data="admin_flow_test_menu",
    )
    builder.adjust(1)
    return builder.as_markup()


def create_admin_guide_nb_step3_keyboard():
    return create_admin_flow_nav_keyboard("nb", 3, 4)


def create_admin_guide_nb_step4_keyboard(extra: list[tuple[str, str]] | None = None):
    return create_admin_flow_nav_keyboard("nb", 4, 4, extra)


def create_admin_flow_nav_keyboard(
    flow: str,
    step: int,
    total: int,
    extra: list[tuple[str, str]] | None = None,
):
    builder = InlineKeyboardBuilder()
    for text, data in extra or []:
        if data.startswith("http"):
            builder.button(text=text, url=data)
        else:
            builder.button(text=text, callback_data=data)
    if step > 1:
        builder.button(
            text="\u25c0\ufe0f \u041d\u0430\u0437\u0430\u0434",
            callback_data=f"admin_flow_g_{flow}_{step - 1}",
        )
    if step < total:
        builder.button(
            text="\u0414\u0430\u043b\u0435\u0435 \u25b6\ufe0f",
            callback_data=f"admin_flow_g_{flow}_{step + 1}",
        )
    builder.button(
        text="\U0001f519 \u041a \u0442\u0435\u0441\u0442\u0430\u043c \u0444\u043b\u043e\u0443",
        callback_data="admin_flow_test_menu",
    )
    builder.adjust(1)
    return builder.as_markup()


def with_admin_flow_back(markup):
    """Main menu (or other) + return to flow test menu."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [list(row) for row in markup.inline_keyboard]
    rows.append(
        [
            InlineKeyboardButton(
                text="\U0001f519 \u041a \u0442\u0435\u0441\u0442\u0430\u043c \u0444\u043b\u043e\u0443",
                callback_data="admin_flow_test_menu",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def create_admin_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\u274c \u041e\u0442\u043c\u0435\u043d\u0430", callback_data="admin_cancel_edit")
    return builder.as_markup()


def create_admin_promos_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\u2795 \u0421\u043e\u0437\u0434\u0430\u0442\u044c", callback_data="admin_promo_create")
    builder.button(text="\U0001f4cb \u0421\u043f\u0438\u0441\u043e\u043a", callback_data="admin_promo_list")
    builder.button(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="open_admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def create_plans_keyboard(plans, action, key_id=0):
    builder = InlineKeyboardBuilder()
    for plan_id, (name, price_rub, _) in plans.items():
        builder.button(text=f"{name} - {float(price_rub):.0f} RUB", callback_data=f"{plan_id}_{action}_{key_id}")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_payment_method_keyboard(payment_methods, plan_id, action, key_id):
    builder = InlineKeyboardBuilder()
    if payment_methods.get("stars"):
        builder.button(text="\u2b50 Telegram Stars", callback_data=f"pay_stars_{plan_id}_{action}_{key_id}")
    if payment_methods.get("yookassa"):
        builder.button(text="\U0001f4b3 \u041a\u0430\u0440\u0442\u0430", callback_data=f"pay_yookassa_{plan_id}_{action}_{key_id}")
    if payment_methods.get("crypto"):
        builder.button(text="\U0001f48e \u041a\u0440\u0438\u043f\u0442\u043e", callback_data=f"pay_crypto_{plan_id}_{action}_{key_id}")
    builder.button(text="\U0001f519 \u041d\u0430\u0437\u0430\u0434", callback_data="back_to_main_menu")
    builder.adjust(1)
    return builder.as_markup()


def create_payment_keyboard(payment_url):
    builder = InlineKeyboardBuilder()
    builder.button(text="\u041f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u043e\u043f\u043b\u0430\u0442\u0435", url=payment_url)
    return builder.as_markup()


def create_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="\u2705 \u041f\u0440\u0438\u043d\u0438\u043c\u0430\u044e", callback_data="agree_to_terms")
    return builder.as_markup()


# Legacy stubs
def create_keys_management_keyboard(keys): return create_back_to_menu_keyboard()
def create_key_info_keyboard(key_id): return create_back_to_menu_keyboard()
def create_back_to_key_keyboard(key_id): return create_back_to_menu_keyboard()
def create_traffic_keyboard(): return create_back_to_menu_keyboard()
def create_support_keyboard(u): return create_back_to_menu_keyboard()
def create_about_keyboard(t, p): return create_back_to_menu_keyboard()
def create_about_keyboard_terms(t): return create_back_to_menu_keyboard()
def create_about_keyboard_privacy(p): return create_back_to_menu_keyboard()
def create_traffic_packs_keyboard(p, k): return create_back_to_menu_keyboard()
def create_promo_enter_keyboard(): return create_back_to_menu_keyboard()
def create_autorenew_toggle_keyboard(e): return create_back_to_menu_keyboard()
