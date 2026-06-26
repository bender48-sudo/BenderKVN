/* BenderVPN Mini App — Balance screen wiring (MINI-APP-BUILD-001).
 *
 * Honest-UI: the daily rate, runway date, amounts and history all come from the
 * server. Nothing about pricing is hardcoded here. Endpoints (proxied, same path
 * shape as /setup/api/cabinet):
 *   POST {BASE}/cabinet        -> balance_rub, runway_until_iso, daily_rate
 *   POST {BASE}/tariff         -> presets[{amount_rub,days}], daily_rate, min/max, payments_live
 *   POST {BASE}/transactions   -> [{type,sign,amount_rub,at_utc}]
 *   POST {BASE}/create-payment -> {confirmation_url} (dry-run while gated)
 */
(function () {
  "use strict";

  var BASE = window.BVPN_API_BASE || "/setup/api";
  var EP = {
    cabinet: BASE + "/cabinet",
    tariff: BASE + "/tariff",
    transactions: BASE + "/transactions",
    pay: BASE + "/create-payment",
  };

  var state = { amount: null, presetAmounts: [], min: 0, max: 0, paymentsLive: false };

  function $(id) { return document.getElementById(id); }

  // ---------- identity ----------
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
      // dev/staging override: ?tg=NNN to impersonate without Telegram chrome
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

  // ---------- formatting (display only; values are server-side) ----------
  function fmtRub(rub) {
    var n = Number(rub) || 0;
    var whole = Math.round(n * 100) % 100 === 0 ? n.toFixed(0) : n.toFixed(2).replace(".", ",");
    // thin-space thousands
    return whole.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " ₽";
  }
  function fmtRateRu(rate) {
    return (Number(rate) || 0).toFixed(2).replace(".", ",");
  }
  var MONTHS = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
  function fmtDateRu(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.getUTCDate() + " " + MONTHS[d.getUTCMonth()];
  }
  function fmtHistDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var now = new Date();
    var dayMs = 86400000;
    var a = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
    var b = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    var diff = Math.round((b - a) / dayMs);
    if (diff <= 0) return "сегодня";
    if (diff === 1) return "вчера";
    return fmtDateRu(iso);
  }

  function toast(msg) {
    var t = $("toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }

  // ---------- render: balance hero ----------
  function renderBalance(doc) {
    if (!doc || !doc.ok) {
      $("bal-amount").textContent = "—";
      $("bal-rate-text").textContent = "Не удалось загрузить баланс";
      return;
    }
    $("bal-amount").textContent = fmtRub(doc.balance_rub);
    var runwayIso = doc.runway_until_iso || doc.access_expires_at_iso;
    if (runwayIso) {
      $("bal-runway-text").textContent = "Хватит до " + fmtDateRu(runwayIso);
      $("bal-runway").hidden = false;
    } else {
      $("bal-runway").hidden = true;
    }
    if (typeof doc.daily_rate === "number") {
      $("bal-rate-text").textContent =
        "Списываем " + fmtRateRu(doc.daily_rate) + " ₽ в день за активное устройство";
    }
  }

  // ---------- render: presets + custom ----------
  function setSelectedAmount(amount, fromCustom) {
    state.amount = amount;
    var btns = document.querySelectorAll(".preset");
    btns.forEach(function (b) {
      var on = !fromCustom && Number(b.getAttribute("data-amount")) === amount;
      b.classList.toggle("sel", on);
    });
    var pay = $("btn-pay");
    if (amount && amount > 0) {
      $("btn-pay-text").textContent = "Пополнить на " + fmtRub(amount);
      pay.disabled = false;
    } else {
      $("btn-pay-text").textContent = "Пополнить";
      pay.disabled = true;
    }
  }

  function renderTariff(doc) {
    if (!doc || !doc.ok) return;
    state.presetAmounts = (doc.presets || []).map(function (p) { return p.amount_rub; });
    state.min = doc.min_rub || 0;
    state.max = doc.max_rub || 0;
    state.paymentsLive = !!doc.payments_live;
    var rate = doc.daily_rate;

    var mount = $("presets");
    mount.innerHTML = "";
    (doc.presets || []).forEach(function (p, i) {
      var b = document.createElement("button");
      b.className = "preset";
      b.setAttribute("data-amount", p.amount_rub);
      b.innerHTML =
        '<div class="days">' + p.days + " дней</div>" +
        '<div class="price">' + fmtRub(p.amount_rub) + "</div>" +
        '<div class="per">' + fmtRateRu(rate) + " ₽/день</div>";
      b.addEventListener("click", function () {
        $("custom-input").value = "";
        clearCustomError();
        setSelectedAmount(p.amount_rub, false);
      });
      mount.appendChild(b);
    });

    var hint = $("custom-hint");
    if (state.min && state.max) {
      hint.textContent = "от " + state.min + " до " + fmtRub(state.max).trim();
    }
    // default selection: second preset (matches mockup "90 дней"), else first
    var def = state.presetAmounts[1] || state.presetAmounts[0];
    if (def) setSelectedAmount(def, false);
  }

  function clearCustomError() {
    $("custom-wrap").classList.remove("err");
    var h = $("custom-hint");
    h.classList.remove("err");
    if (state.min && state.max) h.textContent = "от " + state.min + " до " + fmtRub(state.max).trim();
  }

  function onCustomInput() {
    var raw = $("custom-input").value.trim();
    if (!raw) { clearCustomError(); setSelectedAmount(state.presetAmounts[1] || state.presetAmounts[0], false); return; }
    var val = Math.floor(Number(raw));
    var h = $("custom-hint");
    if (!val || val < state.min || val > state.max) {
      $("custom-wrap").classList.add("err");
      h.classList.add("err");
      h.textContent = "Сумма от " + state.min + " до " + fmtRub(state.max).trim();
      setSelectedAmount(null, true);
      return;
    }
    clearCustomError();
    setSelectedAmount(val, true);
  }

  // ---------- render: history ----------
  function renderTransactions(doc) {
    var mount = $("hist-mount");
    var items = (doc && doc.ok && doc.transactions) || [];
    if (!items.length) {
      mount.innerHTML = '<div class="hist-empty">Операций пока нет</div>';
      return;
    }
    var IN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7 7 7-7" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var OUT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3" stroke-linecap="round"/></svg>';
    var html = '<div class="hist">';
    items.forEach(function (t) {
      var isIn = t.type === "topup";
      var title = isIn ? "Пополнение" : "Списание за день";
      var amt = (isIn ? "+" : "−") + fmtRub(t.amount_rub);
      html +=
        '<div class="hrow">' +
        '<div class="hi ' + (isIn ? "in" : "out") + '">' + (isIn ? IN : OUT) + "</div>" +
        "<div><div class=\"ht\">" + title + "</div><div class=\"hd\">" + fmtHistDate(t.at_utc) + "</div></div>" +
        '<div class="hv ' + (isIn ? "plus" : "minus") + '">' + amt + "</div>" +
        "</div>";
    });
    html += "</div>";
    mount.innerHTML = html;
  }

  // ---------- pay ----------
  function onPay() {
    if (!state.amount || state.amount <= 0) return;
    var body = identity();
    body.amount_rub = state.amount;
    var pay = $("btn-pay");
    pay.disabled = true;
    var prev = $("btn-pay-text").textContent;
    $("btn-pay-text").textContent = "Создаём платёж…";
    postJson(EP.pay, body)
      .then(function (res) {
        var doc = res.doc || {};
        if (doc.ok && doc.confirmation_url) {
          // dry-run returns a sandbox URL; live returns the bank page
          toast("Платёж создан · переход к оплате");
          window.location.href = doc.confirmation_url;
          return;
        }
        var msg = "Не удалось создать платёж";
        if (doc.error === "payments_disabled") msg = "Оплата временно недоступна";
        else if (doc.error === "amount_out_of_range") msg = "Сумма от " + state.min + " до " + state.max + " ₽";
        else if (doc.error === "needs_telegram_bind") msg = "Привяжите Telegram, чтобы пополнить";
        else if (doc.error === "terms_required") msg = "Сначала примите условия в боте";
        toast(msg);
        $("btn-pay-text").textContent = prev;
        pay.disabled = false;
      })
      .catch(function () {
        toast("Сеть недоступна, попробуйте позже");
        $("btn-pay-text").textContent = prev;
        pay.disabled = false;
      });
  }

  // ---------- boot ----------
  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}

    var id = identity();
    postJson(EP.cabinet, id).then(function (r) { renderBalance(r.doc); }).catch(function () { renderBalance(null); });
    postJson(EP.tariff, {}).then(function (r) { renderTariff(r.doc); }).catch(function () {});
    postJson(EP.transactions, id).then(function (r) { renderTransactions(r.doc); }).catch(function () {
      $("hist-mount").innerHTML = '<div class="hist-empty">Не удалось загрузить историю</div>';
    });

    $("custom-input").addEventListener("input", onCustomInput);
    $("btn-pay").addEventListener("click", onPay);
    $("btn-back").addEventListener("click", function () {
      var tg = tgWebApp();
      if (tg && tg.BackButton) { history.length > 1 ? history.back() : (window.location.href = "/portal/cabinet.html"); }
      else window.location.href = "/portal/cabinet.html";
    });
    document.querySelectorAll(".nav a").forEach(function (a) {
      a.addEventListener("click", function () {
        var nav = a.getAttribute("data-nav");
        if (nav === "balance") return;
        var routes = { home: "/portal/home.html", access: "/portal/access.html", referral: "/portal/referral.html", support: "/portal/support.html" };
        if (routes[nav]) { window.location.href = routes[nav]; return; }
        toast("Скоро");
      });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
