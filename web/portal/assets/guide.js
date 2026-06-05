(function () {
  "use strict";

  var CONTENT_URL = "/portal/content/ru.json";
  var devices = [];
  var activeId = "iphone";

  function $(id) {
    return document.getElementById(id);
  }

  function pickDevice() {
    var p = new URLSearchParams(window.location.search).get("device") || "";
    if (p === "ios") return "iphone";
    if (["iphone", "android", "windows", "mac"].indexOf(p) >= 0) return p;
    return "iphone";
  }

  function storeForDevice(dev) {
    var key = dev.install_store_key || dev.id;
    return (window._guideContent && window._guideContent.happ_install || {})[key] || null;
  }

  function renderDeviceTabs() {
    var wrap = $("guide-device-tabs");
    if (!wrap) return;
    wrap.innerHTML = "";
    devices.forEach(function (dev) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "device-card" + (dev.id === activeId ? " device-card--active" : "");
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", dev.id === activeId ? "true" : "false");
      btn.setAttribute("data-device-id", dev.id);
      btn.innerHTML =
        '<span class="icon" aria-hidden="true">' + dev.icon + "</span>" + dev.label;
      btn.addEventListener("click", function () {
        activeId = dev.id;
        if (history.replaceState) {
          history.replaceState(null, "", "?device=" + encodeURIComponent(dev.id));
        }
        renderDeviceTabs();
        renderStepsPanel();
        renderOptionalVideo();
      });
      wrap.appendChild(btn);
    });
  }

  function renderStepsPanel() {
    var panel = $("guide-steps-panel");
    var dev = devices.find(function (d) {
      return d.id === activeId;
    });
    if (!panel || !dev) return;
    panel.innerHTML = "";
    var title = document.createElement("strong");
    title.textContent = dev.install_title || dev.label;
    panel.appendChild(title);

    var ol = document.createElement("ol");
    (dev.install_steps || []).forEach(function (step, idx) {
      var li = document.createElement("li");
      li.textContent = step;
      if (idx === 0) {
        var st = storeForDevice(dev);
        if (st && st.url) {
          var a = document.createElement("a");
          a.className = "store-link";
          a.href = st.url;
          a.target = "_blank";
          a.rel = "noopener";
          a.textContent = "↓ " + (st.label || "Скачать Happ");
          li.appendChild(document.createElement("br"));
          li.appendChild(a);
        } else if (dev.id === "android") {
          var note = document.createElement("span");
          note.className = "muted";
          note.textContent =
            "Ссылка на магазин уточняется — найдите Happ в Google Play.";
          li.appendChild(document.createElement("br"));
          li.appendChild(note);
        }
      }
      ol.appendChild(li);
    });
    panel.appendChild(ol);

    var after = (window._guideContent && window._guideContent.steps || {}).after_device || [];
    if (after.length) {
      var h = document.createElement("p");
      h.className = "sheet__label";
      h.style.marginTop = "0.75rem";
      h.textContent = "Дальше";
      panel.appendChild(h);
      var ol2 = document.createElement("ol");
      after.forEach(function (t) {
        var li = document.createElement("li");
        li.textContent = t;
        ol2.appendChild(li);
      });
      panel.appendChild(ol2);
    }

    if (dev.tun_callout) {
      var callout = document.createElement("p");
      callout.className = "callout callout--warn";
      callout.textContent = dev.tun_callout;
      panel.appendChild(callout);
    }

    var trouble = document.createElement("p");
    trouble.className = "muted";
    trouble.style.marginTop = "0.75rem";
    trouble.innerHTML =
      'Не работает — <a class="site-footer__link" href="/start/help/errors/">частые проблемы</a> или ' +
      '<a class="site-footer__link" href="https://t.me/Bender_KVN_bot" target="_blank" rel="noopener">поддержка</a>.';
    panel.appendChild(trouble);
  }

  function renderOptionalVideo() {
    var fold = $("guide-video-fold");
    var wrap = $("guide-video-wrap");
    var v = (window._guideContent && window._guideContent.setup_videos) || {};
    if (!fold || !wrap) return;
    wrap.innerHTML = "";
    fold.classList.add("hidden");
    var gif = "";
    var mp4 = "";
    if (activeId === "iphone") {
      gif = v.media_ios_gif || "";
      mp4 = v.media_ios_mp4 || "";
    } else if (activeId === "android") {
      gif = v.media_android_gif || "";
      mp4 = v.media_android_mp4 || "";
    }
    if (!gif && !mp4) return;

    var loaded = false;
    if (mp4) {
      var video = document.createElement("video");
      video.className = "guide-video";
      video.controls = true;
      video.playsInline = true;
      video.preload = "metadata";
      if (gif) video.poster = gif;
      var src = document.createElement("source");
      src.src = mp4;
      src.type = "video/mp4";
      video.appendChild(src);
      wrap.appendChild(video);
      loaded = true;
    } else if (gif) {
      var img = document.createElement("img");
      img.className = "guide-gif";
      img.src = gif;
      img.alt = "";
      img.loading = "lazy";
      img.onerror = function () {
        fold.classList.add("hidden");
      };
      img.onload = function () {
        fold.classList.remove("hidden");
      };
      wrap.appendChild(img);
      loaded = true;
    }
    if (loaded && mp4) fold.classList.remove("hidden");
    if ($("guide-video-summary")) {
      $("guide-video-summary").textContent = v.video_optional || "Видео, если удобнее";
    }
  }

  fetch(CONTENT_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("content");
      return r.json();
    })
    .then(function (data) {
      window._guideContent = data;
      var v = data.setup_videos || {};
      devices = data.devices || [];
      activeId = pickDevice();
      $("guide-title").textContent = v.title || "Как подключить";
      document.title = (v.title || "BenderVPN") + " — инструкция";
      $("guide-lead").textContent =
        v.lead || "Пошагово для телефона и компьютера. Страница открывается без VPN.";
      var autoNote = $("guide-auto-note");
      if (autoNote) {
        autoNote.textContent =
          v.auto_note || (data.auto_profile && data.auto_profile.lead) || "";
        if (!autoNote.textContent.trim()) autoNote.classList.add("hidden");
      }
      if (v.setup_button && $("btn-guide-setup")) {
        $("btn-guide-setup").textContent = v.setup_button;
      }
      if (v.portal_button && $("btn-guide-portal")) {
        $("btn-guide-portal").textContent = v.portal_button;
      }
      renderDeviceTabs();
      renderStepsPanel();
      renderOptionalVideo();
      var foot = $("site-footer-mount");
      if (foot && window.BenderPortalShared) {
        BenderPortalShared.renderSiteFooter(foot, data);
      }
    })
    .catch(function () {
      $("guide-lead").textContent = "Не удалось загрузить тексты. Обновите страницу.";
    });
})();
