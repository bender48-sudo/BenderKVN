(function () {
  "use strict";

  var CONTENT_URL = "/portal/content/ru.json";

  function $(id) {
    return document.getElementById(id);
  }

  function pickDevice() {
    var p = new URLSearchParams(window.location.search).get("device") || "";
    if (p === "ios") return "iphone";
    if (p === "iphone" || p === "android") return p;
    return "iphone";
  }

  function mountMedia(container, spec) {
    if (!container || !spec) return;
    container.innerHTML = "";
    if (spec.mp4) {
      var video = document.createElement("video");
      video.className = "guide-video";
      video.controls = true;
      video.playsInline = true;
      video.preload = "metadata";
      if (spec.gif) video.poster = spec.gif;
      var src = document.createElement("source");
      src.src = spec.mp4;
      src.type = "video/mp4";
      video.appendChild(src);
      container.appendChild(video);
      return;
    }
    if (spec.gif) {
      var img = document.createElement("img");
      img.className = "guide-gif";
      img.src = spec.gif;
      img.alt = spec.alt || "";
      img.loading = "lazy";
      container.appendChild(img);
    }
  }

  function showTab(device) {
    var ios = device === "iphone";
    $("panel-ios").classList.toggle("hidden", !ios);
    $("panel-ios").hidden = !ios;
    $("panel-android").classList.toggle("hidden", ios);
    $("panel-android").hidden = ios;
    $("tab-ios").classList.toggle("guide-tab--active", ios);
    $("tab-android").classList.toggle("guide-tab--active", !ios);
    $("tab-ios").setAttribute("aria-selected", ios ? "true" : "false");
    $("tab-android").setAttribute("aria-selected", ios ? "false" : "true");
  }

  function bindTabs() {
    document.querySelectorAll(".guide-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var dev = btn.getAttribute("data-device");
        showTab(dev);
        if (history.replaceState) {
          history.replaceState(null, "", "?device=" + encodeURIComponent(dev));
        }
      });
    });
    showTab(pickDevice());
  }

  fetch(CONTENT_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("content");
      return r.json();
    })
    .then(function (data) {
      var v = data.setup_videos || {};
      $("guide-title").textContent = v.title || "Как подключить VPN";
      document.title = (v.title || "BenderVPN") + " — видео";
      $("guide-lead").textContent =
        v.lead || "Короткая инструкция для телефона. Работает без VPN.";
      $("tab-ios").textContent = v.ios_tab || "iPhone";
      $("tab-android").textContent = v.android_tab || "Android";
      $("guide-ios-caption").textContent = v.ios_caption || "";
      $("guide-android-caption").textContent = v.android_caption || "";
      if (v.setup_button && $("btn-guide-setup")) {
        $("btn-guide-setup").textContent = v.setup_button;
      }
      if (v.portal_button && $("btn-guide-portal")) {
        $("btn-guide-portal").textContent = v.portal_button;
      }

      mountMedia($("media-ios"), {
        mp4: v.media_ios_mp4 || "",
        gif: v.media_ios_gif,
        alt: v.ios_alt,
      });
      mountMedia($("media-android"), {
        mp4: v.media_android_mp4 || "",
        gif: v.media_android_gif,
        alt: v.android_alt,
      });
      bindTabs();
    })
    .catch(function () {
      $("guide-lead").textContent = "Не удалось загрузить тексты. Обновите страницу.";
    });
})();
