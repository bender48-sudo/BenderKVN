# Runbook: безопасный накат compose/env на AMS (gate перед render)

**ID бэклога:** **`P2-OPS-AMS-SAFE-DEPLOY-01`**  
**Контекст:** инцидент **2026-05-17** — накат `panel.env` / `sub/docker-compose.yml` из vault без сверки с живым Postgres и **`REMNA_API_TOKEN`** → **502** / Prisma **P1000** (журнал **`docs/COMMERCIAL-BACKLOG.md` §12**).

Цель: **не перезаписывать** `/opt/remnawave/*`, `/opt/remnawave/sub/*`, `/opt/remna-shop/.env` на AMS без проверок ниже.

---

## 0. Когда обязателен этот runbook

- Любой накат **рендера** из **`compose/ams/**`** (`panel.env`, `docker-compose.yml`, `sub/`, `remna-shop/`).
- После **`python ops/sanitize_compose_templates.py`** или массового **`extract_vault.py`**.
- **Не** нужен для деплоя только **`/opt/scripts/*`** (см. **`docs/DEPLOY.md` §3**).

---

## 1. Чеклист (выполнять по порядку)

| # | Шаг | Критерий |
|---|-----|----------|
| 1 | **Бэкап на AMS** | Копии целевых файлов: `cp … …before-safe-deploy-$(date +%Y%m%d-%H%M%S)` для `.env`, `docker-compose.yml`, `sub/docker-compose.yml`, `sub/.env`, `/opt/remna-shop/.env`. |
| 2 | **Vault актуален** | Свежие снимки в **`.secrets/prod-compose/`** (SCP с AMS), затем **`python ops/extract_vault.py`**. **Не** править **`DATABASE_URL`** / **`REMNA_API_TOKEN_*`** «на глаз». |
| 3 | **Dry-run токена** | **`bash ops/remna_api_token_rollout.sh dry-run`** и/или **`verify-ams`** — без расхождения sub/shop/LV env. |
| 4 | **Локальный drift** | **`python ops/drift-check.py`** — понимать, *какие* пары изменятся; при неожиданном DRIFT по `panel.env` — стоп, сверить vault с прод-бэкапом. |
| 5 | **Рендер в /tmp** | Рендер **не** напрямую в `/opt/…`: `python ops/render_compose.py … > /tmp/rendered-…`, сравнить diff с продом (`diff -u` или md5 только после нормализации CRLF). |
| 6 | **Sub compose** | В **`sub/docker-compose.yml`** на проде — только **`REMNAWAVE_API_TOKEN=${REMNA_API_TOKEN}`**, **без** inline `eyJ…` (**`docs/RUNBOOK-REMNA-API-TOKEN.md`**). |
| 7 | **Накат + перезапуск** | `install` файлов → **`docker compose up -d`** в нужных каталогах; для панели при смене Postgres — только по **`docs/RUNBOOK-P0-SEC04-SEC05.md`**. |
| 8 | **Smoke** | Панель **200**, публичная подписка **200/304**, **`python ops/subscription_load_probe.py --total 20`** (p95 и гистограмма в §12). |
| 9 | **Drift после** | **`python ops/drift-check.py`** exit **0** или осознанный waive в **`docs/DRIFT-POST-P0.md`**. |
| 10 | **Журнал** | Строка **`docs/COMMERCIAL-BACKLOG.md` §12**: что накатили, smoke, probe JSON (кратко). |

---

## 2. Откат (1 команда на файл)

Восстановить из **`*.before-safe-deploy-*`** или **`*.before-drift-*`** (см. инцидент **2026-05-17**), затем:

```bash
cd /opt/remnawave && docker compose up -d
cd /opt/remnawave/sub && docker compose up -d
cd /opt/remna-shop && docker compose up -d
```

Повторить smoke из п. **8**.

---

## 3. Связанные документы

- **`docs/DEPLOY.md` §7.2–7.3** — render, sanitize, extract_vault  
- **`docs/RUNBOOK-REMNA-API-TOKEN.md`**  
- **`docs/KNOWLEDGE-BASE.md`** — типовая ошибка P1000 / 502  
