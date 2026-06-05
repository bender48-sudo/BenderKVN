/** Shared portal helpers: footer, status URL, legal paths. */
(function (global) {
  "use strict";

  var PROD_STATUS_FALLBACK =
    "https://k9x2m1.conntest.xyz:8443/status";

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
        (f.local_status_note || "") +
        " Прод: " +
        PROD_STATUS_FALLBACK;
      mount.appendChild(note);
    }
    bindStatusLinks(mount);
  }

  global.BenderPortalShared = {
    isLocalDev: isLocalDev,
    statusPageUrl: statusPageUrl,
    legalTermsUrl: legalTermsUrl,
    legalPrivacyUrl: legalPrivacyUrl,
    bindStatusLinks: bindStatusLinks,
    renderSiteFooter: renderSiteFooter,
  };
})(typeof window !== "undefined" ? window : globalThis);
