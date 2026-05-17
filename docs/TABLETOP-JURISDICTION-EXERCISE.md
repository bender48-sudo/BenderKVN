# Tabletop: jurisdiction / provider failover (ежегодно)

**P3-RED-JURIS-01** — учение **~90 минут**, **1× в год** (рекомендация: январь или после крупного релиза infra).

Участники: **оператор инфры**, **первый ответ поддержки**, **владелец** (принимает go/no-go на DNS и платежи).

Материалы: **`JURISDICTION-FAILOVER-WIKI.md`**, **`RUNBOOK-JURISDICTION-FAILOVER.md`**, распечатка **`ops/jurisdiction_failover_inventory.json`** (без секретов).

## Подготовка (за 3 дня)

- [ ] Назначить фасилитатора и scribe (протокол в Notion).
- [ ] Убедиться, что **`python ops/jurisdiction_failover_audit.py`** → **`JURIS_FAILOVER_OK`** из репо.
- [ ] Проверить доступ: SSH **`bvpn_lv_ed25519`**, **`bvpn_ams_ed25519`**, Bitwarden vault **read** (не обязательно показывать значения).
- [ ] Слот в календаре **без** прод-деплоев в тот же день.

## Сценарий 1 — «LV Hetzner/FH заблокировали» (45 мин)

**Inject (фасилитатор):** «В 10:00 мониторинг: `k9x2m1` и `p4n7q` не отвечают с EU; SSH на 176.126.162.158 timeout. AMS ping OK.»

| Минута | Вопрос команде | Ожидаемый ответ |
|--------|----------------|-----------------|
| 0–10 | Как подтверждаем масштаб без SSH? | `smoke_status_channels`, внешний curl, TG-алерты |
| 10–20 | Что работает у пользователей с конфигом на NL? | Да, если ноды up; нет новой подписки |
| 20–35 | Порядок восстановления edge? | Новый VPS → Caddy → DNS A records → drift/sub probe |
| 35–45 | Текст пользователю? | Шаблон **`USER-INCIDENT-BROADCAST`**, FAQ «обновите подписку» |

**Stop criteria:** назван новый IP, владелец знает, где A-записи в Dynadot, backup apex — когда переключаем.

## Сценарий 2 — «YooKassa заморозила мерчант» (30 мин)

**Inject:** «Webhook 403, ЛК недоступен, VPN и sub 200.»

| Минута | Вопрос | Ожидаемый ответ |
|--------|--------|-----------------|
| 0–10 | Первое действие? | Отключить кнопку YooKassa, включить Stars/crypto, шаблон в боте |
| 10–20 | Как продлить paying user? | Ручной `expireAt`, админ-команды; idempotency webhook |
| 20–30 | Кто обновляет `.env` и restart? | Оператор AMS по **`RUNBOOK-AMS-SAFE-DEPLOY`** / hotfix bot deploy |

## Сценарий 3 — «DNS: взлом Dynadot» (15 мин)

**Inject:** «A-record `k9x2m1` указывает на чужой IP.»

- Recovery codes **офлайн**, не только Bitwarden.
- DNSSEC статус — **`RUNBOOK-DNS-RED-TEAM` §2**.
- Не восстанавливать старый IP без **`dns_delegation_probe`**.

## Завершение (10 мин)

1. Заполнить **post-tabletop** (шаблон ниже).
2. Добавить строку в **`docs/COMMERCIAL-BACKLOG.md` §12`**.
3. Открыть задачи в бэклоге, если нашли пробел (например backup apex пустой).

### Post-tabletop (копировать в Notion)

```
Дата:
Участники:
Сценарии: 1 / 2 / 3
Найденные пробелы:
Действия (владелец / срок):
Следующее учение (дата):
Smoke: JURIS_FAILOVER_OK да/нет
```

## Критерий успеха учения

- Команда **без подсказок** называет 3 документа: jurisdiction runbook, DNS red team, AMS safe-deploy.
- Владелец подтверждает путь к **backup apex** и **офлайн recovery** регистратора.
- Протокол сохранён; **§12** обновлён в течение 48 ч.
