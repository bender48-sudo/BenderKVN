(function () {
  "use strict";

  var CONTENT_URL = "/portal/content/ru.json";

  function $(id) {
    return document.getElementById(id);
  }

  function pickCode() {
    var p = new URLSearchParams(window.location.search);
    var c = (p.get("code") || "").trim();
    if (window.location.hash) {
      c = window.location.hash.replace(/^#/, "").trim() || c;
    }
    return c;
  }

  function renderItems(items, highlight) {
    var list = $("errors-list");
    if (!list) return;
    list.innerHTML = "";
    (items || []).forEach(function (item) {
      var card = document.createElement("article");
      card.className = "error-card panel";
      card.setAttribute("role", "listitem");
      card.id = "err-" + item.id;
      if (highlight && item.id === highlight) {
        card.classList.add("error-card--highlight");
      }
      var h = document.createElement("h2");
      h.textContent = item.title;
      card.appendChild(h);
      if (item.symptom) {
        var sym = document.createElement("p");
        sym.className = "muted";
        sym.textContent = item.symptom;
        card.appendChild(sym);
      }
      if (item.steps && item.steps.length) {
        var ol = document.createElement("ol");
        ol.className = "steps";
        item.steps.forEach(function (step) {
          var li = document.createElement("li");
          li.textContent = step;
          ol.appendChild(li);
        });
        card.appendChild(ol);
      }
      list.appendChild(card);
    });
    if (highlight) {
      var el = document.getElementById("err-" + highlight);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  fetch(CONTENT_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("content");
      return r.json();
    })
    .then(function (data) {
      var block = data.user_errors || {};
      $("errors-title").textContent = block.title || "Частые ошибки";
      document.title = (block.title || "BenderVPN") + " — помощь";
      $("errors-lead").textContent = block.lead || "";
      if (block.setup_button && $("btn-errors-setup")) {
        $("btn-errors-setup").textContent = block.setup_button;
      }
      if (block.support_button && $("btn-errors-support")) {
        $("btn-errors-support").textContent = block.support_button;
      }
      renderItems(block.items || [], pickCode());
    })
    .catch(function () {
      $("errors-lead").textContent =
        "Не удалось загрузить тексты. Обновите страницу или напишите в поддержку.";
    });
})();
