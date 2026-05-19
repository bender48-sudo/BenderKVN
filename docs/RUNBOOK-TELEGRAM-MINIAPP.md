# Telegram Mini App (P3-FLOW-12)

Один и тот же bundle, что на сайте: **`web/portal/`** → **`https://k9x2m1.conntest.xyz:8443/portal/`**.

UI ориентирован на **HITVPN**: тёмный градиент, pills «Быстро / Стабильно / Безопасно», крупные CTA, нумерованные шаги.

## BotFather (владелец, один раз)

1. [@BotFather](https://t.me/BotFather) → ваш бот → **Bot Settings** → **Menu Button** → **Configure menu button**.
2. Тип **Web App**, URL:

   `https://k9x2m1.conntest.xyz:8443/portal/`

   Должен совпадать с **`TELEGRAM_WEBAPP_URL`** в env бота и **`site_urls.telegram_webapp_url()`**.

3. Сохранить. В чате с ботом слева внизу появится кнопка меню «Подключить VPN».

## Бот (AMS)

- Inline-кнопка **«📱 Открыть инструкцию»** в главном меню и после trial — `bot_src/keyboards.py`.
- При старте бот выставляет Menu Button — `bot_src/main.py` (`set_chat_menu_button`).
- Env (опционально, иначе дефолт prod URL):

  `TELEGRAM_WEBAPP_URL=https://k9x2m1.conntest.xyz:8443/portal/`

Деплой:

```powershell
pwsh -File ops/deploy-bot-handlers-ams.ps1
```

## LV (статика)

```powershell
pwsh -File ops/deploy-user-portal-lv.ps1
```

## Проверка

```bash
python ops/portal_bundle_audit.py
python ops/smoke_telegram_miniapp.py   # → TELEGRAM_MINIAPP_PORTAL_OK
```

Ручной тест: Telegram на телефоне → бот → Menu Button или «📱 Открыть инструкцию» → те же шаги, что на `/portal/`, тёмная/светлая тема TG.

## Безопасность

- В Mini App **не** передавать JWT панели или `BOT_TOKEN`.
- Персональная настройка — только **`/setup/?t=`** (Q036), ссылку выдаёт бот в Q038.

## Откат

- BotFather: убрать Web App URL или вернуть прежний.
- Бот: закомментировать `set_chat_menu_button` и WebApp-кнопки; redeploy handlers/keyboards/main.
