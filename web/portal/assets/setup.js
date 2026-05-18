(function () {
  "use strict";

  var CONTENT_URL = "/portal/content/ru.json";
  var API_TRIAL = "/setup/api/web-trial";
  var API_RECOVER = "/setup/api/web-trial-recover";
  var API_VERIFY = "/setup/api/verify";

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

  function showError(msg) {
    hide($("setup-loading"));
    hide($("setup-content"));
    $("setup-error").textContent = msg;
    showEl($("setup-error"));
    showEl($("setup-signup"));
  }

  function storeForKey(key) {
    var stores = (content && content.happ_install) || {};
    return stores[key] || stores.generic || null;
  }

  function renderHappStoreLink(key) {
    var link = $("happ-store-link");
    if (!link) return;
    var store = storeForKey(key || "generic");
    if (!store) {
      hide(link);
      return;
    }
    link.href = store.url;
    link.textContent = "↓ " + store.label;
    showEl(link.parentElement);
  }

  function renderStepList(ol, steps, storeKey) {
    if (!ol) return;
    ol.innerHTML = "";
    (steps || []).forEach(function (text, idx) {
      var li = document.createElement("li");
      li.textContent = text;
      ol.appendChild(li);
      if (idx === 0 && storeKey) {
        var store = storeForKey(storeKey);
        if (store) {
          var a = document.createElement("a");
          a.className = "store-link";
          a.href = store.url;
          a.target = "_blank";
          a.rel = "noopener";
          a.textContent = "↓ " + store.label;
          li.appendChild(document.createElement("br"));
          li.appendChild(a);
        }
      }
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
    if (step1Lead && s.step1_lead) {
      step1Lead.textContent = s.step1_lead;
      showEl(step1Lead);
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
    $("setup-link").textContent = url;
    $("setup-link").href = url;
    $("btn-open-happ").href = url;
    renderQr(url);
    try {
      localStorage.setItem("bvpn_subscription_url", url);
    } catch (e) {
      /* ignore */
    }
    bindCopy($("btn-copy"), url, s.copied);
    if (extra && extra.customer_id) {
      bindCopy($("btn-copy-id"), extra.customer_id, s.copied_id);
    }
    renderStepList($("happ-steps"), s.happ_steps, lastStoreKey);
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
            if (res.body.error === "rate_limited") err = s.signup_error_rate;
            else if (res.body.error === "invalid_email") err = s.signup_email_invalid;
            showError(err);
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
          if (res.code === 404) {
            showError(s.signup_error_not_found);
            return;
          }
          showError(s.signup_error_used);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic);
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
            if (res.body.error === "not_found") showError(s.signup_error_not_found);
            else showError(s.signup_error_generic);
            return;
          }
          showSetupResult(res.body.sub_url, res.body);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic);
        });
    });
  }

  function bindTexts() {
    var s = content.setup;
    $("setup-title").textContent = s.title_browser || s.title;
    $("setup-lead").textContent = s.lead_browser;
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
            showError(s.invalid_token);
            return;
          }
          showSetupResult(res.body.sub_url, null);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic);
        });
    })
    .catch(function () {
      showError("Не удалось загрузить тексты страницы.");
    });
})();
