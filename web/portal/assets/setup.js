(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var token = params.get("t") || "";
  var SUB_RE = /^https:\/\/.+\/api\/sub\/[A-Za-z0-9_-]{8,128}(\?.*)?$/i;

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
    hide($("setup-paste"));
    $("setup-error").textContent = msg;
    showEl($("setup-error"));
  }

  function normalizeSubUrl(raw) {
    var text = (raw || "").trim();
    if (!text) return "";
    if (!/^https?:\/\//i.test(text)) {
      text = "https://" + text.replace(/^\/+/, "");
    }
    try {
      var u = new URL(text);
      if (u.protocol !== "https:") return "";
      return u.toString();
    } catch (e) {
      return "";
    }
  }

  function isValidSubUrl(url) {
    return SUB_RE.test(url.split("#")[0]);
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

  function showSetupResult(url, content) {
    var s = content.setup;
    hide($("setup-loading"));
    hide($("setup-paste"));
    hide($("setup-error"));
    $("setup-link").textContent = url;
    $("setup-link").href = url;
    $("btn-open-happ").href = url;
    $("btn-open-happ").textContent = s.open_happ || "Открыть в Happ";
    renderQr(url);
    bindCopy(url, s.copy, s.copied);
    showEl($("setup-content"));
  }

  function showPasteForm(content) {
    var s = content.setup;
    hide($("setup-loading"));
    hide($("setup-error"));
    hide($("setup-content"));
    $("setup-lead").textContent = s.lead_paste || s.lead_token;
    $("paste-hint").textContent = s.paste_hint || "";
    $("paste-label").textContent = s.paste_label || "Ссылка";
    $("setup-paste-input").placeholder = s.paste_placeholder || "";
    $("btn-paste-submit").textContent = s.paste_submit || "Показать QR";
    $("no-access-title").textContent = s.no_access_title || "";
    $("no-access-body").textContent = s.no_access_body || "";
    showEl($("setup-paste"));
    $("setup-paste-input").focus();
  }

  function bindPasteForm(content) {
    var input = $("setup-paste-input");
    var submit = $("btn-paste-submit");
    function tryPaste() {
      var url = normalizeSubUrl(input.value);
      if (!url || !isValidSubUrl(url)) {
        showError(content.setup.paste_invalid);
        showPasteForm(content);
        return;
      }
      $("setup-lead").textContent = content.setup.lead_token;
      showSetupResult(url, content);
    }
    submit.addEventListener("click", tryPaste);
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") tryPaste();
    });
  }

  fetch("content/ru.json")
    .then(function (r) {
      return r.json();
    })
    .then(function (content) {
      var s = content.setup;
      $("setup-title").textContent = s.title;
      bindPasteForm(content);

      if (!token) {
        showPasteForm(content);
        return;
      }

      showEl($("setup-loading"));
      $("setup-lead").textContent = s.lead_token || s.lead;

      fetch("api/verify?t=" + encodeURIComponent(token))
        .then(function (r) {
          return r.json().then(function (j) {
            return { code: r.status, body: j };
          });
        })
        .then(function (res) {
          if (!res.body.ok || !res.body.sub_url) {
            $("setup-error").textContent = s.invalid_token;
            showPasteForm(content);
            showEl($("setup-error"));
            return;
          }
          showSetupResult(res.body.sub_url, content);
        })
        .catch(function () {
          showError(content.errors.generic);
        });
    })
    .catch(function () {
      showError("Не удалось загрузить тексты страницы.");
    });
})();
