#!/usr/bin/env python3
"""P5-COM-01: render user-facing incident status HTML from status-mirror JSON."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

_STATUS_RU = {
    "ok": ("operational", "Все системы работают"),
    "degraded": ("degraded", "Частичные ограничения"),
}
_INCIDENT_STATUS_RU = {
    "investigating": "Разбираемся",
    "identified": "Причина найдена",
    "monitoring": "Наблюдаем",
    "resolved": "Устранено",
}


def _load_incidents(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    items = doc.get("incidents") if isinstance(doc, dict) else []
    if not isinstance(items, list):
        return []
    active = [
        i
        for i in items
        if isinstance(i, dict) and i.get("status") != "resolved"
    ]
    return active


def _vpn_summary(nodes: list[dict[str, Any]]) -> tuple[str, str]:
    if not nodes:
        return "unknown", "Нет данных о нодах"
    up = sum(
        1
        for n in nodes
        if n.get("connected") or n.get("expected_down")
    )
    total = len(nodes)
    if up >= total:
        return "ok", f"Серверы VPN: {up}/{total} в норме"
    return "degraded", f"Серверы VPN: {up}/{total} доступны"


def _sub_summary(status: dict[str, Any]) -> tuple[str, str]:
    sub = status.get("subscription") or {}
    code = int(sub.get("primary_http") or 0)
    if code in (200, 304):
        return "ok", "Выдача подписки: работает"
    if code == 0:
        return "unknown", "Выдача подписки: нет данных"
    return "degraded", f"Выдача подписки: HTTP {code}"


def render_public_html(
    status: dict[str, Any],
    incidents_path: Path | None = None,
    *,
    json_url: str = "",
) -> str:
    overall = status.get("overall", "degraded")
    css_class, headline = _STATUS_RU.get(overall, _STATUS_RU["degraded"])
    updated = html.escape(str(status.get("updated_at", "")))
    message = html.escape(str(status.get("message", "")))

    incidents = _load_incidents(incidents_path)
    if incidents:
        css_class = "degraded"
        headline = "Есть активные инциденты"

    components: list[tuple[str, str, str]] = []
    comp_doc = status.get("components")
    if isinstance(comp_doc, dict) and comp_doc:
        for key in ("vpn", "subscription"):
            block = comp_doc.get(key) or {}
            if isinstance(block, dict) and block.get("summary"):
                components.append(
                    (
                        key,
                        str(block.get("state", "unknown")),
                        str(block["summary"]),
                    )
                )
    else:
        vpn_state, vpn_line = _vpn_summary(status.get("nodes") or [])
        components.append(("vpn", vpn_state, vpn_line))
        sub_state, sub_line = _sub_summary(status)
        components.append(("sub", sub_state, sub_line))

    comp_html = []
    for _key, state, line in components:
        comp_html.append(
            f'<li class="comp comp-{html.escape(state)}">{html.escape(line)}</li>'
        )

    inc_html: list[str] = []
    for inc in incidents:
        title = html.escape(str(inc.get("title", "Инцидент")))
        body = html.escape(str(inc.get("message", "")))
        st = _INCIDENT_STATUS_RU.get(
            str(inc.get("status", "investigating")), "Разбираемся"
        )
        inc_html.append(
            f'<article class="incident"><h2>{title}</h2>'
            f'<p class="inc-status">{html.escape(st)}</p>'
            f'<p>{body}</p></article>'
        )
    incidents_block = (
        "\n".join(inc_html)
        if inc_html
        else '<p class="muted">Активных инцидентов нет.</p>'
    )

    json_link = ""
    if json_url:
        json_link = (
            f'<p class="muted"><a href="{html.escape(json_url)}">'
            "Технический JSON (для мониторинга)</a></p>"
        )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="120">
  <title>BenderVPN — статус сервиса</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --ok: #3dd68c;
      --warn: #f5a524;
      --bad: #f31260;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 1.25rem;
      line-height: 1.5;
    }}
    main {{ max-width: 42rem; margin: 0 auto; }}
    h1 {{ font-size: 1.35rem; margin: 0 0 0.5rem; }}
    .banner {{
      border-radius: 12px;
      padding: 1rem 1.25rem;
      margin: 1rem 0;
      background: var(--card);
      border-left: 4px solid var(--muted);
    }}
    .operational {{ border-left-color: var(--ok); }}
    .degraded {{ border-left-color: var(--warn); }}
    .headline {{ font-size: 1.1rem; font-weight: 600; }}
    ul {{ list-style: none; padding: 0; margin: 0.75rem 0; }}
    .comp {{ padding: 0.35rem 0; }}
    .comp-ok::before {{ content: "✓ "; color: var(--ok); }}
    .comp-degraded::before {{ content: "! "; color: var(--warn); }}
    .comp-unknown::before {{ content: "? "; color: var(--muted); }}
    .incident {{
      background: var(--card);
      border-radius: 10px;
      padding: 1rem;
      margin: 0.75rem 0;
    }}
    .incident h2 {{ font-size: 1rem; margin: 0 0 0.35rem; }}
    .inc-status {{ color: var(--warn); margin: 0 0 0.5rem; font-size: 0.9rem; }}
    .muted {{ color: var(--muted); font-size: 0.9rem; }}
    a {{ color: #6eb5ff; }}
  </style>
</head>
<body>
  <main>
    <h1>BenderVPN</h1>
    <p class="muted">Публичный статус сервиса</p>
    <div class="banner {css_class}">
      <p class="headline">{headline}</p>
      <p>{message}</p>
      <p class="muted">Обновлено (UTC): {updated}</p>
    </div>
    <section>
      <h2 class="muted" style="font-size:0.95rem">Компоненты</h2>
      <ul>{"".join(comp_html)}</ul>
    </section>
    <section>
      <h2 class="muted" style="font-size:0.95rem">Инциденты</h2>
      {incidents_block}
    </section>
    <p class="muted">При проблемах с подключением: обновите подписку в клиенте и напишите в поддержку через Telegram-бот.</p>
    {json_link}
  </main>
</body>
</html>
"""
