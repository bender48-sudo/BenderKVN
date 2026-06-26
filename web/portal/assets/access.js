/* BenderVPN Mini App — Access list (MINI-APP-BUILD-001, P2 read-part).
 *
 * Honest-UI: status, days, device count and billing note all come from /portal-cabinet.
 * Mutations (add device / unbind / reissue / delete) are gated "скоро" until G1+H1 smoke
 * + Remna owner OK. One access summary card → tap → access_detail.html.
 *
 * Endpoint: POST {BASE}/cabinet -> {billing_profile, access_expires_at_iso, days_left,
 *   active_config_count, billing_note, configurations[]}
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
    if (!iso) return null;
    var d = new Date(iso); if (isNaN(d.getTime())) return null;
    return Math.max(0, Math.ceil((d.getTime() - Date.now()) / 86400000));
  }
  function toast(msg) {
    var t = $("toast"); if (!t) return;
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }
  function go(path) { window.location.href = path + (location.search || ""); }

  // billing_profile → status name / pill / paused flag (mirrors home/cabinet mapping)
  function statusOf(doc) {
    var p = (doc.billing_profile || doc.access_profile || "unknown");
    if (p === "trial") return { name: "Триал активен", pill: "Активен", paused: false };
    if (p === "wallet" || p === "legacy") return { name: "Доступ активен", pill: "Активен", paused: false };
    if (p === "expired") return { name: "Доступ на паузе", pill: "Нет средств", paused: true };
    return { name: "Доступ", pill: "—", paused: false };
  }

  function render(doc) {
    var mount = $("access-mount");
    if (!doc || !doc.ok) {
      mount.innerHTML = '<button class="acard" id="acard"><div class="row1"><span class="name">Откройте бота</span></div>' +
        '<div class="meta"><span>Чтобы увидеть доступ, откройте Mini App из бота</span></div></button>';
      $("acard").onclick = function () { go((doc && doc.bot_url) || "/portal/cabinet.html"); };
      return;
    }
    var st = statusOf(doc);
    var dc = doc.active_config_count || 0;
    var days = daysUntil(doc.access_expires_at_iso);
    var daysHtml = st.paused
      ? '<span class="days red">Истекла</span>'
      : (days != null ? '<span class="days">' + days + " " + plural(days, "день", "дня", "дней") + "</span>" : "");
    var billLine = st.paused
      ? '<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3" stroke-linecap="round"/></svg>списание на паузе</span>'
      : '<span><svg class="ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" stroke-linecap="round" stroke-linejoin="round"/></svg>ежедневное списание</span>';

    mount.innerHTML =
      '<button class="acard' + (st.paused ? " expired" : "") + '" id="acard">' +
      '<div class="row1"><span class="name">' + esc(st.name) + "</span>" +
      '<span class="pill ' + (st.paused ? "exp" : "active") + '"><span class="pdot"></span>' + esc(st.pill) + "</span>" +
      '<span class="chevron"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg></span></div>' +
      '<div class="meta">' + daysHtml +
      '<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18" stroke-linecap="round"/></svg>' +
      dc + " " + plural(dc, "устройство", "устройства", "устройств") + "</span>" +
      billLine + "</div></button>";
    $("acard").onclick = function () { go("/portal/access_detail.html"); };

    var note = $("empty-note");
    note.hidden = false;
    note.textContent = st.paused
      ? "Доступ приостановлен — баланс закончился. Пополни баланс, и доступ включится сразу."
      : (dc <= 1
          ? "Это твой единственный доступ. Нужно второе устройство — нажми «Устройство» выше."
          : "У тебя " + dc + " " + plural(dc, "активное устройство", "активных устройства", "активных устройств") + ". Открой карточку, чтобы управлять.");
  }

  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}
    postJson(EP.cabinet, identity()).then(function (r) { render(r.doc); }).catch(function () { render(null); });

    $("btn-back").addEventListener("click", function () {
      if (history.length > 1) history.back(); else go("/portal/home.html");
    });
    // Self-issue of a new device is a mutation → gated until G1+H1 smoke + Remna owner OK.
    $("btn-add-device").addEventListener("click", function () { toast("Скоро — добавление устройства"); });
    document.querySelectorAll(".nav a").forEach(function (a) {
      a.addEventListener("click", function () {
        var nav = a.getAttribute("data-nav");
        if (nav === "access") return;
        var routes = { home: "/portal/home.html", balance: "/portal/balance.html", referral: "/portal/referral.html", support: "/portal/support.html" };
        if (routes[nav]) go(routes[nav]); else toast("Скоро");
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
