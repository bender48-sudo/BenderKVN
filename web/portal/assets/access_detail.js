/* BenderVPN Mini App — Access detail (MINI-APP-BUILD-001, P2 read-part).
 *
 * Honest-UI: status, days, devices, sub-link and the "Последний клиент" tag all come from
 * /portal-cabinet. The per-config read fields (last_client/os/version, last_fetch_at_iso,
 * subscription_url) are consumed if present; when absent (Cursor read-API not wired yet) the
 * UI falls back honestly — "Клиент не определён", no "обновлена", sub-link hidden. No guesses.
 *
 * Mutations (unbind / reissue / delete / add / pause) are GATED "скоро" until G1+H1 smoke +
 * Remna owner OK. The "Последний клиент" tag is the last subscription-fetch UA, NOT a live
 * tunnel — independent of HWID, so this read view is not blocked by the smoke.
 */
(function () {
  "use strict";
  var BASE = window.BVPN_API_BASE || "/setup/api";
  var EP = { cabinet: BASE + "/cabinet" };

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function tgWebApp() { return window.Telegram && window.Telegram.WebApp; }
  function identity() {
    var id = {}, tg = tgWebApp(), tid = 0;
    try { var u = tg && tg.initDataUnsafe && tg.initDataUnsafe.user; if (u && u.id) tid = parseInt(u.id, 10) || 0; } catch (e) {}
    var p = new URLSearchParams(location.search);
    if (!tid) tid = parseInt(p.get("tg") || "0", 10) || 0;
    if (tid > 0) { id.telegram_id = tid; id.telegram_user_id = tid; }
    var cid = (p.get("cid") || localStorage.getItem("bvpn_customer_id") || "").trim();
    var em = (p.get("email") || localStorage.getItem("bvpn_email") || "").trim();
    if (cid) id.customer_id = cid;
    if (em) id.email = em;
    return id;
  }
  function postJson(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().then(function (j) { return { status: r.status, doc: j }; }); });
  }
  function plural(n, one, few, many) {
    n = Math.abs(Number(n) || 0) % 100; var n1 = n % 10;
    if (n > 10 && n < 20) return many; if (n1 > 1 && n1 < 5) return few; if (n1 === 1) return one; return many;
  }
  function daysUntil(iso) {
    if (!iso) return null; var d = new Date(iso); if (isNaN(d.getTime())) return null;
    return Math.max(0, Math.ceil((d.getTime() - Date.now()) / 86400000));
  }
  var MONTHS = ["янв","фев","мар","апр","мая","июн","июл","авг","сен","окт","ноя","дек"];
  function fetchDate(iso) {
    if (!iso) return null; var d = new Date(iso); if (isNaN(d.getTime())) return null;
    return d.getUTCDate() + " " + MONTHS[d.getUTCMonth()];
  }
  function isOnline(iso) {
    if (!iso) return false; var d = new Date(iso); if (isNaN(d.getTime())) return false;
    return Date.now() - d.getTime() < 10 * 60 * 1000; // ≤10 min since last sub fetch
  }
  function toast(msg) {
    var t = $("toast"); if (!t) return;
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }
  function copyText(text) {
    if (!text) return;
    var done = function () { toast("Ссылка скопирована"); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { fb(text, done); });
    else fb(text, done);
  }
  function fb(t, done) {
    try { var a = document.createElement("textarea"); a.value = t; a.style.position = "fixed"; a.style.opacity = "0";
      document.body.appendChild(a); a.select(); document.execCommand("copy"); document.body.removeChild(a); done(); }
    catch (e) { toast("Не удалось скопировать"); }
  }
  function go(path) { window.location.href = path + (location.search || ""); }

  function statusOf(doc) {
    var p = (doc.billing_profile || doc.access_profile || "unknown");
    if (p === "trial") return { name: "Триал активен", sub: "Списывается ежедневно, когда триал закончится", pill: "Активен", paused: false };
    if (p === "wallet" || p === "legacy") return { name: "Доступ активен", sub: "Списывается ежедневно с баланса", pill: "Активен", paused: false };
    if (p === "expired") return { name: "Доступ на паузе", sub: "Баланс закончился — пополни, и доступ включится", pill: "Нет средств", paused: true };
    return { name: "Доступ", sub: "", pill: "—", paused: false };
  }

  function GATED(label, icon, wide) {
    return '<button class="da' + (wide ? " wide" : "") + '" data-soon="1">' + icon + esc(label) +
      '<span class="soon-tag">скоро</span></button>';
  }
  var IC = {
    unbind: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 17H7A5 5 0 0 1 7 7h2M15 7h2a5 5 0 0 1 0 10h-2M8 12h8" stroke-linecap="round"/></svg>',
    reissue: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    del: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18" stroke-linecap="round"/></svg>',
    chk: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    q: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .8-1 1.7M12 17v.5" stroke-linecap="round"/></svg>',
  };

  function clientTag(cfg) {
    var name = cfg.last_client;
    if (!name) return '<span class="client-tag unknown">' + IC.q + "Клиент не определён</span>";
    var os = cfg.last_client_os ? " · " + cfg.last_client_os : "";
    var ver = cfg.last_client_version ? " " + cfg.last_client_version : "";
    return '<span class="client-tag">' + IC.chk + "Последний клиент: " + esc(name) + esc(ver) + esc(os) + "</span>";
  }

  function deviceCard(cfg) {
    var online = cfg.active && isOnline(cfg.last_fetch_at_iso);
    var meta = "";
    if (cfg.active && cfg.expires_at) meta += "Активна до <b>" + esc(cfg.expires_at) + "</b>";
    else if (!cfg.active) meta += "Истекла";
    var fd = fetchDate(cfg.last_fetch_at_iso);
    if (fd) meta += (meta ? " · " : "") + "обновлена " + esc(fd);

    var hasSub = !!cfg.subscription_url;
    return (
      '<div class="device">' +
      '<div class="di">' + IC.phone + "</div>" +
      '<div style="flex:1;min-width:0">' +
      '<div class="dn">' + esc(cfg.label || "Настройка") + (online ? '<span class="online" title="активна"></span>' : "") + "</div>" +
      '<div class="dmeta">' + meta + "</div>" +
      clientTag(cfg) +
      "</div>" +
      '<div class="dev-actions">' +
      (hasSub ? '<button class="da" data-copy="' + esc(cfg.subscription_url) + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>Ссылка</button>' : "") +
      GATED("Отвязать", IC.unbind) +
      GATED("Перевыпустить", IC.reissue) +
      GATED("Удалить устройство", IC.del, true) +
      "</div></div>"
    );
  }

  function render(doc) {
    if (!doc || !doc.ok) {
      $("st-name").textContent = doc && doc.error === "terms_required" ? "Примите условия в боте" : "Откройте бота";
      $("connect-card").onclick = function () { go((doc && doc.bot_url) || "/portal/cabinet.html"); };
      return;
    }
    var st = statusOf(doc);
    if (st.paused) $("status-card").classList.add("paused");
    $("st-name").textContent = st.name;
    $("st-sub").textContent = st.sub;
    var pill = $("st-pill");
    pill.className = "pill " + (st.paused ? "exp" : "active");
    $("st-pill-text").textContent = st.pill;
    pill.hidden = false;

    var days = daysUntil(doc.access_expires_at_iso);
    $("m-days").textContent = st.paused ? "0" : (days != null ? days : "—");
    var dc = doc.active_config_count || 0;
    $("m-dev").textContent = dc;

    // configurations: active first, by key_id
    var cfgs = (doc.configurations || []).slice().sort(function (a, b) {
      return (b.active === a.active) ? (a.key_id || 0) - (b.key_id || 0) : (b.active ? 1 : -1);
    });
    $("dev-count").textContent = dc + (cfgs.length > dc ? " / " + cfgs.length : "");
    if (!cfgs.length) {
      $("devices-mount").innerHTML = '<div class="dmeta" style="color:var(--text-mute)">Пока нет настроек. Нажми «Подключить устройство».</div>';
    } else {
      $("devices-mount").innerHTML = cfgs.map(deviceCard).join("");
    }

    // top-level sub-link = primary active config's subscription_url (A: per-config)
    var primary = cfgs.filter(function (c) { return c.active && c.subscription_url && (c.is_primary || c.is_current); })[0]
      || cfgs.filter(function (c) { return c.active && c.subscription_url; })[0];
    if (primary) {
      $("sublink-section").hidden = false;
      $("sub-url").textContent = primary.subscription_url;
      $("sub-url").title = primary.subscription_url;
      $("btn-copy-sub").onclick = function () { copyText(primary.subscription_url); };
    } else {
      // honest: no sub-link yet (read-API not wired / no active config) — hide, don't fake
      $("sublink-section").hidden = true;
    }

    // wire gated + per-device copy actions
    document.querySelectorAll('[data-soon]').forEach(function (b) {
      b.addEventListener("click", function () { toast("Скоро — управление устройством"); });
    });
    document.querySelectorAll('[data-copy]').forEach(function (b) {
      b.addEventListener("click", function () { copyText(b.getAttribute("data-copy")); });
    });
  }

  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}
    postJson(EP.cabinet, identity()).then(function (r) { render(r.doc); }).catch(function () { render(null); });

    $("btn-back").addEventListener("click", function () {
      if (history.length > 1) history.back(); else go("/portal/access.html");
    });
    $("connect-card").addEventListener("click", function () { go("/portal/wizard.html"); });
    $("btn-topup").addEventListener("click", function () { go("/portal/balance.html"); });
    // self-issue + pause are mutations → gated until smoke + Remna owner OK
    $("row-add").addEventListener("click", function () { toast("Скоро — добавление устройства"); });
    $("row-pause").addEventListener("click", function () { toast("Скоро — пауза доступа"); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
