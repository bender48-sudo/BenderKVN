# BenderKVN

Репозиторий инженерной и продуктовой документации VPN-проекта: **compose-шаблоны**, **`ops/`**‑скрипты, код **`bot_src/`**, runbook'и и **коммерческий бэклог**.

## С чего начать

| Раздел | Файл |
|--------|------|
| **Бэклог и журнал решений на проде** | [`docs/COMMERCIAL-BACKLOG.md`](docs/COMMERCIAL-BACKLOG.md) |
| **Правила работы, уроки, типовые ошибки** | [`docs/KNOWLEDGE-BASE.md`](docs/KNOWLEDGE-BASE.md) |
| Деплой и drift | [`docs/DEPLOY.md`](docs/DEPLOY.md) |
| Где живут секреты (paths, не значения) | [`docs/SECRETS.md`](docs/SECRETS.md) |
| Смена `REMNA_API_TOKEN` без 502 | [`docs/RUNBOOK-REMNA-API-TOKEN.md`](docs/RUNBOOK-REMNA-API-TOKEN.md) |
| Git vs прод | [`docs/VCS-WHERE-IS-GIT.md`](docs/VCS-WHERE-IS-GIT.md) |

Секреты и `.env` прод-серверов **не** версионируются (см. [`.gitignore`](.gitignore)).
