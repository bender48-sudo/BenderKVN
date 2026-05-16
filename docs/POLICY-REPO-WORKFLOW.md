# Политика: как вести этот репозиторий (операторы и ассистенты)

Краткая **каноническая** памятка поверх **`docs/DEPLOY.md`**, **`docs/KNOWLEDGE-BASE.md`**, **`docs/SECRETS.md`**.

## 1. Source of Truth

| Что | SoT |
|-----|-----|
| Управляющие скрипты LV/AMS/NL | Файлы в **репо** → деплой на прод по **`docs/DEPLOY.md` §3** |
| Compose и prod-**.env** | **`compose/**/*.tmpl`** в репо + локальный **`.secrets/vault.env`** (не в Git) |
| Публичная логика продукта / поддержка пользователей | **`docs/FAQ.md`**, **`docs/ONBOARDING.md`**, runbook инцидентов |

Не править прод «молча» без обратной записи в репо или явной журнальной строки (**`docs/COMMERCIAL-BACKLOG.md` §12**).

## 2. Секреты

- Никогда коммитить **`.env`**, **`.secrets/vault.env`**, **`prod-compose`**, сырой JWT/`BOT_TOKEN` в любых версионируемых файлах.
- В шаблонах только **`${PLACEHOLDER}`**; канон сборки **`python ops/extract_vault.py`** из **`.secrets/prod-compose/`** после актуальных SCP-снимков.
- **Два machine JWT** для панели: в vault ключи **`REMNA_API_TOKEN_AMS`** и **`REMNA_API_TOKEN_LV`** (`docs/SECRETS.md`). На проде переменная в файлах по-прежнему **`REMNA_API_TOKEN=`**.

## 3. Обновление шаблонов и drift

После ручных правок на проде:

1. Снять копии в **`.secrets/prod-compose/`**  
2. Регенерировать шаблоны: **`python ops/sanitize_compose_templates.py`**  
   — скрипт **удаляет и заново собирает весь **`compose/`** только из **`MAP`** внутри себя**. Любой путь/service вне **`MAP` исчезнет** → перед запуском **commit текущего `compose/`** или точечное правление шаблонов вручную.  
3. **`python ops/extract_vault.py`** → обновить **`vault.env`**  
4. **`python ops/drift-check.py`** → должен быть **exit 0**

## 4. Изменение кода

- **Очередь:** одна строка **`NEXT`** из **`docs/BACKLOG-QUEUE.md`** за сессию агента → коммит → стоп (**`docs/POLICY-SEQUENTIAL-WORK.md`**).
- По возможности узкий diff; один коммит = одна **Q** / одна понятная цель (**зачем** в сообщении коммита).
- Shell: после правок **`bash -n файл.sh`** где применимо.  
- Python: **`python -m py_compile`** на изменённые модули.
- Если изменение **ощутимо**, после проверки — **commit + push в `main`** (согласовано с **`.cursor/rules/commit-after-verify.mdc`**).

## 5. Приоритеты продукта

См. **`docs/POLICY-BACKLOG-ORDER.md`**, **`docs/COMMERCIAL-BACKLOG.md` §2.1**: стабильность и эксплуатация **до** точечных UX-улучшений, если это не блокер безопасности.

## 6. Ссылки для агента Cursor

Табличный указатель операционной памяти — **`docs/KNOWLEDGE-BASE.md`**.
