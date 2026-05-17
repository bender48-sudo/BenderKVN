(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var token = params.get("t") || "";

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

  function renderQr(url) {
    var canvas = $("setup-qr");
    if (window.QRCode && canvas) {
      QRCode.toCanvas(
        canvas,
        url,
        { width: 220, margin: 2, color: { dark: "#1a2332", light: "#ffffff" } },
        function () {}
      );
    }
  }

  function bindCopy(url, labelCopy, labelCopied) {
    var btn = $("btn-copy");
    if (!btn) return;
    btn.textContent = labelCopy;
    btn.onclick = function () {
      var done = function () {
        btn.textContent = labelCopied;
        setTimeout(function () {
          btn.textContent = labelCopy;
        }, 2000);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(done).catch(function () {
          window.prompt("Скопируйте ссылку:", url);
        });
      } else {
        window.prompt("Скопируйте ссылку:", url);
        done();
      }
    };
  }

  function showSetupResult(url, content, extra) {
    var s = content.setup;
    hide($("setup-loading"));
    hide($("setup-signup"));
    hide($("setup-error"));
    if (extra && extra.expire_at && $("setup-success-msg")) {
      $("setup-success-msg").textContent =
        (s.success_trial || "Готово! Бесплатный доступ до") + " " + extra.expire_at;
    }
    $("setup-link").textContent = url;
    $("setup-link").href = url;
    $("btn-open-happ").href = url;
    $("btn-open-happ").textContent = s.open_happ || "Открыть в Happ";
    renderQr(url);
    bindCopy(url, s.copy, s.copied);
    showEl($("setup-content"));
  }

  function bindSignupForm(content) {
    var s = content.setup;
    $("signup-heading").textContent = s.signup_heading || "Новый пользователь";
    $("signup-lead").textContent = s.signup_lead || "";
    $("signup-email-label").textContent = s.signup_email_label || "Email";
    $("signup-phone-label").textContent = s.signup_phone_label || "Телефон";
    $("signup-terms-label").textContent = s.signup_terms || "";
    $("btn-signup-submit").textContent = s.signup_submit || "Получить доступ";
    $("signup-note").textContent = s.signup_note || "";
    $("signup-email").placeholder = s.signup_email_placeholder || "you@example.com";

    var steps = $("happ-steps");
    if (steps && s.happ_steps) {
      steps.innerHTML = "";
      s.happ_steps.forEach(function (t) {
        var li = document.createElement("li");
        li.textContent = t;
        steps.appendChild(li);
      });
    }

    $("btn-signup-submit").addEventListener("click", function () {
      hide($("setup-error"));
      var email = ($("signup-email").value || "").trim();
      var phone = ($("signup-phone").value || "").trim();
      if (!$("signup-terms").checked) {
        showError(s.signup_terms_required || "Примите условия.");
        return;
      }
      if (!email || email.indexOf("@") < 1) {
        showError(s.signup_email_invalid || "Укажите email.");
        return;
      }
      hide($("setup-signup"));
      showEl($("setup-loading"));
      $("setup-loading").textContent = s.signup_loading || "Создаём доступ…";

      fetch("api/web-trial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, phone: phone }),
      })
        .then(function (r) {
          return r.json().then(function (j) {
            return { code: r.status, body: j };
          });
        })
        .then(function (res) {
          hide($("setup-loading"));
          if (!res.body.ok || !res.body.sub_url) {
            var err = s.signup_error_generic;
            if (res.body.error === "trial_already_claimed") {
              err = s.signup_error_used;
            } else if (res.body.error === "rate_limited") {
              err = s.signup_error_rate;
            } else if (res.body.error === "invalid_email") {
              err = s.signup_email_invalid;
            }
            showError(err);
            return;
          }
          showSetupResult(res.body.sub_url, content, res.body);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic);
        });
    });
  }

  fetch("content/ru.json")
    .then(function (r) {
      return r.json();
    })
    .then(function (content) {
      var s = content.setup;
      $("setup-title").textContent = s.title_browser || s.title;
      $("setup-lead").textContent = s.lead_browser || s.lead_paste;
      bindSignupForm(content);

      if (!token) {
        showEl($("setup-signup"));
        return;
      }

      hide($("setup-signup"));
      showEl($("setup-loading"));
      $("setup-lead").textContent = s.lead_token;

      fetch("api/verify?t=" + encodeURIComponent(token))
        .then(function (r) {
          return r.json().then(function (j) {
            return { code: r.status, body: j };
          });
        })
        .then(function (res) {
          hide($("setup-loading"));
          if (!res.body.ok || !res.body.sub_url) {
            showError(s.invalid_token);
            showEl($("setup-signup"));
            return;
          }
          showSetupResult(res.body.sub_url, content, null);
        })
        .catch(function () {
          hide($("setup-loading"));
          showError(content.errors.generic);
          showEl($("setup-signup"));
        });
    })
    .catch(function () {
      showError("Не удалось загрузить тексты страницы.");
    });
})();
