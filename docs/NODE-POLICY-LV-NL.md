# Политика нод Latvia + Netherlands (P6-SCALE-02)

## Роли нод

| Узел | Роль | Примечание |
|------|------|------------|
| **LV** | Production VPN | Основной трафик, selfsteal **:443** |
| **NL** | Production VPN | Alt transport **:9443**, warm spare / leastLoad |
| **AMS** | Панель + sub-page | **`remnanode` decom** — не в расчёте prod-ёмкости |

Клиентский **leastLoad** в Happ распределяет сессии между outbounds в подписке; обе prod-ноды должны быть в **`injectHosts`** шаблона.

## Soft cap (пользователи на prod-ноду)

Ориентир совпадает с **`balancer.sh`** и **`ops/capacity_snapshot.py`**:

| Параметр | Значение |
|----------|----------|
| **`USERS_PER_NODE`** | **50** ACTIVE users на одну prod-ноду (эвристика, не жёсткий лимит панели) |
| **Ёмкость кластера** | `nodes_active_not_disabled × 50` (только prod-ноды в учёте) |
| **WARN** | **≥ 80%** ёмкости → планировать **(N+1)**-ю ноду |
| **ALERT** | **≥ 95%** → закупка/деплой срочно |
| **CRITICAL** | **≥ 100%** → деплой **до** роста базы |

Мониторинг: cron **`balancer.sh`** (TG админу), вручную **`python ops/capacity_snapshot.py`**.

Пороги **users в БД** (не сессии) — отдельно в **`COMMERCIAL-BACKLOG.md` §10.1**: **2000** / **8000**.

## Когда добавлять третью prod-ноду

Выполнять **все** проверки, затем **`deploy-node.sh`** (шаг **L** — injectHosts):

1. **`load_pct_vs_soft_capacity ≥ 80%`** устойчиво **3+ дня** (`capacity_snapshot` / daily summary).
2. Или **CPU load > 1.5** на LV/NL **и** load **≥ 80%** (см. алерты balancer).
3. Или продуктовое решение: отдельный регион (не только LV+NL) для mux (**`TRANSPORT-MUX-MATRIX`**).

**Не** добавлять ноду, если NL **0%** сессий при обеих нодах в шаблоне — сначала **`P6-SCALE-NL-VERIFY`** (раздел ниже).

После деплоя:

1. Host в панели + **`injectHosts`** (автоматически в **`deploy-node.sh`**).
2. **`python ops/transport_mux_audit.py`** — у пользователей есть outbound на новый профиль.
3. При инциденте routing — **`subscription_config_notify.after_template_patch`** (авто-напоминание обновить подписку).

## P6-SCALE-NL-VERIFY (осознанный дисбаланс LV/NL)

> Все активные пользователи на **LV**, **NL** онлайн — политика или баг?

**Норма:**

- NL как **warm spare** / второй транспорт; доля сессий на NL может быть **низкой**, но NL в **`injectHosts`** и **connected**.
- **`transport_mux_audit`**: alt outbounds присутствуют у большинства ACTIVE users.

**Триггер аудита** (7+ дней):

- **0%** сессий/трафика NL при обеих нодах в шаблоне и **connected** → проверить squads, Happ profile, **`leastLoad`**, порядок outbounds.
- См. **`docs/TRANSPORT-MUX-MATRIX.md`**.

## Связанные файлы

- **`balancer.sh`** — алерты 80/95/100% capacity
- **`ops/capacity_snapshot.py`** — снимок + soft-cap NOTICE
- **`deploy-node.sh`** — новая нода + template injectHosts
- **`docs/COMMERCIAL-BACKLOG.md` §10.1–10.2**
