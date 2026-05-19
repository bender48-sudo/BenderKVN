# ТСПУ red-team audit — раунд 2 (после фазы 6)

**ID:** **P2-RED-TSPU-AUDIT-03** (Q098).  
**Дата:** 2026-05-19  
**База:** прод после **Q086–097** (Caddy sunset **2053**, p4n7q portal, AMS бот/admin, status trim).  
**Роль:** внешний противник уровня ТСПУ/DPI + сверка с **Q085**.

**Прогоны:** smokes с рабочей станции + SSH `bvpn-lv` (не RU LTE).

---

## Executive summary

| Метрика | Q085 (до фазы 6) | Сейчас (раунд 2) |
|---------|------------------|------------------|
| **Зрелость к ТСПУ** | 6,5 / 10 | **7,5 / 10** |
| **GTM edge** | условно | **да** (при LTE ok) |
| **Рост 1k** | после discovery | **условно** (RU relay + alt TLD) |

**Закрыто с Q085:** grace **2053→301→8443** на LV, user-facing **:8443**, live **p4n7q** portal/start/status, alt в FAQ, MUX 100%, `log_skip`, public status без ops-leak.

**Остаток P1:** RU egress probe с relay (**72.56.0.145:3344** timeout с LV) — код есть, **инфра не зелёная**.  
**Остаток P2:** один TLD, selfsteal **:9443**, полевой LTE — владелец.

**Регресс:** нет отката Q051–061 / Q079–097.

---

## Live checks (2026-05-19)

| Check | Результат |
|-------|-----------|
| `TSPU_REDTEAM_OK` | ✅ |
| `SUB_EDGE_PORT_OK` | ✅ k9x2m1 + p4n7q **:8443** |
| `DISCOVERY_PORT_OK` | ✅ нет `:2053` в bot/FAQ |
| `:2053/status` | **301** → `:8443/status` |
| `p4n7q:8443/portal/` | **200** |
| `/api/ops/status.json` | **`status-public/v1`** |
| LV Caddy | **3×** redir 2053, **3×** portal blocks, **:2054** только комментарий |
| RU relay SSH | ❌ timeout LV→`bvpncheck@72.56.0.145:3344` |

---

## Находки (P0–P3)

| P | ID | Вектор | Статус | Действие |
|---|-----|--------|--------|----------|
| — | T-AUD-01..02 | 2053 grace + UX | **CLOSED** | фаза 6 |
| — | T-AUD-03 | Alt apex live | **CLOSED** | p4n7q **:8443** portal |
| **P2** | T-AUD-04 | RU probe | **OPEN** | Q099 infra: relay SSH/firewall |
| **P2** | T-AUD-05 | Один TLD | **OPEN** | P4-DNS / владелец |
| **P3** | T-AUD-06 | Selfsteal :9443 | **KEEP** | Q057 |
| **P3** | T-AUD-07 | `balancer.env` PANEL_URL :2053 | **FIXED** | sed на LV → **8443** |
| **P3** | T-AUD-08 | Docs drift KB/ONBOARDING :2053 | **OPEN** | Q100 docs sweep |

---

## Очередь (предложение)

| Q | ID | Смысл |
|---|-----|--------|
| **098** | **P2-RED-TSPU-AUDIT-03** | Этот отчёт |
| **099** | **P2-OPS-RU-RELAY-01** | SSH LV→RU relay для probe/cron |
| **100** | **P2-DOC-PORT-8443-01** | KB/ONBOARDING без :2053 |
| **101** | **P2-RED-CODERABBIT-02** | CodeRabbit раунд 2 (промпт ниже) |

---

## Verify

`python ops/smoke_tspu_redteam.py` → **TSPU_REDTEAM_OK**  
`python ops/smoke_discovery_port.py` → **DISCOVERY_PORT_OK**
