# RU bypass (direct routing for RU apps)

Приложение: список доменов для **`outboundTag: direct`** в шаблоне подписки
Remnawave (`templateJson.remnawave.routing`). Каноничный код и список доменов
живут в **`ops/ru_bypass_routing.py`** (`EXTRA_DIRECT_DOMAINS`).

## Как добавить домен (< 5 мин)

1. Внести полное имя (FQDN) в **`EXTRA_DIRECT_DOMAINS`** в `ops/ru_bypass_routing.py` (коммит при необходимости).
2. Снять состояние: `python ops/ru_bypass_routing.py` (dry-run — план PATCH).
3. Применить: `python ops/ru_bypass_routing.py --apply` (snapshot в `.secrets/snapshots/` создаётся автоматически).
4. Проверить: `python ops/probe_routing.py` — блок **direct.domain** включает новый домен, **degenerate rules = 0**.

## Откат

Восстановить последний JSON из `.secrets/snapshots/template-before-ru-bypass-*.json`
или использовать снапшот до проблемного PATCH; затем PATCH полного объекта шаблон
как описано в `docs/SECRETS.md` / процедуры панели.

## Регресс Xray («no effective fields»)

Не оставлять в `routing.rules` правило с пустым `domain: []` и `outboundTag`/`balancerTag`.
Скрипт `ru_bypass_routing` удаляет вырожденные правила; аварийно:
`python ops/ru_bypass_routing.py --strip-degenerate-only --apply`.
