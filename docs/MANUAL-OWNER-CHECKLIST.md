# Чеклист владельца (только то, что агент не может)

Задачи, требующие **вашего** аккаунта, юридического решения или физического устройства.  
**Агент + терминал:** **`docs/AGENT-PROD-DEPLOY-BACKLOG.md`** (**Q079–Q084** в **`BACKLOG-QUEUE.md`**).

---

## Очередь

| Кто | Q | Что |
|-----|---|-----|
| **Агент** | **Q079–Q084** | Деплой бота, Caddy :8443, panel bind, SSH, smokes, drift |
| **Владелец** | **Q032** | Текст возвратов в оферте (telegra.ph) |
| **Владелец** | ниже § | BotFather, DNSSEC, видео, 2FA регистраторов |

---

## Q032 — возвраты (до GTM)

- [ ] Дописать блок возвратов при массовом дауне в оферте (**P5-COM-02**).
- [ ] Опубликовать / обновить ссылку в боте.

*Черновик может подготовить агент по запросу; финальное «да» — только вы.*

---

## BotFather / Telegram (~5 мин)

*После **Q080** (агент поднял :8443 на LV).*

- [ ] **BotFather** → Menu Button / Web App URL = **`https://k9x2m1.conntest.xyz:8443/portal/`** (см. **`ops/site.env.example`**).
- [ ] Ручной тест: Mini App на телефоне = тот же экран, что **`/start/`** в браузере (**без VPN**, мобильная сеть).

## Админ: smoke флоу в боте (после деплоя)

- [ ] В **главном меню** есть **«Админ-панель»** (ваш Telegram ID в `ADMIN_TELEGRAM_ID` или `ADMIN_TELEGRAM_IDS` в `/opt/remna-shop/.env`).
- [ ] **Админ-панель** → **«Тест флоу»** → **«Запустить все проверки»** — все строки **✅** (особенно Remna API и `subscriptionUrl`).
- [ ] При регрессе: красные пункты с `:2053` или `401` → **`docs/RUNBOOK-REMNA-API-TOKEN.md`**, `REMNA_BASE_URL=https://…:8443` в `/opt/remna-shop/.env`.

---

## CryptoBot (~2 мин)

*После **Q079**.*

- [ ] Личный кабинет CryptoBot: webhook **POST** (не GET), URL как в **`docs/SECRETS.md`**.

---

## DNS / регистраторы (не блокер первого GTM, желательно)

- [ ] Recovery-коды **Dynadot** в Bitwarden + офлайн.
- [ ] **Второй регистратор** (reserve).
- [ ] **DNSSEC** для `conntest.xyz` → `dnssec_enabled: true` в inventory.
- [ ] Backup apex на втором регистраторе.

*Probe делегирования агент гоняет на LV (**Q083**).*

---

## Видео «первый коннект» (качество UX, не security)

Код и плейсхолдеры на проде (**Q042**); для «бабушки» нужны **живые** записи экрана.

- [ ] Снять iPhone / Android (≤ 90 с): Happ → ссылка/QR → VPN on.
- [ ] Положить в `web/portal/media/` → попросить агента **Q085** (опц.) или самому: `pwsh -File ops/deploy-portal-setup-lv.ps1`.
- [ ] `python ops/smoke_portal_setup_video.py` → **`PORTAL_SETUP_VIDEO_OK`**.

---

## Секреты (один раз; агент не создаёт офлайн-копии)

- [ ] Passphrase **LUKS Postgres AMS** в Bitwarden + **ваша** офлайн-копия (агент: `deploy-postgres-luks-ams.ps1 -ProbeOnly` в **Q083**).
- [x] **`SUPPORT_STAFF_IDS`** на AMS: все, кто отвечает из группы Support (ваш TG + `ADMIN_TELEGRAM_ID`), через запятую. Иначе бот **молча игнорирует** ответы (`Ignored support reply from unauthorized` в логах).
- [ ] **BotFather → Group Privacy → Turn off** для @Bender_KVN_bot (иначе ответы в Support не доходят до клиента).
- [ ] После деплоя email-trial: на AMS в `/opt/remna-shop/.env` — **`WEB_TRIAL_DAYS=1`** (отдельно от `REMNA_TRIAL_DAYS=90` в боте).

---

## Раз в год

- [ ] Tabletop jurisdiction — **`TABLETOP-JURISDICTION-EXERCISE.md`**.

---

## Не ваш ручной труд (делает агент)

| Было в старом чеклисте | Теперь |
|------------------------|--------|
| Деплой бота / webhook smokes | **Q079** |
| Caddy :8443 + portal deploy | **Q080** |
| Panel 127.0.0.1:3000 | **Q081** |
| SSH duplicate key | **Q082** |
| Все smokes / drift | **Q083–Q084** |
| Обновить URL в docs на :8443 | агент в **Q080** / docs sync |
