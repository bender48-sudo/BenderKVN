/* BenderVPN Mini App — Referral screen wiring (MINI-APP-BUILD-001, P3).
 *
 * Honest-UI: the invite link, code, counters, invitee list, earnings and program
 * terms all come from the server (/portal-referral). Nothing about reward amounts is
 * hardcoded here. While accrual is gated OFF, earned_rub is 0 and per-invitee
 * reward_rub is null — shown as-is, never a fabricated number.
 *
 * Endpoint (proxied, same path shape as /setup/api/cabinet):
 *   POST {BASE}/referral -> {available, ref_code, invite_url, friends_count,
 *                            earned_rub, invitees[], program{}, partner{},
 *                            needs_telegram_bind?}
 *
 * Renders three states: regular user (screen 1), approved partner (screen 2,
 * read-only), and a "bind Telegram" prompt for web-only users.
 */
(function () {
  "use strict";

  var BASE = window.BVPN_API_BASE || "/setup/api";
  var EP = { referral: BASE + "/referral" };

  function $(id) { return document.getElementById(id); }

  // ---------- identity (mirror balance.js) ----------
  function tgWebApp() { return window.Telegram && window.Telegram.WebApp; }
  function telegramUserId() {
    var tg = tgWebApp();
    try {
      var u = tg && tg.initDataUnsafe && tg.initDataUnsafe.user;
      if (u && u.id) return parseInt(u.id, 10) || 0;
    } catch (e) { /* ignore */ }
    return 0;
  }
  function identity() {
    var id = {};
    var tid = telegramUserId();
    if (tid > 0) { id.telegram_id = tid; id.telegram_user_id = tid; }
    try {
      var p = new URLSearchParams(location.search);
      var cid = (p.get("cid") || localStorage.getItem("bvpn_customer_id") || "").trim();
      var em = (p.get("email") || localStorage.getItem("bvpn_email") || "").trim();
      var devTg = parseInt(p.get("tg") || "0", 10); // dev/staging: ?tg=NNN
      if (!id.telegram_id && devTg > 0) { id.telegram_id = devTg; id.telegram_user_id = devTg; }
      if (cid) id.customer_id = cid;
      if (em) id.email = em;
    } catch (e) { /* ignore */ }
    return id;
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) { return r.json().then(function (j) { return { status: r.status, doc: j }; }); });
  }

  // ---------- formatting (display only) ----------
  function fmtRub(rub) {
    var n = Number(rub) || 0;
    var whole = Math.round(n * 100) % 100 === 0 ? n.toFixed(0) : n.toFixed(2).replace(".", ",");
    return whole.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " ₽";
  }
  var MONTHS = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
  function fmtDateRu(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var now = new Date();
    var a = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
    var b = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    var diff = Math.round((b - a) / 86400000);
    if (diff <= 0) return "сегодня";
    if (diff === 1) return "вчера";
    return d.getUTCDate() + " " + MONTHS[d.getUTCMonth()];
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function toast(msg) {
    var t = $("toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }

  function copyText(text) {
    if (!text) return;
    var done = function () { toast("Ссылка скопирована"); };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
      } else { fallbackCopy(text, done); }
    } catch (e) { fallbackCopy(text, done); }
  }
  function fallbackCopy(text, done) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select(); document.execCommand("copy");
      document.body.removeChild(ta); done();
    } catch (e) { toast("Не удалось скопировать"); }
  }

  function shareLink(url, text) {
    if (!url) return;
    var tg = tgWebApp();
    var shareUrl = "https://t.me/share/url?url=" + encodeURIComponent(url) +
      "&text=" + encodeURIComponent(text || "");
    if (tg && tg.openTelegramLink) { tg.openTelegramLink(shareUrl); return; }
    if (navigator.share) { navigator.share({ url: url, text: text }).catch(function () {}); return; }
    window.open(shareUrl, "_blank");
  }

  function drawQr(canvasId, url) {
    var canvas = $(canvasId);
    if (!canvas || !url) return;
    if (window.QRCode && QRCode.toCanvas) {
      QRCode.toCanvas(canvas, url, { width: 140, margin: 1, color: { dark: "#0A0E14", light: "#ffffff" } },
        function () { /* on error the link + copy still work */ });
    }
  }

  function show(screenId, title) {
    ["screen-loading", "screen-user", "screen-partner", "screen-bind"].forEach(function (s) {
      var el = $(s); if (el) el.hidden = s !== screenId;
    });
    if (title) $("tb-title").textContent = title;
  }

  // ---------- render: regular user (screen 1) ----------
  function renderUser(doc) {
    var prog = doc.program || {};
    var friendBonus = prog.friend_bonus_rub;
    var refPct = prog.referrer_pct;

    $("user-terms").textContent =
      "Друг получит " + fmtRub(friendBonus) + " на старт, ты — " + refPct + "% с его первого пополнения.";
    $("how-2").innerHTML = "Друг регистрируется — ему сразу падает <b>" + esc(fmtRub(friendBonus)) + "</b> на баланс.";
    $("how-3").innerHTML = "Друг первый раз пополняет счёт — тебе на баланс <b>" + esc(refPct) + "%</b> от его суммы.";

    var link = doc.invite_url || "";
    $("user-link").textContent = link.replace(/^https?:\/\//, "");
    $("user-link").title = link;
    drawQr("qr-user", doc.qr_url || link);

    $("user-friends").textContent = (doc.friends_count || 0);
    // Honest: earned_rub is real from the ledger; 0 while accrual is OFF — shown as 0 ₽.
    $("user-earned").textContent = fmtRub(doc.earned_rub || 0);

    renderInvited(doc.invitees || []);

    $("user-copy").onclick = function () { copyText(link); };
    $("user-share").onclick = function () {
      shareLink(link, "Залетай в BenderVPN — " + fmtRub(friendBonus) + " на старт.");
    };
    $("user-partner-cta").onclick = function () {
      // Partner application becomes a real ticket once the ticket system (P4) ships.
      toast("Скоро — заявку можно будет оставить через поддержку");
    };

    show("screen-user", "Рефералы");
  }

  function renderInvited(list) {
    var mount = $("user-invited");
    if (!list.length) {
      mount.innerHTML = '<div class="empty">Пока никого не пригласил.<br>Поделись ссылкой выше — приглашённые появятся здесь.</div>';
      return;
    }
    var html = '<div class="invited">';
    list.forEach(function (inv) {
      var paid = inv.status === "paid";
      var when = fmtDateRu(paid ? inv.first_topup_at_iso : inv.joined_at_iso);
      var sub = (paid ? "пополнил" : "зарегистрировался") + (when ? " · " + when : "");
      var right;
      if (inv.reward_rub != null && Number(inv.reward_rub) > 0) {
        // Real credited reward (only present once accrual is enabled).
        right = '<span class="iearn">+' + esc(fmtRub(inv.reward_rub)) + "</span>";
      } else if (paid) {
        // Friend paid but no reward credited yet (accrual gated) — honest status, no fake ₽.
        right = '<span class="ist paid">пополнил</span>';
      } else {
        right = '<span class="ist reg">ждём</span>';
      }
      html +=
        '<div class="inv">' +
        '<div class="ia">' + esc(inv.avatar_letter || "?") + "</div>" +
        "<div><div class=\"iname\">" + esc(inv.name || "Без имени") + "</div>" +
        '<div class="idate">' + esc(sub) + "</div></div>" +
        right + "</div>";
    });
    html += "</div>";
    mount.innerHTML = html;
  }

  // ---------- render: partner (screen 2, read-only) ----------
  function partnerLink(doc) {
    var p = doc.partner || {};
    if (!p.slug) return doc.invite_url || "";
    var origin = "";
    try { origin = new URL(doc.invite_url || location.href).origin; } catch (e) { origin = location.origin; }
    return origin + "/p/" + p.slug;
  }

  function renderPartner(doc) {
    var p = doc.partner || {};
    var prog = (doc.program && doc.program.partner) || {};

    $("partner-name").textContent = "Партнёр" + (p.display_name ? " · " + p.display_name : "");
    $("partner-available").textContent = fmtRub(p.available_rub || 0);
    $("partner-clients").textContent = (p.clients_count || 0);
    $("partner-earned").textContent = fmtRub(p.total_earned_rub || 0);

    $("pcond-1").innerHTML = "<b>" + esc(prog.first_pct) + "%</b> с первого пополнения каждого приведённого клиента.";
    $("pcond-2").innerHTML = "<b>" + esc(prog.recurring_pct) + "%</b> со всех его последующих пополнений — постоянно.";
    $("pcond-3").innerHTML = "Клиент по твоему QR получает <b>" + esc(fmtRub(prog.friend_bonus_rub)) + "</b> на старт.";

    var min = p.min_withdraw_rub || prog.min_withdraw_rub || 0;
    $("partner-terms").innerHTML =
      wt('<path d="M12 2v20M2 12h20" stroke-linecap="round"/>', "Вывод от " + fmtRub(min) + ".") +
      wt('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18" stroke-linecap="round"/>', "Заявки обрабатываем 15-го числа каждого месяца.") +
      wt('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3" stroke-linecap="round"/>', "Деньги приходят в течение 2 рабочих дней.");

    var link = partnerLink(doc);
    $("partner-link").textContent = link.replace(/^https?:\/\//, "");
    $("partner-link").title = link;
    drawQr("qr-partner", link);
    $("partner-copy").onclick = function () { copyText(link); };

    var wbtn = $("partner-withdraw");
    // Withdraw form (requisites → ticket) waits on the ticket system (P4): gated "soon".
    wbtn.disabled = !p.withdraw_enabled;
    wbtn.onclick = function () {
      if (p.withdraw_enabled) return; // real flow lands with tickets
      toast("Скоро — вывод появится вместе с поддержкой");
    };

    show("screen-partner", "Партнёрский кабинет");
  }
  function wt(pathInner, text) {
    return '<div class="wt"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      pathInner + "</svg>" + esc(text) + "</div>";
  }

  // ---------- render: bind prompt ----------
  function renderBind() {
    show("screen-bind", "Рефералы");
    $("bind-cta").onclick = function () { window.location.href = "/portal/cabinet.html"; };
  }

  // ---------- boot ----------
  function render(doc) {
    if (!doc || !doc.ok) {
      show("screen-bind", "Рефералы");
      $("bind-cta").textContent = "Открыть кабинет";
      $("screen-bind").querySelector("h2").textContent = "Не удалось загрузить";
      $("screen-bind").querySelector("p").textContent =
        "Реферальная программа недоступна. Открой кабинет и попробуй ещё раз.";
      $("bind-cta").onclick = function () { window.location.href = "/portal/cabinet.html"; };
      return;
    }
    if (doc.available === false || doc.needs_telegram_bind) { renderBind(); return; }
    if (doc.partner && doc.partner.is_partner) { renderPartner(doc); return; }
    renderUser(doc);
  }

  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}

    postJson(EP.referral, identity())
      .then(function (r) { render(r.doc); })
      .catch(function () { render(null); });

    $("btn-back").addEventListener("click", function () {
      if (history.length > 1) history.back();
      else window.location.href = "/portal/cabinet.html";
    });
    document.querySelectorAll(".nav a").forEach(function (a) {
      a.addEventListener("click", function () {
        var nav = a.getAttribute("data-nav");
        if (nav === "referral") return;
        var routes = { home: "/portal/home.html", access: "/portal/access.html", balance: "/portal/balance.html" };
        if (routes[nav]) { window.location.href = routes[nav]; return; }
        toast("Скоро"); // support not migrated yet (Variant 1, per-screen)
      });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
