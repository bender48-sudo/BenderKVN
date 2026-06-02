# RU bypass (direct routing for RU apps)

Приложение: список доменов для **`outboundTag: direct`** в шаблоне подписки
Remnawave (`templateJson.routing`). Каноничный код и список доменов
живут в **`ops/ru_bypass_routing.py`** (`EXTRA_DIRECT_DOMAINS`).

## Режимы

| Режим | Признак | Действие |
|-------|---------|----------|
| **normal** | `geoip:ru → direct` + `geosite:category-ru` + regexp `.ru` | Целевой прод |
| **emergency_tun_all_proxy** | `geoip:ru` direct **удалён** | `patch_routing_tun_all_proxy.py` — только инцидент |
| **partial** | direct rules неполные | `ru_bypass_routing.py --apply` |

Проверка: `python ops/verify_ru_bypass_status.py`

## Покрытые сервисы (EXTRA_DIRECT_DOMAINS)

Помимо regexp `.*\.ru$` и `geosite:category-ru`:

| Категория | Домены |
|-----------|--------|
| **VK / MAX** | max.ru, oneme.ru, vk.com, vk.me, vkuservideo.*, userapi.com, player.vk.com |
| **Яндекс CDN** | yandex.com/net, yastatic.net, ya.com |
| **Мобильные** | mts.com, megafon.com, beeline.com, tele2.com |
| **Банки** | sber*, tinkoff, tbank, vtb, alfabank, raiffeisen, tochka, modulbank, open.ru, homecredit, domrf, psb, rosbank, gazprombank, sovcombank |
| **Маркетплейсы** | avito.com, ozon.com, wildberries.eu, sbermegamarket |
| **Гос / почта** | gosuslugi.com, pochta.com |
| **Стриминг** | ivi.ru, more.tv, start.ru, premier.one, rutube.ru, kinopoisk.ru |
| **Mail CDN** | mail.ru, imgsmail.ru, attachmail.ru, mycdn.me |
| **Игры** | warface.com |

Полный список — **`EXTRA_DIRECT_DOMAINS`** в `ops/ru_bypass_routing.py`.

## DNS (отдельно от routing)

**Не** использовать routing `port=53 → direct` (gen=30 regression).

Split DNS: **`ops/patch_dns_split_config.py`** (VPN-AUD-230) — DoH для intl, localhost для RU.

## Как добавить домен (< 5 мин)

1. Внести FQDN в **`EXTRA_DIRECT_DOMAINS`** в `ops/ru_bypass_routing.py`.
2. Dry-run: `python ops/ru_bypass_routing.py`
3. Apply: `python ops/ru_bypass_routing.py --apply`
4. Verify:
   ```bash
   python ops/probe_ru_bypass.py
   python ops/probe_routing.py
   python ops/verify_ru_bypass_status.py
   ```

## Откат

Восстановить JSON из `.secrets/snapshots/template-before-ru-bypass-*.json`.

## Регресс Xray («no effective fields»)

`python ops/ru_bypass_routing.py --strip-degenerate-only --apply`
