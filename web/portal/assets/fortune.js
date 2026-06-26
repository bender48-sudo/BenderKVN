/* BenderVPN Mini App — Fortune wheel (MINI-APP-BUILD-001, P5).
 *
 * SERVER-AUTHORITATIVE: the front never decides the outcome. /portal-fortune-spin returns the
 * winning sector_key; this code only animates the wheel to that sector and shows the result.
 * Counters, history and the gate come from /portal-fortune. Honest-UI: gated off → wheel +
 * "в доработке" + disabled button; real ₽ are credited server-side (ledger) and reflected here.
 *
 * Endpoints: POST {BASE}/fortune (status) · {BASE}/fortune-spin (spin).
 */
(function () {
  "use strict";
  var BASE = window.BVPN_API_BASE || "/setup/api";
  var EP = { status: BASE + "/fortune", spin: BASE + "/fortune-spin" };

  // Visual wheel layout (6 equal segments). Order is fixed; outcome maps server key → index.
  var VIEW = [
    { key: "miss", label: "Мимо", sub: "", color: "#1C242E", text: "#9AA4B2" },
    { key: "rub2", label: "+2 ₽", sub: "на баланс", color: "#FF6B1A", text: "#1a0c02" },
    { key: "extra_spin", label: "Ещё спин", sub: "крути снова", color: "#243040", text: "#F2F4F7" },
    { key: "rub5", label: "+5 ₽", sub: "на баланс", color: "#FF8340", text: "#1a0c02" },
    { key: "rub20", label: "+20 ₽", sub: "на баланс", color: "#E8B84B", text: "#1a0c02" },
    { key: "jackpot", label: "ДЖЕКПОТ", sub: "+50 ₽", color: "#2FBF71", text: "#06210f" },
  ];
  var KEY_INDEX = {}; VIEW.forEach(function (s, i) { KEY_INDEX[s.key] = i; });
  var N = VIEW.length, SEG = 360 / N;

  var state = { live: false, available: 0, spinning: false, rot: 0 };

  function $(id) { return document.getElementById(id); }
  function tgWebApp() { return window.Telegram && window.Telegram.WebApp; }
  function identity() {
    var id = {}, tg = tgWebApp(), tid = 0;
    try { var u = tg && tg.initDataUnsafe && tg.initDataUnsafe.user; if (u && u.id) tid = parseInt(u.id, 10) || 0; } catch (e) {}
    var p = new URLSearchParams(location.search);
    if (!tid) tid = parseInt(p.get("tg") || "0", 10) || 0;
    if (tid > 0) { id.telegram_id = tid; id.telegram_user_id = tid; }
    var cid = (p.get("cid") || localStorage.getItem("bvpn_customer_id") || "").trim();
    var em = (p.get("email") || localStorage.getItem("bvpn_email") || "").trim();
    if (cid) id.customer_id = cid; if (em) id.email = em;
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
  function fmtRub(n) { n = Number(n) || 0; return (Math.round(n * 100) % 100 === 0 ? n.toFixed(0) : n.toFixed(2).replace(".", ",")) + " ₽"; }

  // ---------- wheel ----------
  var cv = $("wheel"), ctx = cv.getContext("2d"), R = 150, C = 150;
  function drawWheel() {
    ctx.clearRect(0, 0, 300, 300);
    for (var i = 0; i < N; i++) {
      var a0 = (i * SEG - 90) * Math.PI / 180, a1 = ((i + 1) * SEG - 90) * Math.PI / 180;
      ctx.beginPath(); ctx.moveTo(C, C); ctx.arc(C, C, R, a0, a1); ctx.closePath();
      ctx.fillStyle = VIEW[i].color; ctx.fill();
      ctx.strokeStyle = "rgba(0,0,0,.25)"; ctx.lineWidth = 2; ctx.stroke();
      ctx.save();
      var mid = (a0 + a1) / 2;
      ctx.translate(C + Math.cos(mid) * R * 0.62, C + Math.sin(mid) * R * 0.62);
      ctx.rotate(mid + Math.PI / 2);
      ctx.fillStyle = VIEW[i].text; ctx.textAlign = "center";
      ctx.font = "700 15px Onest, sans-serif"; ctx.fillText(VIEW[i].label, 0, 0);
      if (VIEW[i].sub) { ctx.font = "500 10px Onest, sans-serif"; ctx.globalAlpha = .85; ctx.fillText(VIEW[i].sub, 0, 14); ctx.globalAlpha = 1; }
      ctx.restore();
    }
  }

  function animateTo(idx, cb) {
    var targetMid = idx * SEG + SEG / 2;
    var finalRot = 5 * 360 + (360 - targetMid) - (state.rot % 360) + state.rot;
    var dur = 4200, start = performance.now(), from = state.rot, delta = finalRot - state.rot;
    function ease(t) { return 1 - Math.pow(1 - t, 3.4); }
    function frame(now) {
      var t = Math.min((now - start) / dur, 1);
      state.rot = from + delta * ease(t);
      $("wheel").style.transform = "rotate(" + state.rot + "deg)";
      if (t < 1) requestAnimationFrame(frame); else cb();
    }
    requestAnimationFrame(frame);
  }

  // ---------- result toast ----------
  function showResult(res) {
    var tw = $("toastWin"), ts = $("toastSub");
    if (res.kind === "nothing") { tw.textContent = "Мимо"; tw.style.color = "var(--text-mute)"; ts.textContent = "в следующий раз повезёт"; }
    else if (res.kind === "extra_spin") { tw.textContent = "Ещё прокрутка!"; tw.style.color = "var(--accent)"; ts.textContent = "крути снова"; }
    else { tw.textContent = "+" + fmtRub(res.amount_rub); tw.style.color = (res.sector_key === "jackpot" || res.sector_key === "rub20") ? "var(--gold)" : "var(--accent)"; ts.textContent = res.sector_key === "jackpot" ? "джекпот на баланс!" : "упало на баланс"; }
    var t = $("toast"); t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 2400);
  }
  function toastText(msg) {
    var tw = $("toastWin"), ts = $("toastSub");
    tw.textContent = msg; tw.style.color = "var(--text)"; ts.textContent = "";
    var t = $("toast"); t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }

  // ---------- status render ----------
  var MONTHS = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
  function relDate(iso) {
    if (!iso) return ""; var d = new Date(iso); if (isNaN(d.getTime())) return "";
    var now = new Date();
    var diff = Math.round((Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()) - Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())) / 86400000);
    if (diff <= 0) return "сегодня"; if (diff === 1) return "вчера";
    if (diff < 7) return diff + " " + plural(diff, "день", "дня", "дней") + " назад";
    return d.getUTCDate() + " " + MONTHS[d.getUTCMonth()];
  }
  function renderHistory(history) {
    var mount = $("hist-mount");
    if (!history || !history.length) { mount.innerHTML = '<div class="hist-empty">Пока пусто — крутаней колесо.</div>'; return; }
    mount.innerHTML = '<div class="hist">' + history.map(function (h) {
      var win = h.kind === "rub" || h.kind === "extra_spin";
      var icon = h.kind === "extra_spin" ? "↻" : (h.kind === "rub" ? "₽" : "—");
      var label = h.kind === "rub" ? "+" + fmtRub(h.amount_rub) : (h.kind === "extra_spin" ? "доп. прокрутка" : "мимо");
      return '<div class="hrow"><div class="hi ' + (win ? "win" : "miss") + '">' + icon + "</div>" +
        '<div class="hv ' + (win ? "win" : "miss") + '">' + label + "</div>" +
        '<div class="hd">' + relDate(h.at_iso) + "</div></div>";
    }).join("") + "</div>";
  }
  function renderStatus(doc) {
    state.live = !!doc.fortune_live;
    state.available = doc.available_spins || 0;
    $("cnt").textContent = state.available;
    $("cnt-word").textContent = plural(state.available, "прокрутка", "прокрутки", "прокруток");
    var dn = doc.days_to_next_spin || 0;
    $("next-spin").innerHTML = state.available > 0
      ? "Доступна <b>сейчас</b> — крути!"
      : (dn > 0 ? "Следующая через <b>" + dn + " " + plural(dn, "активный день", "активных дня", "активных дней") + "</b>" : "");
    // total won from history (real ₽ credited via ledger)
    var won = (doc.history || []).reduce(function (s, h) { return s + (h.kind === "rub" ? (Number(h.amount_rub) || 0) : 0); }, 0);
    $("totalwin").textContent = fmtRub(won);
    $("spins-done").textContent = doc.spins_done || 0;
    renderHistory(doc.history);

    $("soon-chip").hidden = state.live;
    updateButton();
  }
  function updateButton() {
    var btn = $("spin"), label = $("spin-label");
    if (!state.live) { btn.disabled = true; label.textContent = "Скоро — в доработке"; return; }
    if (state.spinning) { btn.disabled = true; label.textContent = "Крутится…"; return; }
    if (state.available <= 0) { btn.disabled = true; label.textContent = "Нет прокруток"; return; }
    btn.disabled = false; label.textContent = "Крутить";
  }

  // ---------- spin ----------
  function loadStatus() {
    postJson(EP.status, identity()).then(function (r) { if (r.doc && r.doc.ok) renderStatus(r.doc); else softFail(r.doc); })
      .catch(function () { softFail(null); });
  }
  function softFail(doc) {
    state.live = false; $("soon-chip").hidden = false; updateButton();
    if (doc && doc.error === "needs_telegram_bind") $("next-spin").textContent = "Привяжи Telegram в кабинете";
  }
  function onSpin() {
    if (state.spinning || !state.live || state.available <= 0) return;
    state.spinning = true; updateButton();
    postJson(EP.spin, identity()).then(function (r) {
      var doc = r.doc || {};
      if (!doc.ok) { state.spinning = false; updateButton(); toastText(mapErr(doc)); return; }
      var idx = KEY_INDEX[doc.sector_key]; if (idx == null) idx = 0;
      animateTo(idx, function () {
        state.spinning = false;
        showResult(doc);
        loadStatus(); // refresh counters/history (and the credited balance is server-side)
      });
    }).catch(function () { state.spinning = false; updateButton(); toastText("Сеть недоступна"); });
  }
  function mapErr(doc) {
    var e = doc && doc.error;
    if (e === "fortune_disabled") return "Колесо в доработке";
    if (e === "no_spins") return "Нет прокруток";
    if (e === "needs_telegram_bind") return "Привяжи Telegram";
    return "Не получилось";
  }

  // ---------- boot ----------
  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}
    drawWheel();
    loadStatus();
    $("spin").addEventListener("click", onSpin);
    $("hub").addEventListener("click", onSpin);
    $("btn-back").addEventListener("click", function () {
      if (history.length > 1) history.back(); else window.location.href = "/portal/home.html";
    });
    var routes = { home: "/portal/home.html", access: "/portal/access.html", balance: "/portal/balance.html", referral: "/portal/referral.html", support: "/portal/support.html" };
    document.querySelectorAll(".nav a").forEach(function (a) {
      a.addEventListener("click", function () { var n = a.getAttribute("data-nav"); if (routes[n]) window.location.href = routes[n]; });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
