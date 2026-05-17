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

  function initTelegram() {
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg) return;
    tg.ready();
    tg.expand();
    if (tg.themeParams && tg.themeParams.bg_color) {
      document.documentElement.style.setProperty(
        "--bg",
        tg.themeParams.bg_color
      );
    }
  }

  function renderHome() {
    var home = content.home;
    $("page-title").textContent = home.title;
    $("page-subtitle").textContent = home.subtitle;
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
      window.open(SUPPORT_URL, "_blank", "noopener");
    });
    var statusBtn = $("btn-status");
    statusBtn.href = STATUS_PATH;
    $("btn-support").href = SUPPORT_URL;
  }

  function showError(msg) {
    $("load-error").textContent = msg || content.errors.generic;
    $("load-error").classList.remove("hidden");
  }

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
