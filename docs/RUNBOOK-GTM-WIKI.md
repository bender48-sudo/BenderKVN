# Runbook: GTM wiki (GTM-WIKI-01)

## 1. Создать живую страницу (владелец, ~30 мин)

1. Открыть **`docs/templates/GTM-WIKI-PAGE.md`** в репозитории.
2. Скопировать содержимое в **Notion** / Google Doc / Outline (приватное пространство).
3. Заполнить таблицы §1 (каналы, бюджет, CAC) и §2 (политика trial / модерация).
4. Вставить **URL** страницы в **`docs/GTM-WIKI.md`** → таблица **Live wiki**.
5. В **`docs/COMMERCIAL-BACKLOG.md` §1`** строка «GTM wiki» — заменить placeholder на тот же URL.
6. Отметить чекбоксы **Owner gate** в **`docs/GTM-WIKI.md`**.

Секреты и персональные контакты **не** переносить в git.

## 2. Еженедельный ритуал (продукт + инженерия)

Каждый понедельник (или после релиза):

```bash
python ops/capacity_snapshot.py
# при росте sub: python ops/subscription_load_probe.py --json
```

Сверить с планом регистраций в wiki §1. При триггерах §10.1 бэклога — задача в инженерную очередь (**`docs/BACKLOG-QUEUE.md`**), не увеличивать рекламу.

## 3. Связанные документы

- **`docs/GTM-GROWTH-OUTLINE.md`**
- **`docs/RUNBOOK-COMMERCE-GO-LIVE.md`**
- **`docs/RUNBOOK-INCIDENT.md`**
- **`docs/COMMERCIAL-BACKLOG.md` §10.1**
