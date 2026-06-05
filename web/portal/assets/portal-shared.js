/** Shared portal helpers: footer, status URL, legal paths. */
(function (global) {
  "use strict";

  function isLocalDev() {
    var h = (window.location.hostname || "").toLowerCase();
    return h === "127.0.0.1" || h === "localhost";
  }

  function statusPageUrl() {
    if (isLocalDev()) {
      return "/status.html";
    }
    return "/status";
  }

  function legalTermsUrl() {
    return "/portal/legal/terms.html";
  }

  function legalPrivacyUrl() {
    return "/portal/legal/privacy.html";
  }

  function bindStatusLinks(root) {
    var scope = root || document;
    scope.querySelectorAll("[data-bvpn-status]").forEach(function (el) {
      el.setAttribute("href", statusPageUrl());
    });
  }

  function renderSiteFooter(mount, content) {
    if (!mount || !content) return;
    var f = content.footer || {};
    var items = [
      { href: "/start/", label: f.home || "Главная" },
      { href: "/portal/guide.html", label: f.guide || "Инструкция" },
      { href: statusPageUrl(), label: f.status || "Статус", attr: "data-bvpn-status" },
      {
        href: "https://t.me/Bender_KVN_bot",
        label: f.support || "Поддержка",
        external: true,
      },
      { href: legalPrivacyUrl(), label: f.privacy || "Политика конфиденциальности" },
      { href: legalTermsUrl(), label: f.terms || "Условия пользования" },
    ];
    mount.className = "site-footer";
    mount.innerHTML = "";
    var nav = document.createElement("nav");
    nav.className = "site-footer__nav";
    nav.setAttribute("aria-label", "Навигация сайта");
    items.forEach(function (item, idx) {
      if (idx > 0) {
        var sep = document.createElement("span");
        sep.className = "site-footer__sep";
        sep.setAttribute("aria-hidden", "true");
        sep.textContent = "·";
        nav.appendChild(sep);
      }
      var a = document.createElement("a");
      a.className = "site-footer__link";
      a.href = item.href;
      a.textContent = item.label;
      if (item.attr) a.setAttribute(item.attr, "1");
      if (item.external) {
        a.target = "_blank";
        a.rel = "noopener";
      }
      nav.appendChild(a);
    });
    mount.appendChild(nav);
    if (isLocalDev()) {
      var note = document.createElement("p");
      note.className = "site-footer__note muted";
      note.textContent =
        f.local_status_note ||
        "Локальный просмотр. В продакшене здесь открывается публичная страница статуса сервиса.";
      mount.appendChild(note);
    }
    bindStatusLinks(mount);
  }

  function renderSupportBlock(mount, content) {
    if (!mount || !content) return;
    var s = content.support || {};
    mount.className = "support-block glass";
    mount.innerHTML = "";
    var h = document.createElement("h2");
    h.className = "sheet__label";
    h.textContent = s.title || "Поддержка";
    mount.appendChild(h);
    var tg = document.createElement("a");
    tg.className = "btn btn--secondary btn--block";
    tg.href = s.telegram_url || "https://t.me/Bender_KVN_bot";
    tg.target = "_blank";
    tg.rel = "noopener";
    tg.textContent = s.telegram_label || "Telegram";
    mount.appendChild(tg);
    if (s.email_value) {
      var emailNote = document.createElement("p");
      emailNote.className = "muted support-block__email";
      emailNote.innerHTML =
        (s.email_label || "Email") +
        ': <a class="site-footer__link" href="mailto:' +
        s.email_value +
        '">' +
        s.email_value +
        "</a>";
      mount.appendChild(emailNote);
    }
    if (s.message_hint) {
      var hint = document.createElement("p");
      hint.className = "muted support-block__hint";
      hint.textContent = s.message_hint;
      mount.appendChild(hint);
    }
  }

  global.BenderPortalShared = {
    isLocalDev: isLocalDev,
    statusPageUrl: statusPageUrl,
    legalTermsUrl: legalTermsUrl,
    legalPrivacyUrl: legalPrivacyUrl,
    bindStatusLinks: bindStatusLinks,
    renderSiteFooter: renderSiteFooter,
    renderSupportBlock: renderSupportBlock,
  };
})(typeof window !== "undefined" ? window : globalThis);
