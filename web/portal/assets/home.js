/* BenderVPN Mini App — Home screen wiring (MINI-APP-BUILD-001, P-HOME).
 *
 * Honest-UI: access status, days, device count, balance, referral counters and banner
 * flags all come from /portal-home. The greeting name comes from Telegram initData
 * (first_name) since the server does not store it. Nothing is fabricated:
 *   - capacity counter is "счётчик скоро" (no live number) — indeterminate bar, no fill %.
 *   - bell shows a real unread count (0 until tickets) — no fake badge.
 *   - Fortune banner is shown only when the server flag says so, in "in_development".
 *
 * Endpoint: POST {BASE}/home -> {profile, unread, access, balance, referral, capacity, banners}
 */
(function () {
  "use strict";

  var BASE = window.BVPN_API_BASE || "/setup/api";
  var EP = { home: BASE + "/home" };

  function $(id) { return document.getElementById(id); }

  // ---------- identity (mirror balance.js / referral.js) ----------
  function tgWebApp() { return window.Telegram && window.Telegram.WebApp; }
  function tgUser() {
    var tg = tgWebApp();
    try { return (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || null; } catch (e) { return null; }
  }
  function telegramUserId() {
    var u = tgUser();
    return u && u.id ? (parseInt(u.id, 10) || 0) : 0;
  }
  function identity() {
    var id = {};
    var tid = telegramUserId();
    if (tid > 0) { id.telegram_id = tid; id.telegram_user_id = tid; }
    try {
      var p = new URLSearchParams(location.search);
      var cid = (p.get("cid") || localStorage.getItem("bvpn_customer_id") || "").trim();
      var em = (p.get("email") || localStorage.getItem("bvpn_email") || "").trim();
      var devTg = parseInt(p.get("tg") || "0", 10);
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

  // ---------- formatting ----------
  function fmtRub(rub) {
    var n = Number(rub) || 0;
    var whole = Math.round(n * 100) % 100 === 0 ? n.toFixed(0) : n.toFixed(2).replace(".", ",");
    return whole.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " ₽";
  }
  function fmtInt(n) { return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " "); }
  function plural(n, one, few, many) {
    n = Math.abs(Number(n) || 0) % 100;
    var n1 = n % 10;
    if (n > 10 && n < 20) return many;
    if (n1 > 1 && n1 < 5) return few;
    if (n1 === 1) return one;
    return many;
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

  function go(path) { window.location.href = path; }

  var ROUTES = {
    home: "/portal/home.html",
    access: "/portal/access.html",
    balance: "/portal/balance.html",
    referral: "/portal/referral.html",
  };
  function navTo(nav) {
    if (nav === "home") { closeDrawer(); return; }
    if (ROUTES[nav]) { go(ROUTES[nav]); return; }
    // support / info / profile / fortune / logout — not migrated yet (Variant 1)
    toast("Скоро");
  }

  // ---------- greeting name (Telegram first) ----------
  function greetingName(doc) {
    var u = tgUser();
    if (u && u.first_name) return u.first_name;
    var p = (doc && doc.profile) || {};
    if (p.username) return p.username;
    return "";
  }

  // ---------- render ----------
  function renderError(doc) {
    var name = $("access-name");
    name.textContent = (doc && doc.error === "terms_required")
      ? "Сначала примите условия в боте"
      : "Откройте бота, чтобы начать";
    $("access-days").textContent = "";
    $("access-meta").innerHTML = "";
    $("access-card").onclick = function () { go((doc && doc.bot_url) || ROUTES.access); };
    $("bal-val").textContent = "—";
    $("bal-sub").textContent = "";
    $("ref-val").textContent = "—";
    $("ref-sub").textContent = "";
    $("greet-name").textContent = "";
  }

  function renderAccess(a) {
    var card = $("access-card");
    var status = (a && a.status) || "unknown";

    var pill = $("status-pill");
    pill.className = "pill " + (status === "trial" ? "trial" : status === "active" ? "active" : "paused");
    $("status-text").textContent = (a && a.status_label) || "";
    pill.hidden = !(a && a.status_label);

    $("access-name").textContent = (a && a.card_title) || "Доступ";
    var days = a && a.days_left;
    $("access-days").textContent = (days != null && days > 0)
      ? fmtInt(days) + " " + plural(days, "день", "дня", "дней")
      : (status === "paused" ? "" : "");

    var meta = [];
    var dc = (a && a.device_count) || 0;
    meta.push("<span>" + fmtInt(dc) + " " + plural(dc, "устройство", "устройства", "устройств") + "</span>");
    if (a && a.traffic_unlimited) {
      meta.push('<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2"><path d="M20 6L9 17l-5-5" stroke-linecap="round" stroke-linejoin="round"/></svg>без лимита</span>');
    }
    $("access-meta").innerHTML = meta.join("");
    // Access detail screen not migrated yet → soft "soon"; CTA goes to the setup wizard.
    card.onclick = function () { toast("Скоро — детальный экран доступа"); };
  }

  function renderTiles(doc) {
    var b = doc.balance || {};
    $("bal-val").textContent = fmtRub(b.balance_rub);
    var bd = b.days_left || 0;
    $("bal-sub").textContent = bd > 0 ? "≈ " + fmtInt(bd) + " " + plural(bd, "день", "дня", "дней") : "пополни баланс";
    $("tile-balance").onclick = function () { go(ROUTES.balance); };

    var r = doc.referral || {};
    $("ref-val").textContent = fmtInt(r.friends_count);
    var fc = r.friends_count || 0;
    var sub = fc > 0
      ? fc + " " + plural(fc, "друг", "друга", "друзей") + " · " + fmtRub(r.earned_rub)
      : "приглашай друзей";
    $("ref-sub").textContent = sub;
    $("tile-referral").onclick = function () { go(ROUTES.referral); };
  }

  function renderCapacity(cap) {
    if (!cap) { $("capacity").hidden = true; return; }
    $("capacity").hidden = false;
    var bar = $("cap-bar");
    if (cap.counter_available) {
      // future: real fill from the server; for now we never fabricate one
      bar.classList.remove("indet");
      $("cap-tag").hidden = true;
    } else {
      bar.classList.add("indet"); // honest indeterminate — no fabricated fill width
      $("cap-tag").textContent = "счётчик скоро";
    }
    var lim = fmtInt(cap.cap_limit || 0);
    $("cap-note").innerHTML =
      "Берём не больше <b>" + esc(lim) + "</b> активных подписок. Дальше выдачу новых ставим на " +
      "паузу — чтобы держать скорость и стабильность для своих.";
  }

  function renderBanners(doc) {
    var banners = doc.banners || {};
    var prog = (doc.referral_program) || {};
    // referral banner
    var refBan = $("banner-referral");
    refBan.hidden = !banners.referral;
    if (banners.referral) {
      $("banner-referral-sub").textContent = "Другу 100 ₽ на старт, тебе 30% с его пополнения.";
      refBan.onclick = function () { go(ROUTES.referral); };
    }
    // fortune banner (gated, in development)
    var f = banners.fortune || {};
    var fBan = $("banner-fortune");
    fBan.hidden = !f.show;
    if (f.show) {
      $("fortune-tag").textContent = f.state === "in_development" ? "в доработке" : "скоро";
      fBan.onclick = function () { toast("Фортуна в доработке — скоро запустим"); };
    }
  }

  function renderHeader(doc) {
    $("greet-name").textContent = (function () {
      var n = greetingName(doc);
      return n ? ", " + n : "";
    })();
    var p = doc.profile || {};
    var lang = (p.language || "ru").toLowerCase();
    setLangLabel(lang);

    // bell unread
    var unread = Number(doc.unread) || 0;
    var dot = $("bell-dot");
    if (unread > 0) { dot.textContent = unread > 99 ? "99+" : unread; dot.classList.add("show"); }
    else { dot.classList.remove("show"); }

    // drawer user
    var u = tgUser();
    var fullName = u
      ? ((u.first_name || "") + (u.last_name ? " " + u.last_name : "")).trim()
      : "";
    fullName = fullName || p.username || "Пользователь";
    $("dh-name").textContent = fullName;
    $("dh-uname").textContent = p.username ? "@" + p.username : "";
    $("dh-ava").textContent = (fullName[0] || "?").toUpperCase();
  }

  function render(doc) {
    if (!doc || !doc.ok) { renderError(doc); return; }
    renderHeader(doc);
    renderAccess(doc.access || {});
    renderTiles(doc);
    renderCapacity(doc.capacity);
    renderBanners(doc);
  }

  // ---------- language (display-only until /portal-locale lands) ----------
  function setLangLabel(lang) {
    $("langLabel").textContent = (lang === "en" ? "EN" : "RU");
    document.querySelectorAll(".lang-menu button").forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-lang") === lang);
    });
  }

  // ---------- drawer ----------
  function openDrawer() { $("drawer").classList.add("open"); }
  function closeDrawer() { $("drawer").classList.remove("open"); }

  // ---------- boot ----------
  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}

    postJson(EP.home, identity())
      .then(function (r) { render(r.doc); })
      .catch(function () { render(null); });

    // header
    $("btn-bell").addEventListener("click", function () { toast("Уведомлений пока нет"); });
    $("btn-lang").addEventListener("click", function (e) {
      e.stopPropagation();
      $("lang-wrap").classList.toggle("open");
    });
    document.querySelectorAll(".lang-menu button").forEach(function (b) {
      b.addEventListener("click", function () {
        setLangLabel(b.getAttribute("data-lang"));
        $("lang-wrap").classList.remove("open");
        // Persisting the choice needs POST /portal-locale (not built yet) — display-only for now.
        toast("Смена языка — скоро");
      });
    });
    document.addEventListener("click", function () { $("lang-wrap").classList.remove("open"); });
    $("btn-burger").addEventListener("click", openDrawer);
    $("drawer-close").addEventListener("click", closeDrawer);
    $("drawer").addEventListener("click", function (e) { if (e.target === $("drawer")) closeDrawer(); });

    // CTA → setup wizard
    $("btn-connect").addEventListener("click", function () { go("/portal/wizard.html"); });
    $("link-manage").addEventListener("click", function () { toast("Скоро — управление доступом"); });

    // nav (bottom + drawer)
    document.querySelectorAll(".nav a, .drawer-list .dl").forEach(function (a) {
      a.addEventListener("click", function () { navTo(a.getAttribute("data-nav")); });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
