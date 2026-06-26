/* BenderVPN Mini App — Support tickets (MINI-APP-BUILD-001, P4).
 *
 * Honest-UI: list, thread, statuses, unread all come from the ticket API. Gated by the server
 * (support_live): when off → honest "скоро" empty state + help@ fallback, new/send disabled.
 * Status: waiting→Ждёт ответа (yellow) · answered→Ответ есть (green) · closed→Закрыто (grey).
 *
 * Endpoints: POST {BASE}/tickets · /ticket-get · /ticket · /ticket-message · /unread
 * Views (one page): list · thread(?ticket=ID) · new(?new=1[&subject=]).
 */
(function () {
  "use strict";
  var BASE = window.BVPN_API_BASE || "/setup/api";
  var EP = {
    list: BASE + "/tickets", get: BASE + "/ticket-get", create: BASE + "/ticket",
    message: BASE + "/ticket-message", unread: BASE + "/unread",
  };
  var SUPPORT_EMAIL = "help@bendervpn.io";
  var TOPICS = [
    { id: "connection", label: "Подключение" }, { id: "payment", label: "Оплата" },
    { id: "devices", label: "Устройства" }, { id: "other", label: "Другое" },
  ];

  var state = { live: false, view: "list", subject: "connection", currentTicket: null };

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
  var MONTHS = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso); if (isNaN(d.getTime())) return "";
    var now = new Date();
    var a = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
    var b = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    var diff = Math.round((b - a) / 86400000);
    var hm = String(d.getUTCHours()).padStart(2, "0") + ":" + String(d.getUTCMinutes()).padStart(2, "0");
    if (diff <= 0) return "сегодня, " + hm;
    if (diff === 1) return "вчера, " + hm;
    return d.getUTCDate() + " " + MONTHS[d.getUTCMonth()];
  }
  function fmtTime(iso) {
    if (!iso) return "";
    var d = new Date(iso); if (isNaN(d.getTime())) return "";
    return String(d.getUTCHours()).padStart(2, "0") + ":" + String(d.getUTCMinutes()).padStart(2, "0");
  }
  function statusInfo(s) {
    if (s === "answered") return { cls: "answered", label: "Ответ есть" };
    if (s === "closed") return { cls: "closed", label: "Закрыто" };
    return { cls: "open", label: "Ждёт ответа" };
  }
  function toast(msg) {
    var t = $("toast"); if (!t) return;
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }
  function copyEmail() {
    var done = function () { toast("Почта скопирована: " + SUPPORT_EMAIL); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(SUPPORT_EMAIL).then(done, done);
    else { window.location.href = "mailto:" + SUPPORT_EMAIL; }
  }

  // ---------- view switching ----------
  function show(view) {
    state.view = view;
    $("screen-list").hidden = view !== "list";
    $("screen-thread").hidden = view !== "thread";
    $("screen-new").hidden = view !== "new";
    $("bottom-nav").hidden = view !== "list";
    $("composer").hidden = view !== "thread";
    $("scroll").scrollTop = view === "thread" ? 999999 : 0;
  }

  // ---------- list ----------
  function loadList() {
    postJson(EP.list, identity()).then(function (r) {
      var doc = r.doc || {};
      state.live = !!doc.support_live;
      renderList(doc);
    }).catch(function () { renderList({ ok: false }); });
    refreshBell();
  }
  function renderList(doc) {
    var mount = $("list-mount");
    var tickets = (doc && doc.tickets) || [];
    $("btn-new").disabled = !state.live;
    if (!state.live) {
      mount.innerHTML = '<div class="empty">Обращения в приложении скоро заработают.<br>Пока напиши нам на почту ниже — ответим там же.</div>';
      return;
    }
    if (doc.needs_telegram_bind) {
      mount.innerHTML = '<div class="empty">Привяжи Telegram в кабинете, чтобы вести обращения здесь.</div>';
      return;
    }
    if (!tickets.length) {
      mount.innerHTML = '<div class="empty">Обращений пока нет. Нажми «Новое обращение», если нужна помощь.</div>';
      return;
    }
    mount.innerHTML = tickets.map(function (t) {
      var st = statusInfo(t.status);
      var unread = (t.unread || 0) > 0;
      var last = t.last_message ? esc(t.last_message) : "";
      return '<button class="ticket' + (unread ? " has-unread" : "") + '" data-id="' + t.id + '">' +
        (unread ? '<span class="t-unread"></span>' : "") +
        '<div class="t-top"><span class="t-id">' + esc(t.number || ("#" + t.id)) + "</span>" +
        '<span class="t-status ' + st.cls + '">' + st.label + "</span></div>" +
        '<div class="t-subj">' + esc(subjectLabel(t.subject)) + "</div>" +
        (last ? '<div class="t-last">' + last + "</div>" : "") +
        '<div class="t-date">' + esc(fmtDate(t.last_message_at_iso)) + "</div></button>";
    }).join("");
    mount.querySelectorAll(".ticket").forEach(function (b) {
      b.addEventListener("click", function () { openThread(parseInt(b.getAttribute("data-id"), 10)); });
    });
  }
  function subjectLabel(id) {
    var t = TOPICS.filter(function (x) { return x.id === id; })[0];
    if (t) return t.label;
    if (id === "partner_apply") return "Партнёрство";
    if (id === "partner_withdraw") return "Вывод средств";
    return "Обращение";
  }

  // ---------- thread ----------
  function openThread(ticketId) {
    show("thread");
    $("thread-mount").innerHTML = '<div class="sys-note">Загрузка…</div>';
    var body = identity(); body.ticket_id = ticketId;
    postJson(EP.get, body).then(function (r) {
      var doc = r.doc || {};
      if (!doc.ok) { toast("Не удалось открыть обращение"); show("list"); return; }
      state.currentTicket = doc.ticket;
      renderThread(doc);
      refreshBell();
    }).catch(function () { toast("Сеть недоступна"); show("list"); });
  }
  function renderThread(doc) {
    var t = doc.ticket, st = statusInfo(t.status);
    $("thread-title").textContent = subjectLabel(t.subject);
    $("thread-sub").textContent = (t.number || "#" + t.id) + " · " + st.label.toLowerCase();
    var html = (doc.messages || []).map(function (m) {
      if (m.sender === "system") return '<div class="sys-note">' + esc(m.body) + "</div>";
      var who = m.sender === "staff" ? "support" : "user";
      var label = m.sender === "staff" ? '<div class="who">Поддержка</div>' : "";
      return '<div class="msg ' + who + '">' + label + "<div>" + esc(m.body) + "</div>" +
        '<div class="time">' + esc(fmtTime(m.at_iso)) + "</div></div>";
    }).join("");
    $("thread-mount").innerHTML = html;
    var closed = t.status === "closed";
    $("composer-text").placeholder = closed ? "Обращение закрыто — напиши, чтобы открыть снова" : "Сообщение…";
    $("scroll").scrollTop = 999999;
  }
  function sendMessage() {
    var text = $("composer-text").value.trim();
    if (!text || !state.currentTicket) return;
    var btn = $("btn-send-msg"); btn.disabled = true;
    var body = identity(); body.ticket_id = state.currentTicket.id; body.text = text;
    postJson(EP.message, body).then(function (r) {
      btn.disabled = false;
      if (!(r.doc && r.doc.ok)) { toast(mapErr(r.doc)); return; }
      $("composer-text").value = "";
      openThread(state.currentTicket.id); // reload thread (now waiting)
    }).catch(function () { btn.disabled = false; toast("Сеть недоступна"); });
  }

  // ---------- new ticket ----------
  function openNew(prefillSubject, prefillText) {
    show("new");
    state.subject = prefillSubject && hasSubject(prefillSubject) ? prefillSubject : "connection";
    renderTopics();
    if (prefillText) $("new-text").value = prefillText;
    var em = identity().email || localStorage.getItem("bvpn_email") || "";
    if (em && !$("new-email").value) $("new-email").value = em;
  }
  function hasSubject(s) { return TOPICS.some(function (t) { return t.id === s; }) || s === "partner_apply" || s === "partner_withdraw"; }
  function renderTopics() {
    $("topics").innerHTML = TOPICS.map(function (t) {
      return '<span class="topic' + (t.id === state.subject ? " sel" : "") + '" data-id="' + t.id + '">' + esc(t.label) + "</span>";
    }).join("");
    $("topics").querySelectorAll(".topic").forEach(function (c) {
      c.addEventListener("click", function () {
        state.subject = c.getAttribute("data-id");
        $("topics").querySelectorAll(".topic").forEach(function (x) { x.classList.remove("sel"); });
        c.classList.add("sel");
      });
    });
  }
  function submitNew() {
    var text = $("new-text").value.trim();
    if (!text) { toast("Напиши, что случилось"); return; }
    var btn = $("btn-send-new"); btn.disabled = true;
    var body = identity();
    body.subject = state.subject; body.text = text;
    var em = $("new-email").value.trim(); if (em) body.email = em;
    postJson(EP.create, body).then(function (r) {
      btn.disabled = false;
      if (!(r.doc && r.doc.ok)) { toast(mapErr(r.doc)); return; }
      $("new-text").value = "";
      toast("Обращение " + (r.doc.number || "") + " создано");
      openThread(r.doc.ticket_id);
    }).catch(function () { btn.disabled = false; toast("Сеть недоступна"); });
  }
  function mapErr(doc) {
    var e = doc && doc.error;
    if (e === "support_disabled") return "Обращения скоро заработают";
    if (e === "needs_telegram_bind") return "Привяжи Telegram в кабинете";
    if (e === "empty_text") return "Напиши сообщение";
    if (e === "not_found") return "Обращение не найдено";
    return "Не удалось отправить";
  }

  // ---------- bell ----------
  function refreshBell() {
    postJson(EP.unread, identity()).then(function (r) {
      var n = (r.doc && r.doc.count) || 0;
      var dot = $("bell-dot");
      if (n > 0) { dot.textContent = n > 99 ? "99+" : n; dot.classList.add("show"); }
      else dot.classList.remove("show");
    }).catch(function () {});
  }

  // ---------- boot ----------
  function navTo(nav) {
    var routes = { home: "/portal/home.html", access: "/portal/access.html", balance: "/portal/balance.html", referral: "/portal/referral.html" };
    if (nav === "support") return;
    if (routes[nav]) window.location.href = routes[nav]; else toast("Скоро");
  }
  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}
    var p = new URLSearchParams(location.search);

    loadList();

    $("btn-new").addEventListener("click", function () { if (state.live) openNew(); else toast("Обращения скоро заработают"); });
    $("btn-home").addEventListener("click", function () { window.location.href = "/portal/home.html"; });
    $("btn-bell").addEventListener("click", function () { toast("Непрочитанные — в обращениях ниже"); });
    $("fallback").addEventListener("click", copyEmail);
    $("thread-back").addEventListener("click", function () { show("list"); loadList(); });
    $("new-back").addEventListener("click", function () { show("list"); loadList(); });
    $("btn-send-msg").addEventListener("click", sendMessage);
    $("btn-send-new").addEventListener("click", submitNew);
    $("composer-text").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    document.querySelectorAll(".nav a").forEach(function (a) {
      a.addEventListener("click", function () { navTo(a.getAttribute("data-nav")); });
    });

    // deep links: ?ticket=ID (open thread), ?new=1[&subject=&prefill=]
    var tk = parseInt(p.get("ticket") || "0", 10);
    if (tk > 0) openThread(tk);
    else if (p.get("new") === "1") openNew(p.get("subject"), p.get("prefill"));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
