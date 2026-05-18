# Чеклист владельца (ручные доработки)

Задачи **вне** линейной очереди Q (или согласование после агента). Очередь агента: **`docs/BACKLOG-QUEUE.md`** (**`NEXT`**).

---

## Критично (безопасность / доступ)

- [ ] **LUKS Postgres AMS** — passphrase в Bitwarden **`BenderVPN/ams/postgres-luks-key`** + офлайн-копия.
- [ ] После **перезагрузки AMS** — `pwsh -File ops/deploy-postgres-luks-ams.ps1 -ProbeOnly` (FAIL → unlock по runbook).
- [ ] **`%USERPROFILE%\.ssh\config`** — `bvpn_lv_ed25519` / `bvpn_ams_ed25519`; `.\scripts\ssh-smoke-test.ps1`.
- [ ] **AMS `authorized_keys`** — убрать дубликат **`root@vinni204329`** (оставить **`bender-bvpn_ams_ed25519`**).
- [ ] **Crypto webhook** (если включён) — `CRYPTO_WEBHOOK_SECRET` в `/opt/remna-shop/.env`.
- [ ] **`PORTAL_SETUP_HMAC_SECRET`** на AMS в `/opt/remna-shop/.env` (для ссылок `/setup/?t=` из бота) — см. **`RUNBOOK-USER-BOOTSTRAP-SITE`**.

---

## Portal / Mini App (после Q037)

- [ ] **BotFather** — Menu Button / Web App URL = **`https://k9x2m1.conntest.xyz:2053/portal/`** (как в **`ops/site.env.example`**).
- [ ] Ручной тест: Mini App на телефоне = тот же экран, что **`/start`** в браузере.
- [ ] Деплой portal после правок: `pwsh -File ops/deploy-user-portal-lv.ps1` (если скрипт есть).

---

## Видео «первый коннект» (Q042 — плейсхолдеры → прод)

Сейчас на **`/portal/guide.html`** стоят **схематичные GIF** из репо. Код и кнопки в боте уже на проде; нужны **настоящие** записи экрана.

- [ ] **Снять iPhone** (≤ 90 с): установка Happ → вставка ссылки / QR → включение VPN. Без жаргона (TLS, Reality, shortUuid).
- [ ] **Снять Android** (≤ 90 с): то же для Google Play + Happ.
- [ ] **Положить файлы** в репо (заменить плейсхолдеры):
  - `web/portal/media/ios-first-connect.gif` — или `.mp4`
  - `web/portal/media/android-first-connect.gif` — или `.mp4`
- [ ] **Если MP4** (предпочтительно для качества): в **`web/portal/content/ru.json`** → `setup_videos` указать пути:
  - `media_ios_mp4`: `/portal/media/ios-first-connect.mp4`
  - `media_android_mp4`: `/portal/media/android-first-connect.mp4`
  - (GIF оставить как `poster` / запасной вариант — см. `guide.js`)
- [ ] **Деплой на LV:** `pwsh -File ops/deploy-portal-setup-lv.ps1` (каталог `media/` + `ru.json` + `guide.html`).
- [ ] **Проверка без VPN** с телефона (мобильная сеть, не Wi‑Fi офиса с VPN):
  - [guide.html](https://k9x2m1.conntest.xyz:2053/portal/guide.html) — оба таба открываются, ролик/GIF проигрывается;
  - кнопка в боте **«🎬 Видео: как подключить»** ведёт на ту же страницу;
  - с главной portal и после `/setup/` — ссылка «Видео: как подключить».
- [ ] **Smoke:** `python ops/smoke_portal_setup_video.py` → **`PORTAL_SETUP_VIDEO_OK`**.
- [ ] (Опционально) перегенерировать плейсхолдеры локально: `python ops/generate_setup_guide_media.py` — только для черновика, не для прода.

---

## DNS (P1-RED-DNS-01)

- [ ] Recovery-коды **Dynadot** в Bitwarden + офлайн.
- [ ] **Второй регистратор** (reserve) заведён.
- [ ] **DNSSEC** для `conntest.xyz` → `dnssec_enabled: true` в inventory.
- [ ] Backup apex на втором регистраторе до GTM.

---

## Postgres / AMS ops

- [ ] Legacy docker volume Postgres (после 7 дней стабильности) — backup → `docker volume rm`.
- [ ] Следующий накат compose — только **`RUNBOOK-AMS-SAFE-DEPLOY`**.

---

## Продукт / очередь

| Что | Статус |
|-----|--------|
| Portal + Mini App (Q033–038) | ✅ в репо; см. §12 |
| Видео guide (Q042) | ✅ код на проде; **ручная замена GIF/MP4** — § выше |
| **NEXT агента** | **Q043** — страница ошибок на portal |
| **До GTM** | **Q032** — возвраты в оферте |
| Tabletop jurisdiction | 1×/год — **`TABLETOP-JURISDICTION-EXERCISE.md`** |

**Параллельно (не NEXT):** **P4-DNS-01…06**.

---

## Smoke (здоровье)

```powershell
cd d:\Va\projects\VPN
python ops/portal_bundle_audit.py
python ops/smoke_public_bootstrap.py
python ops/smoke_telegram_miniapp.py
python ops/smoke_portal_setup_video.py
python ops/smoke_ams_safe_deploy.py
ssh bvpn-lv 'python3 /opt/scripts/dns_delegation_probe.py'
ssh bvpn-ams 'python3 /opt/scripts/ams_postgres_crypt_probe.py'
```

Ожидаемые маркеры: **`PORTAL_BUNDLE_OK`**, **`PUBLIC_BOOTSTRAP_OK`**, **`TELEGRAM_MINIAPP_PORTAL_OK`**, **`PORTAL_SETUP_VIDEO_OK`**, **`AMS_SAFE_DEPLOY_OK`**, **`DNS_DELEGATION_OK`**, **`POSTGRES_CRYPT_OK`**.
