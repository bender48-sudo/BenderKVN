(function () {
  "use strict";

  const CONTENT_URL = "/portal/content/ru.json";
  const STATUS_JSON = "/api/ops/status.json";
  const STATUS_PATH = "/status";
  const SUPPORT_URL = "https://t.me/Bender_KVN_bot";
  const SETUP_PATH = "/setup/";
  const ACK_KEY = "bvpn_vpn_config_ack";
  const SUB_URL_KEY = "bvpn_subscription_url";

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
    var headerColor = tp.bg_color || "#000000";
    if (typeof tg.setHeaderColor === "function") {
      try {
        tg.setHeaderColor(headerColor);
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
    var tg = getTelegramWebApp();
    if (tg && typeof tg.openLink === "function") {
      tg.openLink(url);
      return;
    }
    window.open(url, "_blank", "noopener");
  }

  function bindExternalLink(el) {
    if (!el) return;
    el.addEventListener("click", function (ev) {
      if (getTelegramWebApp()) {
        ev.preventDefault();
        openExternal(el.href);
      }
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
    $("page-title").textContent = home.title;
    if ($("hero-badge") && home.hero_badge) {
      $("hero-badge").textContent = home.hero_badge;
    }
    var sub = $("page-subtitle");
    if (sub) {
      sub.textContent = home.hero_mono || home.subtitle || "";
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
      setupBtn.textContent = content.buttons.setup_browser;
      setupBtn.href = SETUP_PATH;
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
      btn.addEventListener("click", function () {
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
    dev.install_steps.forEach(function (step, idx) {
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
    var after = $("after-device-steps");
    after.innerHTML = "";
    content.steps.after_device.forEach(function (step) {
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
    $("btn-cabinet-bot").textContent = cab.open_bot || "Открыть бота";
    $("btn-cabinet-setup").textContent = content.buttons.setup_browser;
    bindExternalLink($("btn-cabinet-bot"));
    bindExternalLink($("btn-cabinet-setup"));
  }

  function applyRouteFromHash() {
    var raw = (window.location.hash || "").replace(/^#/, "").trim();
    if (raw === "cabinet") {
      renderCabinet();
      show("cabinet");
      return;
    }
    if (raw === "devices" || raw === "connect") {
      show("devices");
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
        renderCabinet();
        show("cabinet");
      });
    }
    var backCab = $("btn-back-home-cabinet");
    if (backCab) backCab.addEventListener("click", function () { show("home"); });
    $("btn-connect").addEventListener("click", function () {
      show("devices");
    });
    $("btn-back-home").addEventListener("click", function () {
      show("home");
    });
    $("btn-back-devices").addEventListener("click", function () {
      show("devices");
    });
    $("btn-stuck").addEventListener("click", function () {
      var helpPanel = $("help-stuck");
      if (helpPanel) {
        helpPanel.classList.toggle("hidden");
        if (!helpPanel.classList.contains("hidden")) {
          helpPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }
    });
    bindExternalLink($("btn-support"));
    bindExternalLink($("btn-setup"));
    bindExternalLink($("btn-device-support"));

    $("btn-events-ack").addEventListener("click", function () {
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
      renderHome();
      renderDevices();
      renderCabinet();
      bindActions();
      applyRouteFromHash();
    })
    .catch(function () {
      showError(
        "Не удалось загрузить тексты. Откройте страницу через веб-сервер или с продакшн-домена."
      );
    });
})();
