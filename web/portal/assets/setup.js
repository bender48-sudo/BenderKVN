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

  function showError(msg, code) {
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
    showEl($("setup-signup"));
  }

  function storeForKey(key) {
    var stores = (content && content.happ_install) || {};
    return stores[key] || stores.generic || null;
  }

  function normalizeSubUrl(url) {
    var u = (url || "").trim();
    if (!u) return u;
    return u
      .replace("://p4n7q.conntest.xyz:2053", "://p4n7q.conntest.xyz:8443")
      .replace("://k9x2m1.conntest.xyz:2053", "://k9x2m1.conntest.xyz:8443");
  }

  function isBrowserFlow() {
    return !getTelegramWebApp() && !token;
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
      a.className = "btn btn-secondary";
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
    if (window.QRCode && canvas) {
      QRCode.toCanvas(
        canvas,
        url,
        { width: 220, margin: 2, color: { dark: "#e85d04", light: "#ffffff" } },
        function () {}
      );
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

  function showSetupResult(url, extra) {
    var s = content.setup;
    hide($("setup-loading"));
    hide($("setup-signup"));
    hide($("setup-error"));
    if (extra && extra.expire_at) {
      $("setup-success-msg").textContent =
        (s.success_trial || "Готово! Бесплатный доступ до") + " " + extra.expire_at;
    }
    var step1Lead = $("setup-step1-lead");
    if (step1Lead) {
      var inTg = !!getTelegramWebApp();
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
    $("setup-link").textContent = norm;
    $("setup-link").href = norm;
    $("btn-open-happ").href = norm;
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

      postJson(API_TRIAL, { email: email, phone: phone })
        .then(function (res) {
          hide($("setup-loading"));
          if (res.code === 409 && res.body.error === "trial_already_claimed") {
            $("recover-email").value = email;
            return postJson(API_RECOVER, { email: email });
          }
          if (!res.body.ok || !res.body.sub_url) {
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
          if (res.body && res.body.ok && res.body.sub_url) {
            showSetupResult(res.body.sub_url, res.body);
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
          if (!res.body.ok || !res.body.sub_url) {
            if (res.body.error === "trial_expired") {
              showError(s.signup_error_expired || s.signup_error_used, "trial_expired");
              if (res.body.bind_url) renderBindTelegram(res.body);
              return;
            }
            if (res.body.error === "not_found") showError(s.signup_error_not_found, "trial_used");
            else showError(s.signup_error_generic, "service_unavailable");
            return;
          }
          showSetupResult(res.body.sub_url, res.body);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic, "service_unavailable");
        });
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

  function loadTelegramSetup(retry) {
    var s = content.setup;
    var tg = getTelegramWebApp();
    if (tg) {
      document.documentElement.classList.add("tg-webapp");
      tg.ready();
      tg.expand();
    }
    $("setup-title").textContent = s.title_tg || s.title;
    $("setup-lead").textContent = s.lead_tg || s.lead_browser;
    hide($("setup-signup"));
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
        "Не удалось определить Telegram. Закройте страницу и откройте снова из бота или Mini App.",
        "service_unavailable"
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
        showError(msg, res.body && res.body.error);
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
        showError(content.errors.generic, "service_unavailable");
      });
  }

  function bindTexts() {
    var s = content.setup;
    var inTg = !!getTelegramWebApp();
    var browser = isBrowserFlow();
    $("setup-title").textContent = inTg
      ? s.title_tg || s.title
      : s.title_browser || s.title;
    $("setup-lead").textContent = inTg ? s.lead_tg || s.lead_browser : s.lead_browser;
    if (browser) {
      renderJourney(1);
      var badge = $("signup-step-badge");
      if (badge) {
        badge.textContent = "Шаг 1 из 3";
        showEl(badge);
      }
    } else {
      hide($("setup-journey"));
      hide($("signup-step-badge"));
    }
    $("signup-heading").textContent = s.signup_heading;
    $("signup-lead").textContent = s.signup_lead;
    $("recover-heading").textContent = s.recover_heading;
    $("recover-lead").textContent = s.recover_lead;
    $("signup-email-label").textContent = s.signup_email_label;
    $("signup-phone-label").textContent = s.signup_phone_label;
    $("signup-terms-label").textContent = s.signup_terms;
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
      guideBtn.textContent = gv || "Видео: как подключить";
    }
    var recoverLabel = $("recover-email").previousElementSibling;
    if (recoverLabel) recoverLabel.textContent = s.signup_email_label;
  }

  fetch(CONTENT_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("content");
      return r.json();
    })
    .then(function (data) {
      content = data;
      bindTexts();
      bindForms();

      if (!token) {
        if (getTelegramWebApp() || getTelegramUserId() > 0) {
          loadTelegramSetup(0);
          return;
        }
        showEl($("setup-signup"));
        return;
      }

      hide($("setup-signup"));
      showEl($("setup-loading"));
      $("setup-loading").textContent = content.setup.lead_token;
      $("setup-lead").textContent = content.setup.lead_token;

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
