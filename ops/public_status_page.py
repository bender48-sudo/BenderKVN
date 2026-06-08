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
_LEGACY_STATUS_MSG_RU = {
    "all core checks green.": "Все основные проверки пройдены.",
    "degraded: review nodes/subscription in json.": "Есть ограничения — смотрите компоненты ниже.",
}


def _status_message_ru(message: str, overall: str) -> str:
    raw = (message or "").strip()
    if not raw:
        return (
            "Все основные проверки пройдены."
            if overall == "ok"
            else "Есть ограничения — смотрите компоненты ниже."
        )
    mapped = _LEGACY_STATUS_MSG_RU.get(raw.lower())
    if mapped:
        return mapped
    return raw


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
    message = html.escape(_status_message_ru(str(status.get("message", "")), overall))

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

    status_pill = "status__dot--ok" if css_class == "operational" else "status__dot--warn"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta http-equiv="refresh" content="120">
  <meta name="theme-color" content="#09090b">
  <title>Статус сервиса — BenderVPN</title>
  <link rel="stylesheet" href="/portal/assets/portal.css">
  <style>
    .status-page-main {{ max-width: 28rem; margin: 0 auto; padding: 0 1rem 2rem; }}
    .status-hero {{ margin-top: 0.5rem; }}
    .status-hero__title {{ margin: 0 0 0.35rem; font-size: 1.35rem; }}
    .status-hero__lead {{ margin: 0; }}
    .status-overall {{
      display: flex;
      align-items: flex-start;
      gap: 0.65rem;
      margin-top: 1rem;
    }}
    .status-overall__text {{ margin: 0; }}
    .status-overall__headline {{ margin: 0 0 0.35rem; font-size: 1.05rem; font-weight: 600; }}
    .status-components {{ list-style: none; padding: 0; margin: 0.75rem 0 0; }}
    .status-components li {{ padding: 0.3rem 0; }}
    .status-components li::before {{ margin-right: 0.35rem; }}
    .comp-ok::before {{ content: "✓"; color: var(--accent); }}
    .comp-degraded::before {{ content: "!"; color: var(--warn); }}
    .comp-unknown::before {{ content: "?"; color: var(--muted); }}
    .status-incident {{ margin-top: 0.75rem; }}
    .status-incident h2 {{ font-size: 1rem; margin: 0 0 0.35rem; }}
    .status-incident .inc-status {{ color: var(--warn); margin: 0 0 0.5rem; font-size: 0.9rem; }}
    .status-footnote {{ margin-top: 1rem; }}
  </style>
</head>
<body class="cosmic">
  <div class="cosmic-bg" aria-hidden="true"></div>
  <main class="status-page-main">
    <header class="top top--sub">
      <p class="top__eyebrow">BenderVPN</p>
      <a class="nav-link" href="/start/">← Главная</a>
    </header>

    <section class="glass status-hero">
      <h1 class="status-hero__title">Статус сервиса</h1>
      <p class="status-hero__lead muted">Публичная страница: работают ли VPN, выдача подписки и активные инциденты.</p>
    </section>

    <section class="sheet glass">
      <div class="status-overall">
        <span class="status__dot {status_pill}" aria-hidden="true"></span>
        <div class="status-overall__text">
          <p class="status-overall__headline">{headline}</p>
          <p class="muted">{message}</p>
          <p class="muted" style="margin-top:0.5rem">Обновлено (UTC): {updated}</p>
        </div>
      </div>
    </section>

    <section class="sheet glass">
      <h2 class="sheet__label">Компоненты</h2>
      <ul class="status-components muted">{"".join(comp_html)}</ul>
    </section>

    <section class="sheet glass">
      <h2 class="sheet__label">Инциденты</h2>
      {incidents_block}
    </section>

    <p class="status-footnote muted">Если VPN не подключается: обнови подписку в Happ (профиль BenderVPN Auto) и напиши в поддержку через Telegram-бот.</p>
    {json_link}

    <footer class="site-footer" style="margin-top:1.5rem">
      <nav class="site-footer__nav" aria-label="Навигация сайта">
        <a class="site-footer__link" href="/start/">Главная</a>
        <span class="site-footer__sep" aria-hidden="true">·</span>
        <a class="site-footer__link" href="/portal/guide.html">Инструкция</a>
        <span class="site-footer__sep" aria-hidden="true">·</span>
        <a class="site-footer__link" href="/status">Статус</a>
        <span class="site-footer__sep" aria-hidden="true">·</span>
        <a class="site-footer__link" href="https://t.me/Bender_KVN_bot" target="_blank" rel="noopener">Поддержка</a>
        <span class="site-footer__sep" aria-hidden="true">·</span>
        <a class="site-footer__link" href="/portal/legal/privacy.html">Политика конфиденциальности</a>
        <span class="site-footer__sep" aria-hidden="true">·</span>
        <a class="site-footer__link" href="/portal/legal/terms.html">Условия пользования</a>
      </nav>
    </footer>
  </main>
</body>
</html>
"""
