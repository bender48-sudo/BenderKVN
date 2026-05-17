(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var token = params.get("t") || "";

  function $(id) {
    return document.getElementById(id);
  }

  function showError(msg) {
    $("setup-loading").classList.add("hidden");
    $("setup-content").classList.add("hidden");
    $("setup-error").textContent = msg;
    $("setup-error").classList.remove("hidden");
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
    btn.textContent = labelCopy;
    btn.addEventListener("click", function () {
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
    });
  }

  fetch("content/ru.json")
    .then(function (r) {
      return r.json();
    })
    .then(function (content) {
      var s = content.setup;
      $("setup-title").textContent = s.title;
      $("setup-lead").textContent = s.lead;
      $("btn-copy").textContent = s.copy;

      if (!token) {
        showError(s.invalid_token);
        return;
      }

      fetch("api/verify?t=" + encodeURIComponent(token))
        .then(function (r) {
          return r.json().then(function (j) {
            return { code: r.status, body: j };
          });
        })
        .then(function (res) {
          if (!res.body.ok || !res.body.sub_url) {
            showError(s.invalid_token);
            return;
          }
          var url = res.body.sub_url;
          $("setup-link").textContent = url;
          $("setup-link").href = url;
          $("btn-open-happ").href = url;
          renderQr(url);
          bindCopy(url, s.copy, s.copied);
          $("setup-loading").classList.add("hidden");
          $("setup-content").classList.remove("hidden");
        })
        .catch(function () {
          showError(content.errors.generic);
        });
    })
    .catch(function () {
      showError("Не удалось загрузить тексты страницы.");
    });
})();
