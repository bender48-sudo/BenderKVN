# Рекомендация: порт публичного edge вместо :2053

**Задача:** **P2-RED-EDGE-PORT-01** (**Q051**).  
**Контекст:** **2053** — дефолт панели **3X-UI** ([Habr](https://habr.com/ru/articles/822597/), [HSTQ](https://cp.hstq.net/knowledgebase/9141/)); сканеры и ТСПУ ассоциируют его с «xray/sub», не с обычным сайтом.

---

## Два разных порта (не путать)

| Слой | Сейчас | Что меняем в Q051 | Источники |
|------|--------|-------------------|-----------|
| **Edge HTTPS** — панель, `/api/sub/*`, portal | **:2053** на **k9x2m1** / **p4n7q** | **Да** — цель Q051 | 3X-UI default, бета ТСПУ |
| **VPN inbound** — VLESS/Reality на LV/NL | **:443**, alt **:9443** / **:8443** | **Q056** отдельно | [net4people/bbs#546](https://github.com/net4people/bbs/issues/546), Habr [990236](https://habr.com/en/articles/990236/) |

Исследования про «не использовать **443** на VPN» относятся к **туннелю**, не к URL подписки в браузере.

---

## Куда уходить с :2053 (edge)

### Не использовать

| Порт | Почему |
|------|--------|
| **2053**, **2054** | Сигнатура 3X-UI / remna-панелей; активные сканы (бета) |
| **3000**, **3010**, **8080** | Типичные dev/API; палево при скане |
| **22**, **80** (голый) | Шум сканеров; для edge нужен **HTTPS** |

### Рекомендация (зафиксировать в Q051)

| Приоритет | Порт | Плюсы | Минусы |
|-----------|------|-------|--------|
| **1 (основной)** | **8443** | Похож на «альтернативный HTTPS»; привычен пользователям; LE/SNI на Caddy; **не** дефолт 3X-UI | На части VPS в firewall иногда закрыт — открыть явно |
| **2 (запасной)** | **4433** | Редко в шаблонах xray; меньше ассоциации с панелями | Менее привычен в URL |
| **3 (если хостер режет 8443)** | **10443** | Высокий порт, реже в массовых шаблонах | Длиннее в ссылках; часть корп. Wi‑Fi режет нестандартные порты |

**Не брать как единственный edge:** случайные **47xxx** — хорошо для **VPN inbound** (меньше DPI на wire, [Habr 990236](https://habr.com/en/articles/990236/)), но **плохо для subscription URL** и Mini App (фильтры, копирование ссылок).

### Согласованность с нашим стеком

- На **нодах** уже есть **LV:8443** (alt xray) — это **другой хост/IP**, не `k9x2m1:8443`. Коллизии нет.
- **NL:9443** — selfsteal/Caddy на AMS; edge **8443** на LV Caddy для **conntest.xyz** — разные роли.

**Итог для репо:** в **`site_urls.py`**, Caddy, BotFather — канонический **`https://k9x2m1.conntest.xyz:8443/`** (и **p4n7q…:8443** для sub origin). Grace **2053→8443** 7–14 дней.

---

## VPN inbound (не Q051, но из тех же источников)

| Наблюдение | Действие |
|------------|----------|
| [bbs#546](https://github.com/net4people/bbs/issues/546): на части ISP РФ ломается **VLESS+Reality на :443** | Держать **alt** (**9443/8443**) в подписке (**MUX** ✅) |
| Тот же тред: помогает смена на **порт ≠ 443** | **Q056** — playbook смены inbound |
| Habr / обсуждения 2025–2026: высокие порты для туннеля | Рассмотреть **второй alt** на **47xxx** для power users (не заменять 8443 edge) |
| Референс-конфиги (бета): **:80** + **SNI www.yandex.ru** | Профиль **wl-direct** — **P1-PRO-SUB-TIER-01** |

---

## Проверка после смены

1. `curl -fsSI https://k9x2m1.conntest.xyz:8443/portal/` → **200**
2. `curl -fsSI https://p4n7q.conntest.xyz:8443/api/sub/<shortId>` → **200**
3. С внешней RU-сети: нет всплеска сканов на **2053** (логи Caddy / fail2ban)
4. Smoke **`SUB_EDGE_PORT_OK`**

---

## Ссылки

- [3X-UI issue #860 — sub и web на одном порту](https://github.com/MHSanaei/3x-ui/issues/860)
- [Remnawave — Caddy reverse proxy](https://docs.rw/docs/install/reverse-proxies/caddy)
- [XTLS/Xray-core #5332 — TCP+Reality blocked](https://github.com/XTLS/Xray-core/issues/5332)
- [Reality SNI whitelist #2283](https://github.com/XTLS/Xray-core/issues/2283)
- **`docs/TSPU-OBSERVATIONS.md`**, **`docs/PRODUCT-TIER-PROFILES.md`**
