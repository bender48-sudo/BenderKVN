(function () {
  "use strict";

  const CONTENT_URL = "/portal/content/ru.json";
  const STATUS_JSON = "/api/ops/status.json";
  const STATUS_PATH = "/status";
  const SUPPORT_URL = "https://t.me/Bender_KVN_bot";
  const SETUP_PATH = "/setup/";
  const API_FUNNEL = "/setup/api/funnel-event";
  const API_CABINET = "/setup/api/cabinet";
  const API_TELEGRAM_SETUP = "/setup/api/telegram-setup";
  const ACK_KEY = "bvpn_vpn_config_ack";
  const SUB_URL_KEY = "bvpn_subscription_url";
  const CID_KEY = "bvpn_customer_id";
  const EMAIL_KEY = "bvpn_customer_email";

  let content = null;

  function $(id) {
    return document.getElementById(id);
  }

  function show(viewId) {
    document.querySelectorAll("[data-view]").forEach(function (el) {
      el.classList.toggle("hidden", el.getAttribute("data-view") !== viewId);
    });
  }

  function getTelegramWebApp() {
    return window.Telegram && window.Telegram.WebApp;
  }

  function getTelegramUserId() {
    var tg = getTelegramWebApp();
    if (tg) {
      var u = tg.initDataUnsafe && tg.initDataUnsafe.user;
      if (u && u.id) return u.id;
      try {
        var idp = new URLSearchParams(tg.initData || "");
        var uj = idp.get("user");
        if (uj) {
          var parsed = JSON.parse(uj);
          if (parsed && parsed.id) return parsed.id;
        }
      } catch (e) {
        /* ignore */
      }
    }
    var params = new URLSearchParams(window.location.search || "");
    var tid = parseInt(params.get("tid") || "0", 10);
    if (tid > 0) return tid;
    return 0;
  }

  function normalizeSubUrl(url) {
    var u = (url || "").trim();
    if (!u) return u;
    return u
      .replace("://p4n7q.conntest.xyz:2053", "://p4n7q.conntest.xyz:8443")
      .replace("://k9x2m1.conntest.xyz:2053", "://k9x2m1.conntest.xyz:8443");
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return Promise.reject(new Error("clipboard unavailable"));
  }

  function initTelegram() {
    var tg = getTelegramWebApp();
    if (!tg) return;
    document.documentElement.classList.add("tg-webapp");
    tg.ready();
    tg.expand();
    try {
      tg.enableClosingConfirmation();
    } catch (e) {
      /* older clients */
    }
    var tp = tg.themeParams || {};
    var cssMap = {
      bg_color: "--bg",
      text_color: "--text",
      hint_color: "--muted",
      secondary_bg_color: "--bg-card",
    };
    Object.keys(cssMap).forEach(function (key) {
      if (tp[key]) {
        document.documentElement.style.setProperty(cssMap[key], tp[key]);
      }
    });
    if (typeof tg.setHeaderColor === "function" && tp.bg_color) {
      try {
        tg.setHeaderColor(tp.bg_color);
      } catch (e) {
        /* ignore */
      }
    }
    if (typeof tg.setBackgroundColor === "function" && tp.bg_color) {
      try {
        tg.setBackgroundColor(tp.bg_color);
      } catch (e) {
        /* ignore */
      }
    }
  }

  function openExternal(url) {
    var u = (url || "").trim();
    if (!u) return;
    var tg = getTelegramWebApp();
    if (tg) {
      if (
        /^https?:\/\/(t\.me|telegram\.me)\//i.test(u) &&
        typeof tg.openTelegramLink === "function"
      ) {
        tg.openTelegramLink(u);
        return;
      }
      if (typeof tg.openLink === "function") {
        tg.openLink(u);
        return;
      }
    }
    window.open(u, "_blank", "noopener");
  }

  function trackFunnel(event) {
    try {
      fetch(API_FUNNEL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: event }),
        keepalive: true,
      }).catch(function () {});
    } catch (e) {
      /* ignore */
    }
  }

  function bindExternalLink(el) {
    if (!el || el.dataset.bvpnBound === "1") return;
    el.dataset.bvpnBound = "1";
    el.addEventListener("click", function (ev) {
      var href = (el.getAttribute("href") || "").trim();
      if (!href || href === "#") return;
      if (getTelegramWebApp()) {
        ev.preventDefault();
        openExternal(href);
      }
    });
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (j) {
        return { code: r.status, body: j };
      });
    });
  }

  function openTelegramSetup(ev) {
    if (ev) ev.preventDefault();
    var tid = getTelegramUserId();
    if (!getTelegramWebApp() && tid <= 0) {
      window.location.href = SETUP_PATH;
      return;
    }
    trackFunnel("portal_tg_setup");
    if (!tid) {
      window.alert(
        "Не удалось определить Telegram. Закройте Mini App и откройте снова из бота."
      );
      return;
    }
    postJson(API_TELEGRAM_SETUP, { telegram_id: tid })
      .then(function (res) {
        if (res.body && res.body.sub_url) {
          try {
            localStorage.setItem(SUB_URL_KEY, normalizeSubUrl(res.body.sub_url));
          } catch (e) {
            /* ignore */
          }
        }
        if (res.body && res.body.ok && res.body.setup_page_url) {
          if (getTelegramWebApp()) {
            window.location.href = res.body.setup_page_url;
          } else {
            openExternal(res.body.setup_page_url);
          }
          return;
        }
        var msg =
          (res.body && res.body.message) ||
          (content.setup && content.setup.error_no_subscription) ||
          "Сначала получите доступ в боте.";
        if (res.body && res.body.bot_url) {
          if (getTelegramWebApp()) {
            openExternal(res.body.bot_url);
          } else {
            window.location.href = res.body.bot_url;
          }
        }
        window.alert(msg);
      })
      .catch(function () {
        window.alert(content.errors.generic);
      });
  }

  function bindSetupEntryButtons() {
    ["btn-setup", "btn-cabinet-setup"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      el.addEventListener("click", function (ev) {
        if (getTelegramWebApp() || getTelegramUserId() > 0) {
          openTelegramSetup(ev);
        }
      });
    });
  }

  function readAckGeneration() {
    try {
      var raw = localStorage.getItem(ACK_KEY);
      if (raw === null || raw === "") return 0;
      return parseInt(raw, 10) || 0;
    } catch (e) {
      return 0;
    }
  }

  function writeAckGeneration(gen) {
    try {
      localStorage.setItem(ACK_KEY, String(gen));
    } catch (e) {
      /* private mode */
    }
  }

  function setEventsState(mode, ev) {
    var pill = $("events-pill");
    var detail = $("events-detail");
    var steps = $("events-steps");
    var ackBtn = $("btn-events-ack");
    if (!pill || !detail || !ev) return;

    pill.className = "events-pill";
    steps.classList.add("hidden");
    ackBtn.classList.add("hidden");

    if (mode === "ok") {
      pill.classList.add("events-pill--ok");
      pill.textContent = ev.ok_pill;
      detail.textContent = ev.ok_detail;
    } else if (mode === "refresh") {
      pill.classList.add("events-pill--action");
      pill.textContent = ev.refresh_pill;
      detail.textContent = ev.refresh_detail;
      steps.classList.remove("hidden");
      steps.innerHTML = "";
      (ev.refresh_steps || []).forEach(function (t) {
        var li = document.createElement("li");
        li.textContent = t;
        steps.appendChild(li);
      });
      ackBtn.classList.remove("hidden");
    } else if (mode === "incident") {
      pill.classList.add("events-pill--incident");
      pill.textContent = ev.incident_pill;
      detail.textContent = ev.incident_detail;
    }
  }

  function loadEvents() {
    var ev = content.events || {};
    $("events-title").textContent = ev.title || "Обновления VPN";
    $("btn-events-ack").textContent = ev.refresh_ack || "Я обновил в Happ";
    var more = $("btn-events-more");
    more.textContent = ev.more || content.buttons.status;
    more.href = STATUS_PATH;
    bindExternalLink(more);
    bindExternalLink($("nav-status-link"));

    fetch(STATUS_JSON)
      .then(function (r) {
        if (!r.ok) throw new Error("status json");
        return r.json();
      })
      .then(function (doc) {
        var cfg = doc.vpn_config || {};
        var gen = parseInt(cfg.generation, 10) || 0;
        var ack = readAckGeneration();
        var overall = doc.overall || "ok";

        if (overall !== "ok") {
          setEventsState("incident", ev);
          return;
        }
        if (gen > 0 && gen > ack) {
          setEventsState("refresh", ev);
          return;
        }
        setEventsState("ok", ev);
      })
      .catch(function () {
        setEventsState("ok", ev);
      });
  }

  function renderHome() {
    var home = content.home;
    var tg = getTelegramWebApp();
    $("page-title").textContent = home.title;
    if ($("hero-badge") && home.hero_badge) {
      $("hero-badge").textContent = tg && home.hero_badge_tg
        ? home.hero_badge_tg
        : home.hero_badge;
    }
    var sub = $("page-subtitle");
    if (sub) {
      sub.textContent = tg
        ? home.subtitle_tg || home.hero_mono || home.subtitle || ""
        : home.hero_mono || home.subtitle || "";
    }
    var stack = $("hero-stack");
    if (stack && home.features && home.features.length) {
      stack.innerHTML = "";
      home.features.forEach(function (label) {
        var li = document.createElement("li");
        li.textContent = label;
        stack.appendChild(li);
      });
    }
    $("devices-note").textContent = home.devices_note;
    var cabBtn = $("btn-cabinet");
    if (cabBtn) cabBtn.textContent = content.buttons.cabinet || "Личный кабинет";
    $("btn-connect").textContent = content.buttons.connect;
    var setupBtn = $("btn-setup");
    if (setupBtn && content.buttons.setup_browser) {
      if (tg) {
        setupBtn.textContent = content.buttons.setup_tg || "Моя настройка VPN";
        setupBtn.href = "#";
      } else {
        setupBtn.textContent = content.buttons.setup_browser;
        setupBtn.href = SETUP_PATH;
      }
    }
    var guideBtn = $("btn-guide");
    if (guideBtn && content.buttons.watch_guide) {
      guideBtn.textContent = content.buttons.watch_guide;
      guideBtn.href = "/portal/guide.html";
    }
    var supportBtn = $("btn-support");
    supportBtn.textContent = content.buttons.support;
    supportBtn.href = SUPPORT_URL;
    $("btn-stuck").textContent = content.buttons.stuck;
    var errBtn = $("btn-help-errors");
    if (errBtn && content.buttons.help_errors) {
      errBtn.textContent = content.buttons.help_errors;
    }
    var help = content.help || {};
    if ($("help-stuck-title") && help.stuck_title) {
      $("help-stuck-title").textContent = help.stuck_title;
    }
    if ($("help-stuck-steps") && help.stuck_steps) {
      var helpList = $("help-stuck-steps");
      helpList.innerHTML = "";
      help.stuck_steps.forEach(function (step) {
        var li = document.createElement("li");
        li.textContent = step;
        helpList.appendChild(li);
      });
    }
    $("tg-blocked-title").textContent = content.telegram_blocked.title;
    $("tg-blocked-body").textContent = content.telegram_blocked.body;
    $("happ-note").textContent = content.happ.phone_and_pc;
    loadEvents();
  }

  function renderDevices() {
    var screens = content.screens || {};
    if ($("devices-heading") && screens.devices_heading) {
      $("devices-heading").textContent = screens.devices_heading;
    }
    if ($("devices-lead") && screens.devices_lead) {
      $("devices-lead").textContent = screens.devices_lead;
    }
    var grid = $("device-grid");
    grid.innerHTML = "";
    content.devices.forEach(function (dev) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "device-card";
      btn.setAttribute("data-device-id", dev.id);
      btn.innerHTML =
        '<span class="icon" aria-hidden="true">' +
        dev.icon +
        "</span>" +
        dev.label;
      btn.setAttribute("role", "listitem");
      btn.setAttribute("aria-label", dev.label);
      btn.addEventListener("click", function () {
        try {
          history.replaceState(null, "", "#device=" + dev.id);
        } catch (e) {
          window.location.hash = "device=" + dev.id;
        }
        trackFunnel("portal_device_" + dev.id);
        showDeviceDetail(dev.id);
      });
      grid.appendChild(btn);
    });
  }

  function readStoredSubscriptionUrl() {
    try {
      return (localStorage.getItem(SUB_URL_KEY) || "").trim();
    } catch (e) {
      return "";
    }
  }

  function renderDeviceSubscriptionQr(subUrl) {
    var panel = $("device-qr-panel");
    var canvas = $("device-sub-qr");
    var missing = $("device-qr-missing");
    var qrCopy = (content && content.device_qr) || {};
    if ($("device-qr-title")) {
      $("device-qr-title").textContent = qrCopy.title || "QR для Happ";
    }
    if ($("device-qr-hint")) {
      $("device-qr-hint").textContent = qrCopy.hint || "";
    }
    if (!panel || !canvas) return;
    panel.classList.remove("hidden");
    if (!subUrl) {
      if (canvas) canvas.classList.add("hidden");
      if (missing) {
        missing.textContent =
          qrCopy.missing ||
          "Сначала получите настройку на странице «Получить бесплатный VPN».";
        missing.classList.remove("hidden");
      }
      return;
    }
    if (canvas) canvas.classList.remove("hidden");
    if (missing) missing.classList.add("hidden");
    if (window.QRCode) {
      QRCode.toCanvas(
        canvas,
        subUrl,
        { width: 220, margin: 2, color: { dark: "#e85d04", light: "#ffffff" } },
        function () {}
      );
    }
  }

  function showDeviceDetail(deviceId) {
    var dev = content.devices.find(function (d) {
      return d.id === deviceId;
    });
    if (!dev) return;
    renderDeviceSubscriptionQr(readStoredSubscriptionUrl());
    var screens = content.screens || {};
    if ($("install-steps-title") && screens.install_steps_title) {
      $("install-steps-title").textContent = screens.install_steps_title;
    }
    if ($("after-title") && screens.after_title) {
      $("after-title").textContent = screens.after_title;
    }
    $("device-detail-title").textContent = dev.install_title;
    var list = $("device-install-steps");
    list.innerHTML = "";
    var storeKey = dev.install_store_key || dev.id;
    var stores = content.happ_install || {};
    var store = stores[storeKey] || stores.generic;
    var steps = (dev.install_steps || []).slice(0, 3);
    steps.forEach(function (step, idx) {
      var li = document.createElement("li");
      li.textContent = step;
      if (idx === 0 && store) {
        var a = document.createElement("a");
        a.className = "store-link";
        a.href = store.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "↓ " + store.label;
        li.appendChild(document.createElement("br"));
        li.appendChild(a);
      }
      list.appendChild(li);
    });
    if (dev.alt_client && dev.id === "windows") {
      var note = document.createElement("p");
      note.className = "muted";
      note.textContent = dev.alt_client;
      list.parentElement.appendChild(note);
    }
    var after = $("after-device-steps");
    after.innerHTML = "";
    (content.steps.after_device || []).slice(0, 2).forEach(function (step) {
      var li = document.createElement("li");
      li.textContent = step;
      after.appendChild(li);
    });
    show("device");
  }

  function renderCabinet() {
    var cab = content.cabinet || {};
    var tg = getTelegramWebApp();
    $("cabinet-title").textContent = cab.title || "Личный кабинет";
    $("cabinet-lead").textContent = tg ? cab.lead_tg : cab.lead_web;
    $("cabinet-balance-label").textContent = cab.balance_label || "Баланс";
    $("cabinet-balance").textContent = cab.balance_na || "—";
    $("cabinet-balance-hint").textContent = cab.balance_hint || "";
    if ($("cabinet-customer-id-label")) {
      $("cabinet-customer-id-label").textContent = cab.customer_id_label || "BVPN-ID";
    }
    if ($("cabinet-email-label")) {
      $("cabinet-email-label").textContent = cab.email_label || "Email";
    }
    if ($("btn-cabinet-load")) {
      $("btn-cabinet-load").textContent = cab.load_balance || "Показать баланс";
    }
    if ($("cabinet-web-notify")) {
      $("cabinet-web-notify").textContent = cab.web_notify_lead || "";
    }
    $("btn-cabinet-bot").textContent = cab.open_bot || "Открыть бота";
    if (tg) {
      $("btn-cabinet-setup").textContent =
        cab.setup_tg || content.buttons.setup_tg || "QR для Happ";
      $("btn-cabinet-setup").href = "#";
    } else {
      $("btn-cabinet-setup").textContent = content.buttons.setup_browser;
      $("btn-cabinet-setup").href = SETUP_PATH;
    }
    var bindBtn = $("btn-cabinet-bind");
    if (bindBtn) {
      bindBtn.textContent = cab.bind_tg || "Привязать Telegram";
    }
    bindExternalLink($("btn-cabinet-bot"));
    bindExternalLink(bindBtn);
    try {
      var cid = localStorage.getItem(CID_KEY) || "";
      var em = localStorage.getItem(EMAIL_KEY) || "";
      if ($("cabinet-customer-id") && cid) $("cabinet-customer-id").value = cid;
      if ($("cabinet-email") && em) $("cabinet-email").value = em;
    } catch (e) {
      /* ignore */
    }
    if (tg) {
      var login = $("cabinet-login-panel");
      if (login) login.classList.add("hidden");
    }
  }

  function showCabinetError(msg) {
    var err = $("cabinet-load-error");
    var lead = $("cabinet-lead");
    if (err) {
      err.textContent = msg;
      err.classList.remove("hidden");
    }
    if (lead && getTelegramWebApp()) {
      lead.textContent = msg;
    }
    var panel = $("cabinet-balance-panel");
    if (panel) panel.classList.add("hidden");
  }

  function applyCabinetData(doc) {
    var cab = content.cabinet || {};
    var balEl = $("cabinet-balance");
    var panel = $("cabinet-balance-panel");
    var err = $("cabinet-load-error");
    if (err) err.classList.add("hidden");
    if (!doc || !doc.ok) {
      var msg =
        (doc && doc.message) ||
        (getTelegramWebApp()
          ? "Аккаунт не найден. Нажмите /start в боте и попробуйте снова."
          : "Не найдено. Проверьте email или BVPN-ID.");
      showCabinetError(msg);
      if (doc && doc.bot_url) {
        var bindBtn = $("btn-cabinet-bind");
        if (bindBtn) {
          bindBtn.href = doc.bot_url;
          bindBtn.textContent = content.cabinet.open_bot || "Открыть бота";
          bindBtn.classList.remove("hidden");
        }
      }
      return;
    }
    var fmt = cab.balance_format || "{balance} ₽ · ~{days} дн.";
    balEl.textContent = fmt
      .replace("{balance}", String(Math.round(doc.balance_rub)))
      .replace("{days}", String(doc.days_left));
    if (doc.days_left <= 3) {
      balEl.classList.add("cabinet-balance--low");
    }
    if (panel) panel.classList.remove("hidden");
    var botBtn = $("btn-cabinet-bot");
    if (botBtn && doc.bot_url) {
      botBtn.href = doc.bot_url;
    }
    var bindBtn = $("btn-cabinet-bind");
    if (bindBtn) {
      var bindHref = "";
      try {
        bindHref = localStorage.getItem("bvpn_bind_url") || "";
      } catch (e) {
        bindHref = "";
      }
      if (bindHref && !doc.telegram_bound) {
        bindBtn.href = bindHref;
        bindBtn.classList.remove("hidden");
      } else if (doc.needs_telegram_bind && !doc.telegram_bound) {
        bindBtn.classList.add("hidden");
      } else {
        bindBtn.classList.add("hidden");
      }
    }
    try {
      if (doc.customer_id) localStorage.setItem(CID_KEY, doc.customer_id);
    } catch (e) {
      /* ignore */
    }
  }

  function showCabinetLoading() {
    var panel = $("cabinet-balance-panel");
    var balEl = $("cabinet-balance");
    var err = $("cabinet-load-error");
    if (err) err.classList.add("hidden");
    if (panel) panel.classList.remove("hidden");
    if (balEl) balEl.textContent = "…";
  }

  function loadCabinetBalanceAttempt(retry) {
    var tg = getTelegramWebApp();
    if (tg) {
      var uid = getTelegramUserId();
      if (!uid && retry < 8) {
        setTimeout(function () {
          loadCabinetBalanceAttempt(retry + 1);
        }, 120);
        return;
      }
      if (!uid) {
        showCabinetError("Не удалось определить пользователя. Закройте Mini App и откройте снова из бота.");
        return;
      }
      showCabinetLoading();
      trackFunnel("portal_cabinet_load_tg");
      fetch(API_CABINET, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: uid }),
      })
        .then(function (r) {
          return r.json().then(function (j) {
            return { status: r.status, body: j };
          });
        })
        .then(function (res) {
          if (res.body && res.body.ok) {
            applyCabinetData(res.body);
            return;
          }
          applyCabinetData(
            res.body || {
              ok: false,
              message:
                res.status === 502
                  ? "Сервис кабинета временно недоступен. Попробуйте через минуту."
                  : "Аккаунт не найден. Нажмите /start в боте и откройте кабинет снова.",
            }
          );
        })
        .catch(function () {
          applyCabinetData({ ok: false, message: content.errors.generic });
        });
      return;
    }
    var cid = ($("cabinet-customer-id") && $("cabinet-customer-id").value) || "";
    var email = ($("cabinet-email") && $("cabinet-email").value) || "";
    try {
      if (email) localStorage.setItem(EMAIL_KEY, email.trim());
    } catch (e) {
      /* ignore */
    }
    trackFunnel("portal_cabinet_load");
    fetch(API_CABINET, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: cid.trim(),
        email: email.trim(),
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(applyCabinetData)
      .catch(function () {
        applyCabinetData({ ok: false });
      });
  }

  function loadCabinetBalance() {
    loadCabinetBalanceAttempt(0);
  }

  function resolveRouteView() {
    if (window.BVPN_INITIAL_VIEW) {
      return String(window.BVPN_INITIAL_VIEW).trim();
    }
    var path = (window.location.pathname || "").toLowerCase();
    if (path.indexOf("cabinet.html") >= 0) return "cabinet";
    var params = new URLSearchParams(window.location.search || "");
    var view = (params.get("view") || "").trim();
    if (view) return view;
    var raw = (window.location.hash || "").replace(/^#/, "").trim();
    if (raw) return raw;
    var tg = getTelegramWebApp();
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) {
      return String(tg.initDataUnsafe.start_param).trim();
    }
    return "";
  }

  function openCabinetView() {
    renderCabinet();
    show("cabinet");
    trackFunnel("portal_view_cabinet");
    loadCabinetBalance();
  }

  function applyRouteFromHash() {
    var raw = resolveRouteView();
    if (raw === "cabinet") {
      openCabinetView();
      return;
    }
    if (raw === "devices" || raw === "connect") {
      show("devices");
      trackFunnel("portal_view_devices");
      return;
    }
    var dm = raw.match(/^device=(iphone|android|windows|mac)$/);
    if (dm) {
      showDeviceDetail(dm[1]);
      return;
    }
    if (/^(iphone|android|windows|mac)$/.test(raw)) {
      showDeviceDetail(raw);
      return;
    }
    show("home");
  }

  function bindActions() {
    var cabBtn = $("btn-cabinet");
    if (cabBtn) {
      cabBtn.addEventListener("click", function () {
        try {
          history.replaceState(null, "", "?view=cabinet");
        } catch (e) {
          window.location.search = "?view=cabinet";
        }
        openCabinetView();
      });
    }
    var loadBal = $("btn-cabinet-load");
    if (loadBal) {
      loadBal.addEventListener("click", loadCabinetBalance);
    }
    var backCab = $("btn-back-home-cabinet");
    if (backCab) {
      backCab.addEventListener("click", function () {
        window.location.href = "/portal/";
      });
    }
    var btnConnect = $("btn-connect");
    if (btnConnect) btnConnect.addEventListener("click", function () {
      try {
        history.replaceState(null, "", "#devices");
      } catch (e) {
        window.location.hash = "devices";
      }
      show("devices");
      trackFunnel("portal_view_devices");
    });
    var btnBackHome = $("btn-back-home");
    if (btnBackHome) {
      btnBackHome.addEventListener("click", function () {
        show("home");
      });
    }
    var btnBackDevices = $("btn-back-devices");
    if (btnBackDevices) {
      btnBackDevices.addEventListener("click", function () {
        show("devices");
      });
    }
    var btnStuck = $("btn-stuck");
    if (btnStuck) btnStuck.addEventListener("click", function () {
      var helpPanel = $("help-stuck");
      if (helpPanel) {
        helpPanel.classList.toggle("hidden");
        if (!helpPanel.classList.contains("hidden")) {
          helpPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }
    });
    bindExternalLink($("btn-support"));
    bindExternalLink($("btn-device-support"));

    var btnEventsAck = $("btn-events-ack");
    if (btnEventsAck) btnEventsAck.addEventListener("click", function () {
      fetch(STATUS_JSON)
        .then(function (r) {
          return r.json();
        })
        .then(function (doc) {
          var gen = parseInt((doc.vpn_config || {}).generation, 10) || 0;
          writeAckGeneration(gen > 0 ? gen : 1);
          setEventsState("ok", content.events || {});
          $("events-card").scrollIntoView({ behavior: "smooth", block: "nearest" });
        })
        .catch(function () {
          writeAckGeneration(1);
          setEventsState("ok", content.events || {});
        });
    });
  }

  function showError(msg) {
    $("load-error").textContent = msg || content.errors.generic;
    $("load-error").classList.remove("hidden");
  }

  window.bvpnCopyText = copyToClipboard;

  fetch(CONTENT_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("content load failed");
      return r.json();
    })
    .then(function (data) {
      content = data;
      initTelegram();
      if ($("hero-badge")) renderHome();
      if ($("device-grid")) renderDevices();
      renderCabinet();
      bindActions();
      bindSetupEntryButtons();
      applyRouteFromHash();
      if (resolveRouteView() !== "cabinet") {
        trackFunnel("portal_view_home");
      }
    })
    .catch(function () {
      showError(
        "Не удалось загрузить тексты. Откройте страницу через веб-сервер или с продакшн-домена."
      );
    });
})();
