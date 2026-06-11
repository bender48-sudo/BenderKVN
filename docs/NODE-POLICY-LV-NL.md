# Политика нод Latvia + Netherlands (P6-SCALE-02)

> **Live vs policy (2026-06-11):** **`VPN-ARCH-001-NL-AUTOHOST-PROOF-001`** + **`VPN-ARCH-001-NL-QUALITY-PROOF-001`**: штатный Auto = **Candidate D relay-only×6**; **NL не active delivery** (`usersOnline=0`, subs NL=0, inject NL=0). NL **pre-qualified** для **A2/A4 controlled smoke** после **MONITOR-FLAP-001** soak (RU relay→NL TCP PASS с LV; infra OK). **`nl_node_health_probe` FAIL** до inclusion — ожидаемо (ждёт inject NL≥4), не отказ по качеству. Следующий шаг: **controlled smoke**, не blind PATCH и не decom. **VPN-AUD-220** / **Q167–Q171** — история / failover. **VPN-ARCH-001**: preferred **A2/A4** after soak; interim **B** OK; **C/D** not now unless smoke fails.

## Роли нод (целевая политика)

| Узел | Роль | Примечание |
|------|------|------------|
| **LV** | Production VPN | Основной трафик, selfsteal **:443** |
| **NL** | Production VPN (целевое) | Alt transport; warm spare / leastLoad — **сейчас failover-only, не в Auto sub** |
| **AMS** | Панель + sub-page | **`remnanode` decom** — не в расчёте prod-ёмкости |

**Live (2026-06-11):** NL **connected**, billable, **не** в live `injectHosts`; **не** active delivery capacity. **QUALITY-PROOF-001:** RU reachability + infra OK → **A2/A4 smoke** after soak, not decom.

Клиентский **leastLoad** в Happ распределяет сессии между outbounds в подписке; **при целевой политике** обе prod-ноды должны быть в **`injectHosts`** шаблона. **Сейчас** в inject только relay×6.

## Soft cap (пользователи на prod-ноду)

Ориентир совпадает с **`balancer.sh`** и **`ops/capacity_snapshot.py`**.

**Учёт ёмкости:** считать только ноды в **generated profiles/routing** после **controlled smoke** и post-inclusion audit. **NL сейчас = 0** в `delivery_path_nodes`. **Не считать:** paid/connected NL без outbounds в подписке; backup edge; failover-only; pre-smoke pre-qualification (**QUALITY-PROOF-001**).

| Параметр | Значение |
|----------|----------|
| **`USERS_PER_NODE`** | **50** ACTIVE users на одну prod-ноду (эвристика, не жёсткий лимит панели) |
| **Ёмкость кластера** | `delivery_path_nodes × 50` — только ноды **в generated subs/routing** (не backup/failover-only) |
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

**Не** добавлять ноду, если NL **0%** сессий при обеих нодах **в шаблоне** — сначала **`P6-SCALE-NL-VERIFY`**. **Сейчас (2026-06-11):** NL **0%** потому что **не в injectHosts** — сначала **VPN-ARCH-001** owner decision, не «баг leastLoad».

После деплоя:

1. Host в панели + **`injectHosts`** (автоматически в **`deploy-node.sh`**).
2. **`python ops/transport_mux_audit.py`** — у пользователей есть outbound на новый профиль.
3. При инциденте routing — **`subscription_config_notify.after_template_patch`** (авто-напоминание обновить подписку).

## P6-SCALE-NL-VERIFY (осознанный дисбаланс LV/NL)

> Все активные пользователи на **LV**, **NL** онлайн — политика или баг?

**Норма (целевая политика LV+NL в inject):**

- NL как **warm spare** / второй транспорт; доля сессий на NL может быть **низкой**, но NL в **`injectHosts`** и **connected**.
- **`transport_mux_audit`**: alt outbounds присутствуют у большинства ACTIVE users.

**Live (2026-06-11):** NL **не в injectHosts** → **0 NL outbounds** у всех ACTIVE users — **ожидаемо**, не триггер P6-SCALE-NL-VERIFY. Триггер смены — **VPN-ARCH-001** re-include или decom.

**Триггер аудита** (7+ дней) — только **после** NL снова в шаблоне:

- **0%** сессий/трафика NL при обеих нодах в шаблоне и **connected** → проверить squads, Happ profile, **`leastLoad`**, порядок outbounds.
- См. **`docs/TRANSPORT-MUX-MATRIX.md`**.

## LV недоступен (billing / VPS)

Авто NL-only в шаблоне подписки (gate до/после): **`docs/RUNBOOK-LV-DOWN-NL-FAILOVER.md`**,  
`python ops/lv_node_down_nl_failover.py --auto --gate --apply`.

**Не путать:** этот runbook — **emergency/manual capacity (classification C)**, не штатная ёмкость для роста.

## Связанные файлы

- **`balancer.sh`** — алерты 80/95/100% capacity
- **`ops/capacity_snapshot.py`** — снимок + soft-cap NOTICE
- **`deploy-node.sh`** — новая нода + template injectHosts
- **`docs/COMMERCIAL-BACKLOG.md` §10.1–10.2**
