# In-app support tickets + TG bridge — plan (SUPPORT-TICKET-BRIDGE-001, P4)

**Status:** PLAN ONLY. No schema, no code, no prod. Branch/staging. Gated behind
`SUPPORT_TICKETS_LIVE` (default off) until ready. Does NOT touch billing/Remna. Basis:
`MINI-APP-INTERACTION-SPEC.md` §SUPPORT + `design/mockups/support_mockup.html`.

Order: **schema + bridge + status engine (this doc) → STOP → code → front.**

---

## 0. What exists today (reuse) vs new

**Exists (`bot_src/support_handler.py`):** ONE forum topic **per user** (`users.support_topic_id`),
`copy_message` relay both ways, `support_last_user_at/staff_at`, `support_auth.is_authorized_support_staff`,
rate limits, `SUPPORT_GROUP_ID`. It is a **bot-DM** bridge — one thread per user, no ticket model,
no statuses, no in-app threads.

**New (this plan):** an in-app **ticket** model — multiple tickets per user, each with subject +
status + its own TG forum topic (`#тикет_NNNN`). The legacy per-user DM bridge stays untouched for
users who just DM the bot; in-app tickets are a parallel, ticket-scoped bridge.

---

## 1. DB schema (migration v9, additive — CREATE only)

```sql
CREATE TABLE IF NOT EXISTS tickets (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,  -- ticket #NNNN (display zero-pad)
    user_id             INTEGER NOT NULL,                   -- owner telegram_id
    subject             TEXT    NOT NULL,                   -- connection|payment|devices|other
                                                            --  |partner_apply|partner_withdraw
    status              TEXT    NOT NULL DEFAULT 'waiting',  -- waiting | answered | closed
    tg_topic_id         INTEGER,                            -- forum topic for this ticket (null→not bridged)
    contact_email       TEXT,                               -- email for the first-reply duplicate
    last_message_at     TEXT,                               -- sort + 3-day auto-close
    last_sender         TEXT,                               -- user | staff | system  (drives status)
    first_staff_reply_at TEXT,                              -- dedupe email+TG duplicate (only first)
    unread_user         INTEGER NOT NULL DEFAULT 0,         -- unread staff msgs → bell badge
    created_at_utc      TEXT    NOT NULL,
    closed_at_utc       TEXT
);
CREATE TABLE IF NOT EXISTS ticket_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id     INTEGER NOT NULL,
    sender        TEXT    NOT NULL,        -- user | staff | system
    body          TEXT,
    channel       TEXT,                    -- app | tg | email  (origin)
    tg_message_id INTEGER,                 -- bridged TG msg id (dedupe / idempotency)
    created_at_utc TEXT   NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_user   ON tickets(user_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_topic  ON tickets(tg_topic_id) WHERE tg_topic_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tickets_openset ON tickets(status, last_message_at);
CREATE INDEX IF NOT EXISTS idx_ticket_msgs    ON ticket_messages(ticket_id, id);
```

- **Auto-ack text** (admin-editable) → reuse existing `bot_settings` (key `support_auto_ack_text`).
  No new settings table.
- `unread_user` is the source for the home **bell** (currently hardcoded 0) → `GET /portal-unread`.

---

## 2. TG bridge — per-ticket forum topic

| Direction | Flow |
|---|---|
| **create** (app) | `POST /portal-ticket` → insert ticket (status `waiting`) → create forum topic `#{id} · {subject} · {name}\|{user_id}` → save `tg_topic_id` → post header (subject/email/user) + first user message → append **system auto-ack** message (`support_auto_ack_text`) shown in-app + sent to user. |
| **app → TG** | `POST /portal-ticket/{id}/message` → insert `ticket_messages(sender=user, channel=app)` → bot posts text into `tg_topic_id` → status → `waiting`; if was `closed` → **reopen**. |
| **TG → app** | extend existing `admin_reply_in_topic`: if the topic maps to a **ticket** (`tickets.tg_topic_id`), insert `ticket_messages(sender=staff, channel=tg)`, status → `answered`, `unread_user += 1`. (Legacy per-user topics keep current behavior.) |
| **first staff reply** | on the FIRST staff message (`first_staff_reply_at` null) → also **duplicate to email + TG DM** to the user (so they notice without the app open), set `first_staff_reply_at`. Later replies → in-app + bell only. |
| **close** | staff `/close` command in the ticket topic (auth via `support_auth`) → status `closed`, `closed_at_utc`. |

Reverse-routing key = `tickets.tg_topic_id` (per-ticket), distinct from legacy `users.support_topic_id`.

---

## 3. Status engine (spec §166–167)

- **States:** `waiting` (Ждёт ответа · жёлтый) · `answered` (Ответ есть · зелёный) · `closed` (Закрыто · серый).
- **Driver = who wrote last** (`last_sender`): user → `waiting`; staff → `answered`. (`system` auto-ack
  does **not** flip to answered — stays `waiting`.)
- **Close:** manual (staff `/close` in TG) **or** 3 days of silence (`last_message_at` > 3d, status≠closed)
  via the existing scheduler tick → `closed`.
- **Reopen:** a new user message on a `closed` ticket → `waiting`.
- Status is **stored** (not purely derived) so manual close survives; updated on every message + by the
  auto-close sweep.

---

## 4. API surface (build after this plan; identity = telegram_id, validate initData in prod)

| Endpoint | Returns / does |
|---|---|
| `POST /portal-tickets` | list: `[{id, subject, status, last_message, last_message_at, unread}]` |
| `POST /portal-ticket` | create `{subject, text, email}` → `{ticket_id, status}` (+topic+auto-ack) |
| `POST /portal-ticket-get` `{id}` | `{ticket, messages[]}`; marks read → `unread_user=0` |
| `POST /portal-ticket-message` `{id, text}` | append + bridge → status `waiting` |
| `POST /portal-unread` | `{count}` = Σ `unread_user` → home bell |

(POST-only to match the existing proxy/`telegram-setup` shape; paths added to the `:8871` allowlist
at deploy, like balance/referral/home.)

---

## 5. Unblocks / dependencies

- **Home bell** unread badge (now 0) → `GET /portal-unread`.
- **P3 partner** «Стать партнёром» / «Запросить вывод» → create tickets with subjects
  `partner_apply` / `partner_withdraw` (referral screen's gated buttons light up once this ships).
- **Wizard step-4** «Не работает» → create ticket subject `connection` (its toast becomes real).
- **Email transport:** the first-reply email duplicate needs an email sender. **Open: confirm an
  SMTP/provider exists**; if not, degrade to TG-DM + in-app first, add email later.

---

## 6. Migration / flags / scope

- Migration **v9**: the two tables + indexes (additive, reversible: drop tables). `bot_settings`
  reused for auto-ack.
- Gate `SUPPORT_TICKETS_LIVE` (default off). `SUPPORT_GROUP_ID`, `support_auth`, rate limits reused.
- No billing/Remna. Legacy per-user DM bridge untouched.

---

## Decisions needed before code (STOP)

- **Q1.** Per-ticket forum topics (recommended — matches `#тикет_NNNN`, clean status) vs one per-user
  topic with tagged messages?
- **Q2.** **Email transport** — is there an SMTP/email provider wired for the first-reply duplicate?
  If not: ship TG-DM + in-app first, email later — OK?
- **Q3.** Ticket number = raw `id` zero-padded (`#1042`) — OK, or a separate display sequence?
- **Q4.** Staff close via bot `/close` command in the topic — OK?
- **Q5.** Auto-close window = **3 days** silence (per spec) — confirm; reuse existing scheduler tick.
- **Q6.** Partner subjects (`partner_apply`, `partner_withdraw`) included now so P3 partner unblocks — OK?
```
