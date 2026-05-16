# Панель LV → AMS: следующие шаги (после бэкапов)

Сделано **2026-05-11**:

- Полные бэкапы на **LV**: `/opt/backups/panel-migrate-20260511-182407` (тома + `/opt/remnawave`, `/opt/remnanode`, логический `remnawave-logical.sql.gz`, inspect).
- Бэкапы на **AMS**: `/opt/backups/panel-migrate-20260511-182635`.
- Логический дамп скопирован на AMS:  
  `/opt/backups/panel-migrate-20260511-182635/remnawave-from-lv-logical.sql` (~720 KB plain SQL).

## Безопасность (сделать в ближайшее время)

**Сделано 2026-05-12 (по SSH с вашей машины):**

- **Latvia:** `chmod 600` на `/opt/remnawave/.env`, `/opt/remnanode/.env`.
- **Amsterdam:** `chmod 600` на `/opt/remnawave/.env`, `/opt/caddy/.env`. Отдельного `/opt/remnanode/.env` на AMS нет (у remnanode только `docker-compose.yml` в каталоге).
- **Осталось вручную при следующем заходе на AMS:** `chmod 600` на `/opt/remna-shop/backups/ux-cleanup-20260415-211540/.env` и `.../ux-cleanup-20260416-214102/.env` (ранее были `644`).
- **Caddy на LV:** в `/etc/caddy/Caddyfile` пока **нет** `log_skip` для путей подписки — в `sub-access.log` тысячи строк с `/api/` и `/sub/`, то есть **URI с токеном могли писаться в лог**. Имеет смысл один раз применить готовый сценарий `ops/fix-caddy-security.sh` на **bvpn-lv** (бэкап `Caddyfile.bak-20260511-security` уже есть на сервере), затем `caddy validate` и `systemctl restart caddy`.

В `docker-compose.yml` на LV и в `/opt/remnawave/sub/docker-compose.yml` на AMS в репозитории **не хранить** `REMNAWAVE_API_TOKEN` — только через `.env` / secrets. После стабилизации миграции **перевыпустить API-токен** в Remnawave UI (старые попадали в логи/вывод).

## Перед cutover (окно обслуживания)

1. **Согласовать даунтайм** (панель недоступна N минут).
2. На **AMS** проверить сеть Docker: `docker network ls | grep remnawave` — для `sub` нужна `remnawave-network` (external).
3. **Вариант A (рекомендуемый):** поднять на AMS полный стек как на LV (`postgres` + `valkey` + `remnawave` backend) из **актуального** `/opt/remnawave/docker-compose.yml` LV (скопировать compose + `.env` + `patches/`), **без** дублирующего subscription в том же compose на первом шаге — оставить существующий `sub/docker-compose.yml`, но обновить там только `REMNAWAVE_API_TOKEN` и убедиться, что `remnawave` контейнер в той же сети.
4. Импорт БД на AMS: новый Postgres из compose → `psql ... < remnawave-from-lv-logical.sql` (после `CREATE` чистой БД или в пустую БД с тем же именем, как в `.env`).
5. Health: `curl` к metrics порту backend, вход в панель.
6. **Ноды** (LV, AMS, позже NL): в `.env` remnanode или в UI обновить URL панели, если меняется публичный endpoint.
7. **Бот** `/opt/remna-shop`: переменные API панели под новый хост/URL.
8. **Caddy** на LV/AMS: маршруты на панель и subscription — под новую схему.
9. Только после проверки: **остановить** на LV `remnawave`, `remnawave-db`, `remnawave-redis` и subscription из основного compose, **оставить** `remnanode` и AdGuard.

## Откат

См. `ops/PANEL-MIGRATION-ROLLBACK.md`. При сбое на AMS — не трогать LV до восстановления; при сбое после остановки LV — поднимать LV из `panel-migrate-20260511-182407`.

---

Дальнейшие команды cutover **не выполнялись** в этой сессии — только бэкап и перенос файла дампа. Напишите **«окно N минут, делаем cutover»**, когда готовы — продолжим по пунктам с подтверждением после каждого критичного шага.
