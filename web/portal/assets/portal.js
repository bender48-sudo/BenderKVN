(function () {
  "use strict";

  const CONTENT_URL = "content/ru.json";
  const STATUS_PATH = "/status";
  const SUPPORT_URL = "https://t.me/Bender_KVN_bot";

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
      button_color: "--accent",
      button_text_color: "--text",
      secondary_bg_color: "--card",
    };
    Object.keys(cssMap).forEach(function (key) {
      if (tp[key]) {
        document.documentElement.style.setProperty(cssMap[key], tp[key]);
      }
    });
    var headerColor = tp.bg_color || "#0f1419";
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

  function renderHome() {
    var home = content.home;
    $("page-title").textContent = home.title;
    if ($("hero-badge") && home.hero_badge) {
      $("hero-badge").textContent = home.hero_badge;
    }
    $("page-subtitle").textContent = home.subtitle;
    var pills = $("feature-pills");
    if (pills && home.features && home.features.length) {
      pills.innerHTML = "";
      home.features.forEach(function (label) {
        var li = document.createElement("li");
        li.textContent = label;
        pills.appendChild(li);
      });
    }
    $("devices-note").textContent = home.devices_note;
    $("btn-connect").textContent = content.buttons.connect;
    $("btn-status").textContent = content.buttons.status;
    $("btn-support").textContent = content.buttons.support;
    $("btn-stuck").textContent = content.buttons.stuck;
    $("tg-blocked-title").textContent = content.telegram_blocked.title;
    $("tg-blocked-body").textContent = content.telegram_blocked.body;
    $("happ-note").textContent = content.happ.phone_and_pc;
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

  function showDeviceDetail(deviceId) {
    var dev = content.devices.find(function (d) {
      return d.id === deviceId;
    });
    if (!dev) return;
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
    dev.install_steps.forEach(function (step) {
      var li = document.createElement("li");
      li.textContent = step;
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

  function bindActions() {
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
      openExternal(SUPPORT_URL);
    });
    var statusBtn = $("btn-status");
    statusBtn.addEventListener("click", function (ev) {
      if (getTelegramWebApp()) {
        ev.preventDefault();
        openExternal(statusBtn.href);
      }
    });
    var supportBtn = $("btn-support");
    supportBtn.addEventListener("click", function (ev) {
      if (getTelegramWebApp()) {
        ev.preventDefault();
        openExternal(SUPPORT_URL);
      }
    });
    var deviceSupport = $("btn-device-support");
    if (deviceSupport) {
      deviceSupport.addEventListener("click", function (ev) {
        if (getTelegramWebApp()) {
          ev.preventDefault();
          openExternal(SUPPORT_URL);
        }
      });
    }
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
      bindActions();
      show("home");
    })
    .catch(function () {
      showError(
        "Не удалось загрузить тексты. Откройте страницу через веб-сервер или с продакшн-домена."
      );
    });
})();
