/* BenderVPN Mini App — Connect wizard (MINI-APP-BUILD-001, P-WIZARD).
 *
 * 4 steps: OS → app → import → done. The client chosen in step 2 is inherited by step 3
 * (instruction + one-tap), no switcher. The subscription URL is resolved in-app via
 * POST /setup/api/telegram-setup {telegram_id} -> {sub_url} (one link for all clients;
 * the edge does UA branching, G13). QR + copy work in any client; the one-tap
 * "Открыть в {client}" button appears ONLY for clients with a verified URL scheme.
 *
 * Honest-UI: store links and deep-link schemes are all verified (no fabricated incy://).
 * Step 4 "Не работает → обращение" is a placeholder toast until the ticket system (P4).
 */
(function () {
  "use strict";

  var API_TELEGRAM_SETUP = (window.BVPN_API_BASE || "/setup/api") + "/telegram-setup";

  // ---- verified client registry (stores + one-tap schemes; null scheme = QR/copy only) ----
  var HAPP = "happ://add/"; // verified iOS+Android+desktop one-tap
  var OS = {
    ios: {
      title: "iPhone", short: "iPhone", os_label: "iOS",
      sub: "Через него работает BenderVPN. Рекомендуем INCY — основной клиент с полной защитой.",
      note: "INCY сам выбирает сервер и держит соединение. В запасных приложениях сервер выбираешь вручную и переподключаешь, если какой-то стал нестабильным.",
      apps: [
        { id: "incy", name: "INCY", rec: true, sub: "Полная защита · App Store", scheme: null,
          store: "https://apps.apple.com/ru/app/incy/id6756943388" },
        { id: "v2ray", name: "V2Ray Client+", backup: true, sub: "App Store", scheme: null,
          store: "https://apps.apple.com/ru/app/v2ray-client/id6747379524" },
        { id: "izi", name: "Изи VPN", backup: true, sub: "App Store", scheme: null,
          store: "https://apps.apple.com/ru/app/изи-vpn/id6746414734" },
        { id: "happ", name: "Happ", backup: true, sub: "App Store", scheme: HAPP,
          store: "https://apps.apple.com/app/happ-proxy-utility/id6504287215" },
      ],
    },
    android: {
      title: "Android", short: "Android", os_label: "Android",
      sub: "Через него работает BenderVPN. Рекомендуем Happ — основной клиент с полной защитой.",
      note: "Happ сам выбирает сервер и держит соединение. В запасном приложении сервер выбираешь вручную.",
      apps: [
        { id: "happ", name: "Happ", rec: true, sub: "Полная защита · Google Play", scheme: HAPP,
          store: "https://play.google.com/store/apps/details?id=com.happproxy.happ" },
        { id: "v2raytun", name: "v2RayTun", backup: true, sub: "Google Play",
          scheme: "v2raytun://import/", schemeSuffix: "#BenderVPN",
          store: "https://play.google.com/store/apps/details?id=com.v2raytun.android" },
      ],
    },
    windows: {
      title: "Windows", short: "Windows", os_label: "Windows",
      sub: "На ПК работает через Happ. Скачай и установи — дальше добавим настройку.",
      note: "Happ сам выбирает сервер и держит соединение.",
      apps: [
        { id: "happ", name: "Happ для Windows", rec: true, sub: "Скачать · Windows", scheme: HAPP,
          store: "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe" },
      ],
    },
    macos: {
      title: "macOS", short: "Mac", os_label: "macOS",
      sub: "На Mac работает через Happ. Скачай и установи — дальше добавим настройку.",
      note: "Happ сам выбирает сервер и держит соединение.",
      apps: [
        { id: "happ", name: "Happ для Mac", rec: true, sub: "Скачать · Mac", scheme: HAPP,
          store: "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.macOS.universal.dmg" },
      ],
    },
  };

  var OS_ORDER = [
    { id: "ios", name: "iPhone / iPad", sub: "iOS", icon: "phone" },
    { id: "android", name: "Android", sub: "телефон / планшет", icon: "phone" },
    { id: "windows", name: "Windows", sub: "ПК / ноутбук", icon: "desktop" },
    { id: "macos", name: "macOS", sub: "Mac", icon: "desktop" },
  ];
  var ICON = {
    phone: '<rect x="6" y="2" width="12" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18" stroke-linecap="round"/>',
    desktop: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4" stroke-linecap="round"/>',
  };
  var ARR = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var DOWNLOAD = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  var state = { step: 1, os: null, app: null, subUrl: null, resolved: false };

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // ---------- identity / api ----------
  function tgWebApp() { return window.Telegram && window.Telegram.WebApp; }
  function telegramUserId() {
    var tg = tgWebApp();
    try { var u = tg && tg.initDataUnsafe && tg.initDataUnsafe.user; if (u && u.id) return parseInt(u.id, 10) || 0; } catch (e) {}
    var p = new URLSearchParams(location.search);
    return parseInt(p.get("tg") || "0", 10) || 0; // dev/staging override
  }
  function postJson(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().then(function (j) { return { status: r.status, doc: j }; }); });
  }
  function normalizeSubUrl(url) {
    var u = (url || "").trim();
    if (!u) return u;
    return u
      .replace("://p4n7q.conntest.xyz:2053", "://p4n7q.conntest.xyz:8443")
      .replace("://k9x2m1.conntest.xyz:2053", "://k9x2m1.conntest.xyz:8443");
  }
  function deepLink(app, subUrl) {
    if (!app || !app.scheme || !subUrl) return null;
    return app.scheme + normalizeSubUrl(subUrl) + (app.schemeSuffix || "");
  }

  function toast(msg) {
    var t = $("toast");
    if (!t) return;
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 2200);
  }
  function copyText(text, ok) {
    if (!text) return;
    var done = function () { toast(ok || "Скопировано"); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fb(text, done); });
    } else { fb(text, done); }
  }
  function fb(text, done) {
    try { var ta = document.createElement("textarea"); ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta); done(); }
    catch (e) { toast("Не удалось скопировать"); }
  }

  // ---------- step navigation ----------
  function showStep(n) {
    state.step = n;
    [1, 2, 3, 4].forEach(function (i) { $("step-" + i).hidden = i !== n; });
    for (var i = 0; i < 4; i++) {
      var seg = $("seg-" + i);
      seg.className = "seg" + (i < n - 1 ? " done" : i === n - 1 ? " cur" : "");
    }
    var titles = {
      1: "Подключение",
      2: "Подключение · " + (state.os ? OS[state.os].short : ""),
      3: "Подключение · " + (state.app ? state.app.name : ""),
      4: "Подключение",
    };
    $("tb-title").textContent = titles[n];
    document.querySelector(".scroll").scrollTop = 0;
  }

  function goBack() {
    if (state.step <= 1) { window.location.href = "/portal/home.html"; return; }
    showStep(state.step - 1);
  }

  // ---------- step 1: OS ----------
  function renderOsList() {
    var html = "";
    OS_ORDER.forEach(function (o) {
      html +=
        '<button class="opt" data-os="' + o.id + '">' +
        '<div class="oi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' + ICON[o.icon] + "</svg></div>" +
        "<div><div class=\"oh\">" + esc(o.name) + "</div><div class=\"os\">" + esc(o.sub) + "</div></div>" +
        '<div class="arr">' + ARR + "</div></button>";
    });
    $("os-list").innerHTML = html;
    $("os-list").querySelectorAll(".opt").forEach(function (b) {
      b.addEventListener("click", function () { selectOs(b.getAttribute("data-os")); });
    });
  }

  function selectOs(osId) {
    state.os = osId;
    state.app = null;
    renderAppList();
    showStep(2);
  }

  // ---------- step 2: app ----------
  function renderAppList() {
    var conf = OS[state.os];
    $("step2-sub").textContent = conf.sub;
    $("step2-note-text").textContent = conf.note;
    // default selection: recommended app
    var def = conf.apps.filter(function (a) { return a.rec; })[0] || conf.apps[0];
    state.app = def;

    var html = "";
    conf.apps.forEach(function (a) {
      var badge = a.rec ? '<span class="badge-rec">рекомендуем</span>'
        : a.backup ? '<span class="badge-bk">запасной</span>' : "";
      html +=
        '<button class="opt' + (a.rec ? " primary" : "") + (a === def ? " sel" : "") + '" data-app="' + a.id + '">' +
        '<div class="oi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' +
        "<div><div class=\"oh\">" + esc(a.name) + badge + "</div><div class=\"os\">" + esc(a.sub) + "</div></div>" +
        '<div class="arr">' + DOWNLOAD + "</div></button>";
    });
    $("app-list").innerHTML = html;
    $("app-list").querySelectorAll(".opt").forEach(function (b) {
      b.addEventListener("click", function () {
        var app = conf.apps.filter(function (x) { return x.id === b.getAttribute("data-app"); })[0];
        selectApp(app, b);
      });
    });
  }

  function selectApp(app, btn) {
    state.app = app;
    $("app-list").querySelectorAll(".opt").forEach(function (b) { b.classList.remove("sel"); });
    if (btn) btn.classList.add("sel");
    // open the verified store page in a new tab
    if (app.store) window.open(app.store, "_blank", "noopener");
  }

  // ---------- step 3: import ----------
  function resolveSub() {
    if (state.resolved) { renderImport(); return; }
    var tid = telegramUserId();
    if (!tid) {
      showStep(3); renderImportError(
        "Открой Mini App из Telegram-бота, чтобы подтянуть настройку.");
      return;
    }
    showStep(3);
    $("step3-body").hidden = true;
    $("step3-error").hidden = true;
    postJson(API_TELEGRAM_SETUP, { telegram_id: tid })
      .then(function (res) {
        var b = res.doc || {};
        if (b.ok && b.sub_url) {
          state.subUrl = normalizeSubUrl(b.sub_url);
          state.resolved = true;
          renderImport();
        } else {
          renderImportError(b.message || "Не удалось загрузить настройку. Попробуй позже.");
        }
      })
      .catch(function () { renderImportError("Сеть недоступна. Попробуй ещё раз."); });
  }

  function renderImportError(msg) {
    $("step3-body").hidden = true;
    $("step3-error").hidden = false;
    $("step3-error-text").textContent = msg;
  }

  function renderImport() {
    var app = state.app, name = app.name;
    $("step3-error").hidden = true;
    $("step3-body").hidden = false;
    $("step3-sub").textContent =
      "Открой " + name + " и добавь профиль — по QR или ссылке. Сервер BenderVPN Auto подтянется сам.";
    $("qr-head").textContent = "Отсканируй QR в " + name;
    $("qr-hint").textContent = "В " + name + ": «Добавить» → «Сканировать QR». Профиль BenderVPN Auto подтянется сам.";
    $("link-hint").textContent = "В " + name + ": «Добавить» → «Вставить из буфера».";
    $("sub-url").textContent = state.subUrl;
    $("sub-url").title = state.subUrl;

    // QR (real, from sub url)
    var canvas = $("wizard-qr");
    $("qr-fallback").hidden = true;
    if (window.QRCode && QRCode.toCanvas) {
      QRCode.toCanvas(canvas, state.subUrl, { width: 150, margin: 1, color: { dark: "#0A0E14", light: "#ffffff" } },
        function (err) { if (err) $("qr-fallback").hidden = false; });
    } else { $("qr-fallback").hidden = false; }

    // one-tap only for clients with a verified scheme; otherwise QR + copy (no fake button)
    var link = deepLink(app, state.subUrl);
    var openBtn = $("btn-open-client");
    if (link) {
      openBtn.hidden = false;
      openBtn.textContent = "Открыть в " + name;
      openBtn.href = link;
    } else {
      openBtn.hidden = true; // INCY / V2Ray Client+ / Изи — no public scheme; QR/copy only
    }
  }

  // ---------- step 4 ----------
  function renderDone() {
    $("step4-sub").textContent =
      "VPN подключён. Включи его в " + (state.app ? state.app.name : "приложении") + " одной кнопкой — и всё работает.";
    showStep(4);
  }

  // ---------- boot ----------
  function boot() {
    try { var tg = tgWebApp(); if (tg) { tg.ready && tg.ready(); tg.expand && tg.expand(); } } catch (e) {}
    renderOsList();
    showStep(1);

    $("btn-back").addEventListener("click", goBack);
    $("btn-step2-next").addEventListener("click", function () { resolveSub(); });
    $("btn-copy-sub").addEventListener("click", function () { copyText(state.subUrl, "Ссылка скопирована"); });
    $("btn-step3-next").addEventListener("click", renderDone);
    $("btn-home").addEventListener("click", function () { window.location.href = "/portal/home.html"; });
    $("btn-ticket").addEventListener("click", function () {
      // In-app tickets land with the support system (P4); placeholder until then.
      toast("Скоро — обращения через поддержку");
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
