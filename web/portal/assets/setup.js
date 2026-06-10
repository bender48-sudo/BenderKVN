(function () {
  "use strict";

  var CONTENT_URL = "/portal/content/ru.json";
  var API_TRIAL = "/setup/api/web-trial";
  var API_RECOVER = "/setup/api/web-trial-recover";
  var API_VERIFY = "/setup/api/verify";
  var API_TELEGRAM_SETUP = "/setup/api/telegram-setup";
  var SUPPORT_BOT_URL = "https://t.me/Bender_KVN_bot";

  var params = new URLSearchParams(window.location.search);
  var token = params.get("t") || "";
  var content = null;
  var lastStoreKey = "generic";

  function $(id) {
    return document.getElementById(id);
  }

  function hide(el) {
    if (el) el.classList.add("hidden");
  }

  function showEl(el) {
    if (el) el.classList.remove("hidden");
  }

  function showError(msg, code, opts) {
    opts = opts || {};
    hide($("setup-loading"));
    hide($("setup-content"));
    $("setup-error").textContent = msg;
    var helpWrap = $("setup-error-help");
    var helpLink = $("setup-error-help-link");
    if (helpWrap && helpLink) {
      if (code) {
        helpLink.href = "/start/help/errors/?code=" + encodeURIComponent(code);
        var hl = (content && content.user_errors && content.user_errors.help_link) || "";
        helpLink.textContent = hl || "Подробнее об этой ошибке";
        showEl(helpWrap);
      } else {
        hide(helpWrap);
      }
    }
    showEl($("setup-error"));
    if (opts.hideSignup) {
      hide($("setup-signup"));
    } else {
      showEl($("setup-signup"));
      if (!isTelegramMiniApp()) {
        showEl($("setup-paths"));
        showEl($("setup-hero"));
        if ($("setup-recover-fold")) showEl($("setup-recover-fold"));
      }
    }
  }

  function storeForKey(key) {
    var stores = (content && content.happ_install) || {};
    return stores[key] || stores.generic || null;
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
    var q = new URLSearchParams(window.location.search || "");
    var tid = parseInt(q.get("tid") || "0", 10);
    if (tid > 0) return tid;
    return 0;
  }

  /** True only inside a real Telegram Mini App session (not bare telegram-web-app.js in a browser). */
  function hasTelegramInitContext() {
    var tg = getTelegramWebApp();
    if (!tg) return false;
    var initData = (tg.initData || "").trim();
    if (initData) return true;
    var unsafe = tg.initDataUnsafe;
    if (!unsafe || typeof unsafe !== "object") return false;
    if (unsafe.user && unsafe.user.id) return true;
    if (unsafe.auth_date) return true;
    return false;
  }

  function isTelegramMiniApp() {
    return hasTelegramInitContext();
  }

  function openExternal(url) {
    var u = (url || "").trim();
    if (!u) return;
    var tg = isTelegramMiniApp() ? getTelegramWebApp() : null;
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

  function bindExternalLink(el) {
    if (!el || el.dataset.bvpnBound === "1") return;
    el.dataset.bvpnBound = "1";
    el.addEventListener("click", function (ev) {
      var href = (el.getAttribute("href") || "").trim();
      if (!href || href === "#") return;
      if (isTelegramMiniApp()) {
        ev.preventDefault();
        openExternal(href);
      }
    });
  }

  function normalizeSubUrl(url) {
    var u = (url || "").trim();
    if (!u) return u;
    return u
      .replace("://p4n7q.conntest.xyz:2053", "://p4n7q.conntest.xyz:8443")
      .replace("://k9x2m1.conntest.xyz:2053", "://k9x2m1.conntest.xyz:8443");
  }

  /** Happ deep link for one-tap subscription import (iOS/Android). */
  function buildHappDeepLink(subUrl) {
    var u = normalizeSubUrl(subUrl);
    if (!u) return u;
    return "happ://add/" + u;
  }

  function isBrowserFlow() {
    return !isTelegramMiniApp() && !token;
  }

  function renderJourney(activeStep) {
    var wrap = $("setup-journey");
    var s = content.setup || {};
    if (!wrap || !isBrowserFlow()) {
      hide(wrap);
      return;
    }
    var steps = s.journey_steps || [];
    if (!steps.length) {
      hide(wrap);
      return;
    }
    wrap.innerHTML = "";
    if (s.journey_title) {
      var h = document.createElement("p");
      h.className = "step-badge";
      h.textContent = s.journey_title;
      wrap.appendChild(h);
    }
    steps.forEach(function (label, idx) {
      var n = idx + 1;
      var el = document.createElement("div");
      el.className = "flow-journey__step";
      if (n < activeStep) el.className += " flow-journey__step--done";
      if (n === activeStep) el.className += " flow-journey__step--active";
      el.textContent = n + ". " + label;
      wrap.appendChild(el);
    });
    showEl(wrap);
  }

  function renderPlatformDownloads() {
    var wrap = $("platform-downloads");
    var title = $("platform-downloads-title");
    var s = content.setup || {};
    if (title) {
      title.textContent = s.platform_downloads_title || "Скачать Happ";
    }
    if (!wrap) return;
    wrap.innerHTML = "";
    var stores = (content && content.happ_install) || {};
    ["ios", "android", "windows", "mac"].forEach(function (key) {
      var st = stores[key];
      if (!st || !st.url) return;
      var a = document.createElement("a");
      a.className = "btn btn--secondary";
      a.href = st.url;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = "↓ " + (st.label || key);
      wrap.appendChild(a);
    });
  }

  function renderHappStoreLink(key) {
    var link = $("happ-store-link");
    if (!link) return;
    hide(link);
  }

  function renderStepList(ol, steps) {
    if (!ol) return;
    ol.innerHTML = "";
    (steps || []).forEach(function (text) {
      var li = document.createElement("li");
      li.textContent = text;
      ol.appendChild(li);
    });
  }

  function renderQr(url) {
    var canvas = $("setup-qr");
    var fallback = $("setup-qr-fallback");
    var panel = $("setup-qr-panel");
    if (fallback) {
      fallback.classList.add("hidden");
      fallback.textContent = "";
    }
    if (!canvas) return;
    if (window.QRCode) {
      QRCode.toCanvas(
        canvas,
        url,
        { width: 220, margin: 2, color: { dark: "#e85d04", light: "#ffffff" } },
        function (err) {
          if (err) {
            if (panel) panel.classList.add("qr-wrap--failed");
            if (fallback) {
              fallback.textContent =
                (content.setup && content.setup.qr_fallback) ||
                "QR не загрузился. Скопируй ссылку или открой Happ вручную.";
              fallback.classList.remove("hidden");
            }
          }
        }
      );
    } else {
      if (panel) panel.classList.add("qr-wrap--failed");
      if (fallback) {
        fallback.textContent =
          (content.setup && content.setup.qr_fallback) ||
          "QR не загрузился. Скопируй ссылку или открой Happ вручную.";
        fallback.classList.remove("hidden");
      }
    }
  }

  function bindCopy(btn, text, doneText) {
    if (!btn) return;
    btn.onclick = function () {
      var done = function () {
        var prev = btn.textContent;
        btn.textContent = doneText;
        setTimeout(function () {
          btn.textContent = prev;
        }, 2000);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () {
          window.prompt("Скопируйте:", text);
        });
      } else {
        window.prompt("Скопируйте:", text);
        done();
      }
    };
  }

  function renderBindTelegram(extra) {
    var panel = $("bind-tg-panel");
    var s = content.setup;
    if (!panel || !s) return;
    if (!extra || !extra.bind_url || extra.telegram_bound) {
      hide(panel);
      return;
    }
    $("bind-tg-title").textContent = s.bind_tg_title || "Подтвердите в Telegram";
    $("bind-tg-lead").textContent = s.bind_tg_lead || "";
    var btn = $("btn-bind-tg");
    btn.href = extra.bind_url;
    btn.textContent = s.bind_tg_button || "Открыть бота";
    bindExternalLink(btn);
    $("bind-tg-note").textContent = s.bind_tg_note || "";
    var copyBind = $("btn-copy-bind");
    if (copyBind) {
      copyBind.textContent = s.bind_tg_copy || "Скопировать ссылку на бота";
      bindCopy(copyBind, extra.bind_url, s.bind_tg_copied || "Скопировано");
    }
    renderJourney(3);
    showEl(panel);
    try {
      localStorage.setItem("bvpn_bind_url", extra.bind_url);
    } catch (e) {
      /* ignore */
    }
  }

  function handleTrialSuccess(body) {
    if (body && body.setup_url) {
      window.location.href = body.setup_url;
      return true;
    }
    if (body && body.sub_url) {
      showSetupResult(body.sub_url, body);
      return true;
    }
    return false;
  }

  function renderSetupDeviceGrid() {
    var grid = $("setup-device-grid");
    var title = $("device-pick-title");
    var s = content.setup || {};
    if (title && s.device_pick_title) title.textContent = s.device_pick_title;
    if (!grid) return;
    grid.innerHTML = "";
    (content.devices || []).forEach(function (dev) {
      var a = document.createElement("a");
      a.className = "device-card";
      a.href = "/portal/guide.html?device=" + encodeURIComponent(dev.id);
      a.innerHTML =
        '<span class="icon" aria-hidden="true">' + dev.icon + "</span>" + dev.label;
      grid.appendChild(a);
    });
  }

  function mountSharedSupport() {
    var mount = $("support-block-mount");
    if (mount && window.BenderPortalShared && content) {
      BenderPortalShared.renderSupportBlock(mount, content);
    }
  }

  function showSetupResult(url, extra) {
    var s = content.setup;
    hide($("setup-loading"));
    hide($("setup-signup"));
    hide($("setup-error"));
    hide($("setup-paths"));
    hide($("setup-hero"));
    if ($("setup-recover-fold")) hide($("setup-recover-fold"));
    if ($("config-ready-title")) {
      $("config-ready-title").textContent = s.config_ready_title || "Твоя настройка готова";
    }
    if ($("config-ready-lead")) {
      $("config-ready-lead").textContent = s.config_ready_lead || s.device_rule || "";
    }
    if ($("auto-profile-note")) {
      $("auto-profile-note").textContent =
        s.auto_profile_note || (content.auto_profile && content.auto_profile.lead) || "";
    }
    if (extra && extra.expire_at) {
      $("setup-success-msg").textContent =
        (s.success_trial || "Готово! Бесплатный доступ до") + " " + extra.expire_at;
      showEl($("setup-success-msg"));
    } else {
      hide($("setup-success-msg"));
    }
    var step1Lead = $("setup-step1-lead");
    if (step1Lead) {
      var inTg = isTelegramMiniApp();
      var lead = inTg
        ? s.step1_lead_tg || s.step1_lead
        : s.step1_lead;
      if (lead) {
        step1Lead.textContent = lead;
        showEl(step1Lead);
      }
    }
    renderJourney(2);
    renderPlatformDownloads();
    var afterVpn = $("setup-after-vpn");
    if (afterVpn && s.after_vpn_ok && isBrowserFlow()) {
      afterVpn.textContent = s.after_vpn_ok;
      showEl(afterVpn);
    } else if (afterVpn) {
      hide(afterVpn);
    }
    var happTitle = $("happ-steps-title");
    if (happTitle) happTitle.textContent = s.step1_title || "Шаг 1 — Happ";
    if (extra && extra.customer_id) {
      $("customer-id-value").textContent = extra.customer_id;
      showEl($("customer-id-panel"));
      try {
        localStorage.setItem("bvpn_customer_id", extra.customer_id);
        localStorage.setItem("bvpn_customer_email", ($("signup-email").value || "").trim());
      } catch (e) {
        /* ignore */
      }
    } else {
      hide($("customer-id-panel"));
    }
    var norm = normalizeSubUrl(url);
    var linkEl = $("setup-link");
    if (linkEl) linkEl.textContent = norm;
    var linkFold = $("setup-link-fold");
    if (linkFold) linkFold.open = true;
    var openBtn = $("btn-open-happ");
    if (openBtn) {
      openBtn.href = buildHappDeepLink(norm);
      bindExternalLink(openBtn);
    }
    var devRule = $("setup-device-rule");
    if (devRule && s.device_rule) devRule.textContent = s.device_rule;
    var devRuleExtra = $("setup-device-rule-extra");
    if (devRuleExtra) {
      if (s.device_rule_extra) {
        devRuleExtra.textContent = s.device_rule_extra;
        showEl(devRuleExtra);
      } else {
        hide(devRuleExtra);
      }
    }
    if ($("setup-link-section-title")) {
      $("setup-link-section-title").textContent = s.link_section_title || "Подключение в Happ";
    }
    if ($("setup-link-section-lead")) {
      var linkLead = $("setup-link-section-lead");
      if (s.link_section_lead) {
        linkLead.textContent = s.link_section_lead;
        showEl(linkLead);
      } else {
        hide(linkLead);
      }
    }
    if ($("setup-qr-toggle")) {
      $("setup-qr-toggle").textContent = s.qr_section_title || "QR-код для другого устройства";
    }
    var instr = $("btn-setup-instruction");
    if (instr) {
      instr.href = "/portal/guide.html?v=27";
      instr.textContent = s.instruction_link || "Открыть инструкцию";
    }
    bindExternalLink(instr);
    renderQr(norm);
    try {
      localStorage.setItem("bvpn_subscription_url", norm);
    } catch (e) {
      /* ignore */
    }
    bindCopy($("btn-copy"), url, s.copied);
    if (extra && extra.customer_id) {
      bindCopy($("btn-copy-id"), extra.customer_id, s.copied_id);
    }
    renderStepList($("happ-steps"), s.happ_steps);
    renderHappStoreLink(lastStoreKey);
    renderBindTelegram(extra);
    renderSetupDeviceGrid();
    mountSharedSupport();
    showEl($("setup-content"));
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

  function bindLegalConsent() {
    var label = $("signup-terms-label");
    var btn = $("btn-signup-submit");
    var cb = $("signup-terms");
    if (!label || !btn || !cb) return;
    var legal = content.legal || {};
    var shared = window.BenderPortalShared;
    var termsUrl = shared ? shared.legalTermsUrl() : "/portal/legal/terms.html";
    var privacyUrl = shared ? shared.legalPrivacyUrl() : "/portal/legal/privacy.html";
    label.innerHTML =
      'Я принимаю <a class="text-link" href="' +
      termsUrl +
      '" target="_blank" rel="noopener">условия пользования</a> и ' +
      '<a class="text-link" href="' +
      privacyUrl +
      '" target="_blank" rel="noopener">политику конфиденциальности</a>.';
    function syncBtn() {
      btn.disabled = !cb.checked;
      btn.setAttribute("aria-disabled", cb.checked ? "false" : "true");
    }
    cb.addEventListener("change", syncBtn);
    syncBtn();
  }

  function bindForms() {
    var s = content.setup;

    $("btn-signup-submit").addEventListener("click", function () {
      hide($("setup-error"));
      var email = ($("signup-email").value || "").trim();
      var phone = ($("signup-phone").value || "").trim();
      if (!$("signup-terms").checked) {
        showError(s.signup_terms_required);
        return;
      }
      if (!email || email.indexOf("@") < 1) {
        showError(s.signup_email_invalid);
        return;
      }
      hide($("setup-signup"));
      showEl($("setup-loading"));
      $("setup-loading").textContent = s.signup_loading;

      var refCode = "";
      try {
        refCode = localStorage.getItem("bvpn_ref_code") || "";
      } catch (eRef) {
        refCode = "";
      }
      postJson(API_TRIAL, { email: email, phone: phone, ref_code: refCode })
        .then(function (res) {
          hide($("setup-loading"));
          if (res.code === 409 && res.body.error === "trial_already_claimed") {
            $("recover-email").value = email;
            return postJson(API_RECOVER, { email: email });
          }
          if (!res.body.ok || (!res.body.setup_url && !res.body.sub_url)) {
            var err = s.signup_error_generic;
            if (res.body.error === "rate_limited") {
              showError(s.signup_error_rate, "rate_limited");
              return null;
            }
            if (res.body.error === "invalid_email") {
              showError(s.signup_email_invalid);
              return null;
            }
            showError(err, "service_unavailable");
            return null;
          }
          return res;
        })
        .then(function (res) {
          if (!res) return;
          if (res.body && res.body.ok && handleTrialSuccess(res.body)) {
            return;
          }
          if (res.body && res.body.error === "trial_expired") {
            showError(s.signup_error_expired || s.signup_error_used, "trial_expired");
            if (res.body.bind_url) renderBindTelegram(res.body);
            return;
          }
          if (res.code === 404) {
            showError(s.signup_error_not_found, "trial_used");
            return;
          }
          showError(s.signup_error_used, "trial_used");
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic, "service_unavailable");
        });
    });

    $("btn-recover-submit").addEventListener("click", function () {
      hide($("setup-error"));
      var email = ($("recover-email").value || $("signup-email").value || "").trim();
      if (!email || email.indexOf("@") < 1) {
        showError(s.signup_email_invalid);
        return;
      }
      hide($("setup-signup"));
      showEl($("setup-loading"));
      $("setup-loading").textContent = s.recover_loading;

      postJson(API_RECOVER, { email: email })
        .then(function (res) {
          hide($("setup-loading"));
          if (!res.body.ok || (!res.body.setup_url && !res.body.sub_url)) {
            if (res.body.error === "trial_expired") {
              showError(s.signup_error_expired || s.signup_error_used, "trial_expired");
              if (res.body.bind_url) renderBindTelegram(res.body);
              return;
            }
            if (res.body.error === "not_found") showError(s.signup_error_not_found, "trial_used");
            else showError(s.signup_error_generic, "service_unavailable");
            return;
          }
          handleTrialSuccess(res.body);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic, "service_unavailable");
        });
    });
  }

  function loadTelegramSetup(retry) {
    var s = content.setup;
    if (isTelegramMiniApp()) {
      var tg = getTelegramWebApp();
      document.documentElement.classList.add("tg-webapp");
      tg.ready();
      tg.expand();
    }
    if ($("setup-hero-title")) $("setup-hero-title").textContent = s.title_tg || s.title;
    if ($("setup-hero-lead")) $("setup-hero-lead").textContent = s.lead_tg || "";
    if ($("setup-hero")) showEl($("setup-hero"));
    hide($("setup-paths"));
    hide($("setup-signup"));
    if ($("setup-recover-fold")) hide($("setup-recover-fold"));
    hide($("setup-error"));
    showEl($("setup-loading"));
    $("setup-loading").textContent = s.signup_loading_tg || s.signup_loading;

    var tid = getTelegramUserId();
    if (!tid && retry < 8) {
      setTimeout(function () {
        loadTelegramSetup(retry + 1);
      }, 120);
      return;
    }
    if (!tid) {
      hide($("setup-loading"));
      showError(
        s.error_tg_user_missing ||
          "Не удалось определить тебя в Telegram. Закрой Mini App и открой снова из бота.",
        "service_unavailable",
        { hideSignup: true }
      );
      return;
    }

    postJson(API_TELEGRAM_SETUP, { telegram_id: tid })
      .then(function (res) {
        hide($("setup-loading"));
        if (res.body && res.body.ok && res.body.setup_page_url) {
          window.location.replace(res.body.setup_page_url);
          return;
        }
        if (res.body && res.body.ok && res.body.sub_url) {
          showSetupResult(res.body.sub_url, null);
          return;
        }
        var msg =
          (res.body && res.body.message) ||
          s.signup_error_generic ||
          "Не удалось загрузить настройку.";
        if (res.body && res.body.error === "no_subscription") {
          msg = s.error_no_subscription || msg;
        }
        showError(msg, res.body && res.body.error, { hideSignup: true });
        if (res.body && res.body.bot_url) {
          var helpWrap = $("setup-error-help");
          var helpLink = $("setup-error-help-link");
          if (helpWrap && helpLink) {
            helpLink.href = res.body.bot_url;
            helpLink.textContent = s.error_open_bot || "Открыть бота";
            showEl(helpWrap);
          }
        }
      })
      .catch(function () {
        hide($("setup-loading"));
        showError(content.errors.generic, "service_unavailable", { hideSignup: true });
      });
  }

  function botUrlWithReferral() {
    try {
      var ref = localStorage.getItem("bvpn_ref_code") || "";
      if (ref) return SUPPORT_BOT_URL + "?start=ref_" + encodeURIComponent(ref);
    } catch (e) {
      /* ignore */
    }
    return SUPPORT_BOT_URL;
  }

  function renderSetupStepsList() {
    var list = $("setup-steps-list");
    var s = content.setup || {};
    if (!list) return;
    list.innerHTML = "";
    (s.steps_list || s.journey_steps || []).forEach(function (step, idx) {
      var li = document.createElement("li");
      li.textContent = idx + 1 + ". " + step;
      list.appendChild(li);
    });
  }

  function bindTexts() {
    var s = content.setup;
    var inTg = isTelegramMiniApp();
    var browser = isBrowserFlow();
    var hero = $("setup-hero");
    var paths = $("setup-paths");
    var recoverFold = $("setup-recover-fold");

    if (inTg) {
      if (hero) hide(hero);
      if (paths) hide(paths);
      if (recoverFold) hide(recoverFold);
      hide($("setup-journey"));
      hide($("signup-step-badge"));
    } else if (browser) {
      if (hero) showEl(hero);
      if ($("setup-hero-title")) {
        $("setup-hero-title").textContent = s.hero_title || s.title_browser || s.title;
      }
      if ($("setup-hero-lead")) {
        $("setup-hero-lead").textContent = s.hero_lead || s.path_email_lead || "";
      }
      if (paths) showEl(paths);
      if ($("setup-tg-badge")) $("setup-tg-badge").textContent = s.path_tg_badge || "90 дней";
      if ($("setup-tg-title")) {
        $("setup-tg-title").textContent = s.path_tg_title || "90 дней бесплатно в Telegram";
      }
      if ($("setup-tg-lead")) $("setup-tg-lead").textContent = s.path_tg_lead || "";
      var tgBtn = $("btn-setup-tg");
      if (tgBtn) {
        tgBtn.textContent = s.path_tg_button || "Открыть Telegram-бота";
        tgBtn.href = botUrlWithReferral();
        bindExternalLink(tgBtn);
      }
      if ($("setup-email-badge")) $("setup-email-badge").textContent = s.path_email_badge || "1 сутки";
      if ($("setup-email-title")) {
        $("setup-email-title").textContent = s.path_email_title || s.signup_heading;
      }
      if ($("setup-email-lead")) {
        $("setup-email-lead").textContent = s.path_email_lead || s.signup_lead;
      }
      renderJourney(1);
      if ($("setup-steps-list")) hide($("setup-steps-list"));
      if (recoverFold) showEl(recoverFold);
    }

    if ($("recover-fold-title")) {
      $("recover-fold-title").textContent = s.recover_fold_title || s.recover_heading || "";
    }
    var recoverTeaser = $("recover-fold-teaser");
    if (recoverTeaser) {
      if (s.recover_fold_teaser) {
        recoverTeaser.textContent = s.recover_fold_teaser;
        showEl(recoverTeaser);
      } else {
        hide(recoverTeaser);
      }
    }
    $("recover-lead").textContent = s.recover_lead;
    if ($("recover-tg-hint")) $("recover-tg-hint").textContent = s.recover_tg_hint || "";
    var recoverTgBtn = $("btn-recover-tg-id");
    if (recoverTgBtn) {
      recoverTgBtn.textContent = s.recover_tg_btn || "Узнать мой Telegram ID";
      recoverTgBtn.href = SUPPORT_BOT_URL + "?start=show_id";
      bindExternalLink(recoverTgBtn);
    }
    if ($("recover-email-label")) $("recover-email-label").textContent = s.signup_email_label;
    $("signup-email-label").textContent = s.signup_email_label;
    $("signup-phone-label").textContent = s.signup_phone_label;
    var phoneHint = $("signup-phone-hint");
    if (phoneHint) {
      if (s.signup_phone_hint) {
        phoneHint.textContent = s.signup_phone_hint;
        showEl(phoneHint);
      } else {
        hide(phoneHint);
      }
    }
    var consent = $("signup-consent-note");
    if (consent) consent.textContent = s.signup_consent_note || "";
    bindLegalConsent();
    var linkToggle = $("setup-link-toggle");
    if (linkToggle) linkToggle.textContent = s.show_link || "Ссылка подписки";
    $("btn-signup-submit").textContent = s.signup_submit;
    $("btn-recover-submit").textContent = s.recover_submit;
    $("signup-note").textContent = s.signup_note;
    $("signup-email").placeholder = s.signup_email_placeholder;
    $("recover-email").placeholder = s.signup_email_placeholder;
    $("customer-id-label").textContent = s.customer_id_label;
    $("customer-id-hint").textContent = s.customer_id_hint;
    $("btn-copy").textContent = s.copy;
    $("btn-copy-id").textContent = s.copy_id;
    $("btn-open-happ").textContent = s.open_happ;
    var guideBtn = $("btn-setup-guide");
    if (guideBtn) {
      var gv = (content.setup_videos || {}).guide_link || content.buttons.watch_guide;
      guideBtn.textContent = gv || "Инструкция по шагам";
    }
    var instr = $("btn-setup-instruction");
    if (instr) {
      instr.textContent = s.instruction_link || "Открыть инструкцию";
    }
    if ($("device-pick-title")) {
      $("device-pick-title").textContent = s.device_pick_title || "Выбери устройство";
    }
  }

  fetch(CONTENT_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("content");
      return r.json();
    })
    .then(function (data) {
      content = data;
      try {
        var qp = new URLSearchParams(window.location.search || "");
        var ref = (qp.get("ref") || "").trim();
        if (ref) localStorage.setItem("bvpn_ref_code", ref);
      } catch (eRef) {
        /* ignore */
      }
      bindTexts();
      bindForms();
      var footMount = $("site-footer-mount");
      if (footMount && window.BenderPortalShared) {
        BenderPortalShared.renderSiteFooter(footMount, data);
        BenderPortalShared.bindStatusLinks(document);
      }
      mountSharedSupport();

      if (!token) {
        if (isTelegramMiniApp()) {
          loadTelegramSetup(0);
          return;
        }
        if (
          window.BenderPortalShared &&
          BenderPortalShared.isLocalDev &&
          BenderPortalShared.isLocalDev() &&
          getTelegramUserId() > 0
        ) {
          loadTelegramSetup(0);
          return;
        }
        showEl($("setup-paths"));
        showEl($("setup-signup"));
        if ($("setup-recover-fold")) showEl($("setup-recover-fold"));
        return;
      }

      hide($("setup-signup"));
      hide($("setup-paths"));
      hide($("setup-hero"));
      if ($("setup-recover-fold")) hide($("setup-recover-fold"));
      showEl($("setup-loading"));
      $("setup-loading").textContent = content.setup.lead_token;

      fetch(API_VERIFY + "?t=" + encodeURIComponent(token))
        .then(function (r) {
          return r.json().then(function (j) {
            return { code: r.status, body: j };
          });
        })
        .then(function (res) {
          hide($("setup-loading"));
          if (!res.body.ok || !res.body.sub_url) {
            showError(s.invalid_token, "link_expired");
            return;
          }
          showSetupResult(res.body.sub_url, null);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic, "service_unavailable");
        });
    })
    .catch(function () {
      showError("Не удалось загрузить тексты страницы.", "service_unavailable");
    });
})();
