(function () {
  "use strict";

  const CONTENT_URL = "/portal/content/ru.json";
  const STATUS_JSON = "/api/ops/status.json";
  function statusPageUrl() {
    if (window.BenderPortalShared) return BenderPortalShared.statusPageUrl();
    return "/status";
  }
  const SUPPORT_URL = "https://t.me/Bender_KVN_bot";
  const SETUP_PATH = "/setup/";
  const API_FUNNEL = "/setup/api/funnel-event";
  const API_CABINET = "/setup/api/cabinet";
  const API_CAPACITY = "/setup/api/capacity";
  const API_TELEGRAM_SETUP = "/setup/api/telegram-setup";
  const REF_KEY = "bvpn_ref_code";
  const ACK_KEY = "bvpn_vpn_config_ack";
  const SUB_URL_KEY = "bvpn_subscription_url";
  const CID_KEY = "bvpn_customer_id";
  const EMAIL_KEY = "bvpn_customer_email";

  let content = null;

  function $(id) {
    return document.getElementById(id);
  }

  function show(viewId) {
    document.querySelectorAll("[data-view]").forEach(function (el) {
      el.classList.toggle("hidden", el.getAttribute("data-view") !== viewId);
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

  function normalizeSubUrl(url) {
    var u = (url || "").trim();
    if (!u) return u;
    return u
      .replace("://p4n7q.conntest.xyz:2053", "://p4n7q.conntest.xyz:8443")
      .replace("://k9x2m1.conntest.xyz:2053", "://k9x2m1.conntest.xyz:8443");
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return Promise.reject(new Error("clipboard unavailable"));
  }

  function showToast(msg, kind) {
    var text = (msg || "").trim();
    if (!text) return;
    var root = $("toast-root");
    var inline = $("portal-toast");
    if (inline) {
      inline.textContent = text;
      inline.className =
        "banner " + (kind === "error" ? "banner--error" : "banner--warn");
      inline.classList.remove("hidden");
      setTimeout(function () {
        inline.classList.add("hidden");
      }, 6000);
    }
    if (!root) return;
    var el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("role", "status");
    el.textContent = text;
    root.appendChild(el);
    requestAnimationFrame(function () {
      el.classList.add("toast--visible");
    });
    setTimeout(function () {
      el.classList.remove("toast--visible");
      setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 220);
    }, 5200);
  }

  function hasStoredSetup() {
    try {
      if (readStoredSubscriptionUrl()) return true;
      if (localStorage.getItem(CID_KEY)) return true;
      if (localStorage.getItem(EMAIL_KEY)) return true;
    } catch (e) {
      /* ignore */
    }
    return false;
  }

  function initTelegram() {
    if (!isTelegramMiniApp()) return;
    var tg = getTelegramWebApp();
    if (!tg) return;
    document.documentElement.classList.add("tg-webapp");
    tg.ready();
    tg.expand();
    try {
      tg.enableClosingConfirmation();
    } catch (e) {
      /* older clients */
    }
    var tp = tg.themeParams || {};
    var cssMap = {
      bg_color: "--bg",
      text_color: "--text",
      hint_color: "--muted",
      secondary_bg_color: "--bg-card",
    };
    Object.keys(cssMap).forEach(function (key) {
      if (tp[key]) {
        document.documentElement.style.setProperty(cssMap[key], tp[key]);
      }
    });
    if (typeof tg.setHeaderColor === "function" && tp.bg_color) {
      try {
        tg.setHeaderColor(tp.bg_color);
      } catch (e) {
        /* ignore */
      }
    }
    if (typeof tg.setBackgroundColor === "function" && tp.bg_color) {
      try {
        tg.setBackgroundColor(tp.bg_color);
      } catch (e) {
        /* ignore */
      }
    }
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

  function trackFunnel(event) {
    try {
      fetch(API_FUNNEL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: event }),
        keepalive: true,
      }).catch(function () {});
    } catch (e) {
      /* ignore */
    }
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

  function openTelegramSetup(ev) {
    if (ev) ev.preventDefault();
    var tid = getTelegramUserId();
    if (!isTelegramMiniApp() && tid <= 0) {
      window.location.href = SETUP_PATH;
      return;
    }
    trackFunnel("portal_tg_setup");
    if (!tid) {
      showToast(
        "Не удалось определить Telegram. Закрой Mini App и открой снова из бота.",
        "error"
      );
      return;
    }
    postJson(API_TELEGRAM_SETUP, { telegram_id: tid })
      .then(function (res) {
        if (res.body && res.body.sub_url) {
          try {
            localStorage.setItem(SUB_URL_KEY, normalizeSubUrl(res.body.sub_url));
          } catch (e) {
            /* ignore */
          }
        }
        if (res.body && res.body.ok && res.body.setup_page_url) {
          if (isTelegramMiniApp()) {
            window.location.href = res.body.setup_page_url;
          } else {
            openExternal(res.body.setup_page_url);
          }
          return;
        }
        var msg =
          (res.body && res.body.message) ||
          (content.setup && content.setup.error_no_subscription) ||
          "Сначала получите доступ в боте.";
        if (res.body && res.body.bot_url) {
          if (isTelegramMiniApp()) {
            openExternal(res.body.bot_url);
          } else {
            window.location.href = res.body.bot_url;
          }
        }
        showToast(msg, "error");
      })
      .catch(function () {
        showToast(content.errors.generic, "error");
      });
  }

  function bindSetupEntryButtons() {
    var el = $("btn-cabinet-setup");
    if (!el) return;
    el.addEventListener("click", function (ev) {
      if (isTelegramMiniApp() || getTelegramUserId() > 0) {
        openTelegramSetup(ev);
      }
    });
  }

  function readAckGeneration() {
    try {
      var raw = localStorage.getItem(ACK_KEY);
      if (raw === null || raw === "") return 0;
      return parseInt(raw, 10) || 0;
    } catch (e) {
      return 0;
    }
  }

  function writeAckGeneration(gen) {
    try {
      localStorage.setItem(ACK_KEY, String(gen));
    } catch (e) {
      /* private mode */
    }
  }

  function setEventsState(mode, ev) {
    var dot = $("events-pill");
    var detail = $("events-detail");
    var steps = $("events-steps");
    var ackBtn = $("btn-events-ack");
    if (!dot || !detail || !ev) return;

    dot.className = "status__dot";
    dot.textContent = "";
    dot.setAttribute("aria-label", "");
    steps.classList.add("hidden");
    ackBtn.classList.add("hidden");

    if (mode === "ok") {
      dot.classList.add("status__dot--ok");
      dot.setAttribute("aria-label", ev.ok_pill || "Всё в порядке");
      detail.textContent = ev.ok_detail;
    } else if (mode === "refresh") {
      dot.classList.add("status__dot--action");
      dot.setAttribute("aria-label", ev.refresh_pill || "Нужно обновить");
      detail.textContent = ev.refresh_detail;
      steps.classList.remove("hidden");
      steps.innerHTML = "";
      (ev.refresh_steps || []).forEach(function (t) {
        var li = document.createElement("li");
        li.textContent = t;
        steps.appendChild(li);
      });
      ackBtn.classList.remove("hidden");
    } else if (mode === "incident") {
      dot.classList.add("status__dot--incident");
      dot.setAttribute("aria-label", ev.incident_pill || "Сбой");
      detail.textContent = ev.incident_detail;
    }
  }

  function loadEvents() {
    var ev = content.events || {};
    $("events-title").textContent = ev.title || "Обновления VPN";
    $("btn-events-ack").textContent = ev.refresh_ack || "Я обновил в Happ";
    var more = $("btn-events-more");
    more.textContent = ev.more || content.buttons.status;
    more.href = statusPageUrl();
    more.setAttribute("data-bvpn-status", "1");
    bindExternalLink(more);
    var navStatus = $("nav-status-link");
    if (navStatus) {
      navStatus.href = statusPageUrl();
      navStatus.setAttribute("data-bvpn-status", "1");
      bindExternalLink(navStatus);
    }
    if (window.BenderPortalShared) BenderPortalShared.bindStatusLinks(document);

    fetch(STATUS_JSON)
      .then(function (r) {
        if (!r.ok) throw new Error("status json");
        return r.json();
      })
      .then(function (doc) {
        var cfg = doc.vpn_config || {};
        var gen = parseInt(cfg.generation, 10) || 0;
        var ack = readAckGeneration();
        var overall = doc.overall || "ok";

        if (overall !== "ok") {
          setEventsState("incident", ev);
          return;
        }
        if (gen > 0 && gen > ack) {
          setEventsState("refresh", ev);
          return;
        }
        setEventsState("ok", ev);
      })
      .catch(function () {
        setEventsState("ok", ev);
      });
  }

  function renderFaq() {
    var faq = content.faq;
    var list = $("faq-list");
    var title = $("faq-fold-title");
    if (!faq || !list) return;
    if (title) title.textContent = faq.title || "Частые вопросы";
    list.innerHTML = "";
    (faq.items || []).forEach(function (item) {
      var det = document.createElement("details");
      det.className = "faq__item";
      var sum = document.createElement("summary");
      sum.textContent = item.q || "";
      var p = document.createElement("p");
      p.textContent = item.a || "";
      det.appendChild(sum);
      det.appendChild(p);
      list.appendChild(det);
    });
  }

  function updateHomeCtas() {
    var tg = isTelegramMiniApp();
    var btns = content.buttons || {};
    var primary = $("btn-setup");
    var secondary = $("btn-setup-secondary");
    var connect = $("btn-connect");
    var topup = $("btn-topup");
    var sepTopup = $("sep-topup");
    if (!primary) return;

    if (tg) {
      primary.textContent = btns.setup_tg || "Открыть настройку в Happ";
      primary.href = "#";
      primary.classList.remove("hidden");
      if (secondary) secondary.classList.add("hidden");
      var landing = $("landing-paths");
      if (landing) landing.classList.add("hidden");
      if (connect) {
        connect.textContent = btns.connect || "Инструкция по устройству";
        connect.classList.remove("hidden");
      }
      if (topup) {
        topup.textContent = btns.topup_bot || "Пополнить в боте";
        topup.href = "https://t.me/Bender_KVN_bot";
        topup.classList.remove("hidden");
      }
      if (sepTopup) sepTopup.classList.remove("hidden");
      var fold = $("account-fold");
      if (fold) fold.open = true;
      return;
    }

    if (hasStoredSetup()) {
      primary.textContent = btns.connect || "Подключить устройство";
      primary.href = "#";
      primary.classList.add("btn--primary");
      if (secondary) {
        secondary.textContent = btns.connect_setup || "Обновить настройку";
        secondary.href = SETUP_PATH;
        secondary.classList.remove("hidden");
      }
      if (connect) {
        connect.textContent = btns.connect_guide || "Инструкция по шагам";
        connect.classList.remove("hidden");
      }
      var foldHas = $("account-fold");
      if (foldHas && (localStorage.getItem(EMAIL_KEY) || localStorage.getItem(CID_KEY))) {
        foldHas.open = true;
      }
    } else {
      primary.textContent = btns.landing_tg || btns.setup_browser_alt || "Telegram";
      primary.href = botUrlWithReferral();
      bindExternalLink(primary);
      primary.classList.remove("hidden");
      if (secondary) secondary.classList.add("hidden");
      if (connect) {
        connect.textContent = btns.connect_guide || "Инструкция по шагам";
        connect.classList.remove("hidden");
      }
      var blocked = $("tg-blocked-banner");
      if (blocked) blocked.classList.remove("hidden");
    }
    if (topup) topup.classList.add("hidden");
    if (sepTopup) sepTopup.classList.add("hidden");
  }

  function preserveReferralFromUrl() {
    try {
      var params = new URLSearchParams(window.location.search || "");
      var ref = (params.get("ref") || "").trim();
      if (!ref && window.location.hash.indexOf("ref_") >= 0) {
        ref = window.location.hash.replace(/^#/, "").replace(/^ref_/, "");
      }
      if (ref) {
        localStorage.setItem(REF_KEY, ref);
      }
    } catch (e) {
      /* ignore */
    }
  }

  function botUrlWithReferral() {
    var base = "https://t.me/Bender_KVN_bot";
    try {
      var ref = localStorage.getItem(REF_KEY) || "";
      if (ref) return base + "?start=ref_" + encodeURIComponent(ref);
    } catch (e2) {
      /* ignore */
    }
    return base;
  }

  function loadCapacity() {
    var card = $("slots-card");
    var home = content.home || {};
    if (!card) return;
    if (isTelegramMiniApp()) {
      card.classList.add("hidden");
      return;
    }
    if ($("slots-title") && home.slots_title) {
      $("slots-title").textContent = home.slots_title;
    }
    fetch(API_CAPACITY, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(function (r) {
        return r.json();
      })
      .then(function (doc) {
        if (!doc || !doc.ok) throw new Error("capacity");
        var val = $("slots-value");
        var hint = $("slots-hint");
        var cap = doc.access_cap || 30000;
        if (!doc.registration_open) {
          if (val) val.textContent = "0";
          if (hint) hint.textContent = home.slots_closed || "";
        } else {
          var fmt = home.slots_format || "{remaining} мест";
          if (val) {
            val.textContent = fmt.replace(
              "{remaining}",
              String(doc.remaining_slots)
            );
          }
          var capNote = $("slots-cap");
          if (capNote) {
            var capFmt = home.slots_cap_note || "из {cap}";
            capNote.textContent = capFmt.replace("{cap}", String(cap));
          }
          if (hint) {
            var hintFmt = home.slots_hint_live || "";
            hint.textContent = hintFmt.replace(
              "{active}",
              String(doc.active_configurations)
            );
          }
        }
        card.classList.remove("hidden");
      })
      .catch(function () {
        if ($("slots-value")) {
          $("slots-value").textContent =
            home.slots_unavailable || "Количество мест обновляется";
        }
        if ($("slots-hint")) $("slots-hint").textContent = "";
        var capNote = $("slots-cap");
        if (capNote) capNote.textContent = "";
        card.classList.remove("hidden");
      });
  }

  function renderJourney() {
    var panel = $("landing-journey");
    var home = content.home || {};
    if (!panel || isTelegramMiniApp()) {
      if (panel) panel.classList.add("hidden");
      return;
    }
    var title = $("journey-title");
    var list = $("journey-steps");
    var steps = home.journey_steps || [];
    if (!steps.length) {
      panel.classList.add("hidden");
      return;
    }
    if (title && home.journey_title) title.textContent = home.journey_title;
    if (list) {
      list.innerHTML = "";
      steps.forEach(function (step, idx) {
        var li = document.createElement("li");
        li.className = "journey-steps__item";
        li.innerHTML =
          '<span class="journey-steps__num" aria-hidden="true">' +
          (idx + 1) +
          "</span><span>" +
          step +
          "</span>";
        list.appendChild(li);
      });
    }
    panel.classList.remove("hidden");
  }

  function renderReferralWelcome() {
    var panel = $("referral-welcome");
    var home = content.home || {};
    if (!panel || isTelegramMiniApp()) {
      if (panel) panel.classList.add("hidden");
      return;
    }
    var hasRef = false;
    try {
      hasRef = !!localStorage.getItem(REF_KEY);
    } catch (e) {
      hasRef = false;
    }
    if (!hasRef) {
      panel.classList.add("hidden");
      return;
    }
    if ($("referral-welcome-title") && home.referral_welcome_title) {
      $("referral-welcome-title").textContent = home.referral_welcome_title;
    }
    if ($("referral-welcome-lead") && home.referral_welcome_lead) {
      $("referral-welcome-lead").textContent = home.referral_welcome_lead;
    }
    if ($("referral-welcome-hint") && home.referral_welcome_hint) {
      $("referral-welcome-hint").textContent = home.referral_welcome_hint;
    }
    panel.classList.remove("hidden");
  }

  function renderLandingPaths() {
    var panel = $("landing-paths");
    var home = content.home || {};
    var btns = content.buttons || {};
    if (!panel || isTelegramMiniApp()) {
      if (panel) panel.classList.add("hidden");
      return;
    }
    if ($("landing-paths-title") && home.landing_paths_title) {
      $("landing-paths-title").textContent = home.landing_paths_title;
    }
    if ($("landing-tg-lead") && home.landing_tg_lead) {
      $("landing-tg-lead").textContent = home.landing_tg_lead;
    }
    if ($("landing-email-lead") && home.landing_email_lead) {
      $("landing-email-lead").textContent = home.landing_email_lead;
    }
    var tgBtn = $("btn-landing-tg");
    if (tgBtn) {
      tgBtn.textContent = btns.landing_tg || btns.setup_browser_alt || "Telegram";
      tgBtn.href = botUrlWithReferral();
      bindExternalLink(tgBtn);
    }
    var emBtn = $("btn-landing-email");
    if (emBtn) {
      emBtn.textContent = btns.landing_email || btns.setup_browser || "Email";
      emBtn.href = SETUP_PATH;
    }
    var refNote = $("referral-note");
    if (refNote) {
      try {
        if (localStorage.getItem(REF_KEY)) {
          refNote.classList.add("hidden");
        } else if (home.invite_model_note) {
          refNote.textContent = home.invite_model_note;
          refNote.classList.remove("hidden");
        }
      } catch (e) {
        /* ignore */
      }
    }
    panel.classList.remove("hidden");
  }

  function renderPhilosophy() {
    var pos = content.positioning;
    var body = $("fold-about-body");
    var title = $("fold-about-title");
    if (!pos || !body) return;
    if (title) title.textContent = content.home.about_fold_title || "О сервисе";
    var blocks = [
      ["invite_title", "invite_body"],
      ["limit_title", "limit_body"],
      ["support_title", "support_body"],
    ];
    body.innerHTML = "";
    blocks.forEach(function (pair) {
      if (!pos[pair[0]]) return;
      var block = document.createElement("p");
      block.innerHTML =
        "<strong>" +
        pos[pair[0]] +
        "</strong> " +
        (pos[pair[1]] || "").replace(/\n\n/g, " ");
      body.appendChild(block);
    });
  }

  function renderHome() {
    var home = content.home;
    var tg = isTelegramMiniApp();
    $("page-title").textContent = home.title;
    var badge = $("hero-badge");
    if (badge && home.hero_badge) {
      var badgeText = tg && home.hero_badge_tg
        ? home.hero_badge_tg
        : home.hero_badge;
      badge.textContent = badgeText;
      badge.classList.remove("hidden");
    } else if (badge) {
      badge.classList.add("hidden");
    }
    var sub = $("page-subtitle");
    if (sub) {
      sub.textContent = tg
        ? home.subtitle_tg || home.hero_title || home.subtitle || ""
        : home.hero_title || home.subtitle || "";
    }
    var lead = $("hero-lead");
    if (lead && home.hero_lead) {
      lead.textContent = home.hero_lead;
    }
    var eyebrow = $("hero-eyebrow");
    if (eyebrow && home.hero_eyebrow && !tg) {
      eyebrow.textContent = home.hero_eyebrow;
      eyebrow.classList.remove("hidden");
    } else if (eyebrow) {
      eyebrow.classList.add("hidden");
    }
    if ($("devices-note") && home.devices_note) {
      $("devices-note").textContent = home.devices_note;
    }
    var foldTitle = $("account-fold-title");
    if (foldTitle && home.account_fold_title) {
      foldTitle.textContent = home.account_fold_title;
    }
    var cabBtn = $("btn-cabinet");
    if (cabBtn) cabBtn.textContent = content.buttons.cabinet || "Мой доступ";
    renderPhilosophy();
    renderFaq();
    updateHomeCtas();
    var guideBtn = $("btn-guide");
    if (guideBtn && content.buttons.watch_guide) {
      guideBtn.textContent = content.buttons.watch_guide;
      guideBtn.href = "/portal/guide.html";
    }
    var supportBtn = $("btn-support");
    if (supportBtn) {
      supportBtn.textContent = content.buttons.support;
      supportBtn.href = SUPPORT_URL;
    }
    bindExternalLink(supportBtn);
    bindExternalLink($("btn-topup"));
    $("btn-stuck").textContent = content.buttons.stuck;
    var errBtn = $("btn-help-errors");
    if (errBtn && content.buttons.help_errors) {
      errBtn.textContent = content.buttons.help_errors;
    }
    var help = content.help || {};
    if ($("help-stuck-title") && help.stuck_title) {
      $("help-stuck-title").textContent = help.stuck_title;
    }
    if ($("help-stuck-steps") && help.stuck_steps) {
      var helpList = $("help-stuck-steps");
      helpList.innerHTML = "";
      help.stuck_steps.forEach(function (step) {
        var li = document.createElement("li");
        li.textContent = step;
        helpList.appendChild(li);
      });
    }
    if ($("tg-blocked-title") && content.telegram_blocked) {
      $("tg-blocked-title").textContent = content.telegram_blocked.title;
    }
    if ($("tg-blocked-body") && content.telegram_blocked) {
      $("tg-blocked-body").textContent = " " + (content.telegram_blocked.body || "");
    }
    var blockedBanner = $("tg-blocked-banner");
    if (blockedBanner) {
      if (tg || hasStoredSetup()) {
        blockedBanner.classList.add("hidden");
      }
    }
    if ($("happ-note") && content.happ) {
      $("happ-note").textContent = content.happ.phone_and_pc;
    }
    preserveReferralFromUrl();
    loadCapacity();
    renderLandingPaths();
    renderReferralWelcome();
    renderJourney();
    loadEvents();
  }

  function focusAccountSheet() {
    var sheet = $("account-sheet");
    if (sheet) {
      sheet.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function renderDevices() {
    var screens = content.screens || {};
    if ($("devices-heading") && screens.devices_heading) {
      $("devices-heading").textContent = screens.devices_heading;
    }
    if ($("devices-lead") && screens.devices_lead) {
      $("devices-lead").textContent = screens.devices_lead;
    }
    var grid = $("device-grid");
    grid.innerHTML = "";
    content.devices.forEach(function (dev) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "device-card";
      btn.setAttribute("data-device-id", dev.id);
      btn.innerHTML =
        '<span class="icon" aria-hidden="true">' +
        dev.icon +
        "</span>" +
        dev.label;
      btn.setAttribute("role", "listitem");
      btn.setAttribute("aria-label", dev.label);
      btn.addEventListener("click", function () {
        try {
          history.replaceState(null, "", "#device=" + dev.id);
        } catch (e) {
          window.location.hash = "device=" + dev.id;
        }
        trackFunnel("portal_device_" + dev.id);
        showDeviceDetail(dev.id);
      });
      grid.appendChild(btn);
    });
  }

  function readStoredSubscriptionUrl() {
    try {
      return (localStorage.getItem(SUB_URL_KEY) || "").trim();
    } catch (e) {
      return "";
    }
  }

  function renderDeviceSubscriptionQr(subUrl) {
    var panel = $("device-qr-panel");
    var canvas = $("device-sub-qr");
    var missing = $("device-qr-missing");
    var qrCopy = (content && content.device_qr) || {};
    if ($("device-qr-title")) {
      $("device-qr-title").textContent = qrCopy.title || "QR для Happ";
    }
    if ($("device-qr-hint")) {
      $("device-qr-hint").textContent = qrCopy.hint || "";
    }
    if (!panel || !canvas) return;
    panel.classList.remove("hidden");
    if (!subUrl) {
      if (canvas) canvas.classList.add("hidden");
      if (missing) {
        missing.textContent =
          qrCopy.missing ||
          "Сначала получите настройку на странице «Получить бесплатный VPN».";
        missing.classList.remove("hidden");
      }
      return;
    }
    if (canvas) canvas.classList.remove("hidden");
    if (missing) missing.classList.add("hidden");
    if (window.QRCode) {
      QRCode.toCanvas(
        canvas,
        subUrl,
        { width: 220, margin: 2, color: { dark: "#e85d04", light: "#ffffff" } },
        function (err) {
          if (err && missing) {
            missing.textContent =
              (content.setup && content.setup.qr_fallback) ||
              "QR не загрузился. Скопируй ссылку.";
            missing.classList.remove("hidden");
          }
        }
      );
    } else if (missing) {
      missing.textContent =
        (content.setup && content.setup.qr_fallback) ||
        "QR не загрузился. Скопируй ссылку.";
      missing.classList.remove("hidden");
    }
  }

  function showDeviceDetail(deviceId) {
    var dev = content.devices.find(function (d) {
      return d.id === deviceId;
    });
    if (!dev) return;
    renderDeviceSubscriptionQr(readStoredSubscriptionUrl());
    var screens = content.screens || {};
    if ($("install-steps-title") && screens.install_steps_title) {
      $("install-steps-title").textContent = screens.install_steps_title;
    }
    if ($("after-title") && screens.after_title) {
      $("after-title").textContent = screens.after_title;
    }
    $("device-detail-title").textContent = dev.install_title;
    var list = $("device-install-steps");
    list.innerHTML = "";
    var storeKey = dev.install_store_key || dev.id;
    var stores = content.happ_install || {};
    var store = stores[storeKey] || stores.generic;
    var tunCallout = $("device-tun-callout");
    if (tunCallout) {
      if (dev.tun_callout) {
        tunCallout.textContent = dev.tun_callout;
        tunCallout.classList.remove("hidden");
      } else {
        tunCallout.classList.add("hidden");
      }
    }
    var steps = dev.install_steps || [];
    steps.forEach(function (step, idx) {
      var li = document.createElement("li");
      li.textContent = step;
      if (idx === 0 && store) {
        var a = document.createElement("a");
        a.className = "store-link";
        a.href = store.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "↓ " + store.label;
        li.appendChild(document.createElement("br"));
        li.appendChild(a);
      }
      list.appendChild(li);
    });
    if (dev.alt_client && dev.id === "windows") {
      var note = document.createElement("p");
      note.className = "muted";
      note.textContent = dev.alt_client;
      list.parentElement.appendChild(note);
    }
    var after = $("after-device-steps");
    after.innerHTML = "";
    (content.steps.after_device || []).slice(0, 2).forEach(function (step) {
      var li = document.createElement("li");
      li.textContent = step;
      after.appendChild(li);
    });
    show("device");
  }

  function renderCabinetSupportCards() {
    var cab = content.cabinet || {};
    var wrap = $("cabinet-support-cards");
    if (!wrap) return;
    wrap.innerHTML = "";
    [
      [cab.support_phone_title, cab.support_phone_body],
      [cab.support_link_title, cab.support_link_body],
    ].forEach(function (pair) {
      if (!pair[0]) return;
      var card = document.createElement("div");
      card.className = "support-card";
      card.innerHTML = "<strong>" + pair[0] + "</strong>" + (pair[1] || "");
      wrap.appendChild(card);
    });
    var support = document.createElement("a");
    support.className = "btn btn--ghost btn--block";
    support.href = SUPPORT_URL;
    support.textContent = content.buttons.support || "Написать в поддержку";
    bindExternalLink(support);
    wrap.appendChild(support);
  }

  function renderCabinet() {
    var cab = content.cabinet || {};
    var tg = isTelegramMiniApp();
    if ($("cabinet-title")) {
      $("cabinet-title").textContent = cab.title || "Личный кабинет";
    }
    if ($("cabinet-lead")) {
      $("cabinet-lead").textContent = tg ? cab.lead_tg : cab.lead_web;
    }
    if ($("cabinet-lead-inline")) {
      $("cabinet-lead-inline").textContent = tg ? cab.lead_tg : cab.lead_web;
    }
    if ($("cabinet-configs-title")) {
      $("cabinet-configs-title").textContent = cab.configs_title || "Конфигурации";
    }
    if ($("cabinet-device-rule")) {
      $("cabinet-device-rule").textContent = cab.configs_device_rule || "";
    }
    if ($("btn-new-device")) {
      $("btn-new-device").textContent = cab.new_device_cta || "Новое устройство";
      $("btn-new-device").href = botUrlWithReferral();
      bindExternalLink($("btn-new-device"));
    }
    renderCabinetSupportCards();
    $("cabinet-balance-label").textContent = cab.balance_label || "Баланс";
    $("cabinet-balance").textContent = cab.balance_na || "—";
    $("cabinet-balance-hint").textContent = cab.balance_hint || "";
    if ($("cabinet-customer-id-label")) {
      $("cabinet-customer-id-label").textContent = cab.customer_id_label || "BVPN-ID";
    }
    if ($("cabinet-email-label")) {
      $("cabinet-email-label").textContent = cab.email_label || "Email";
    }
    if ($("btn-cabinet-load")) {
      $("btn-cabinet-load").textContent = cab.load_balance || "Показать баланс";
    }
    if ($("cabinet-web-notify")) {
      $("cabinet-web-notify").textContent = cab.web_notify_lead || "";
    }
    $("btn-cabinet-bot").textContent = cab.open_bot || "Открыть бота";
    if (tg) {
      $("btn-cabinet-setup").textContent =
        cab.setup_tg || content.buttons.setup_tg || "QR для Happ";
      $("btn-cabinet-setup").href = "#";
    } else {
      $("btn-cabinet-setup").textContent = content.buttons.setup_browser;
      $("btn-cabinet-setup").href = SETUP_PATH;
    }
    var bindBtn = $("btn-cabinet-bind");
    if (bindBtn) {
      bindBtn.textContent = cab.bind_tg || "Привязать Telegram";
    }
    bindExternalLink($("btn-cabinet-bot"));
    bindExternalLink(bindBtn);
    try {
      var cid = localStorage.getItem(CID_KEY) || "";
      var em = localStorage.getItem(EMAIL_KEY) || "";
      if ($("cabinet-customer-id") && cid) $("cabinet-customer-id").value = cid;
      if ($("cabinet-email") && em) $("cabinet-email").value = em;
    } catch (e) {
      /* ignore */
    }
    if (tg) {
      var login = $("cabinet-login-panel");
      if (login) login.classList.add("hidden");
    }
  }

  function showCabinetError(msg) {
    var err = $("cabinet-load-error");
    var lead = $("cabinet-lead");
    if (err) {
      err.textContent = msg;
      err.classList.remove("hidden");
    }
    if (lead && isTelegramMiniApp()) {
      lead.textContent = msg;
    }
  }

  function applyCabinetData(doc) {
    var cab = content.cabinet || {};
    var balEl = $("cabinet-balance");
    var err = $("cabinet-load-error");
    if (err) err.classList.add("hidden");
    if (!doc || !doc.ok) {
      var msg =
        (doc && doc.message) ||
        (isTelegramMiniApp()
          ? "Аккаунт не найден. Нажми /start в боте и открой Mini App снова."
          : "Не найдено. Проверь email или ID.");
      showCabinetError(msg);
      if (doc && doc.bot_url) {
        var bindBtn = $("btn-cabinet-bind");
        if (bindBtn) {
          bindBtn.href = doc.bot_url;
          bindBtn.textContent = content.cabinet.open_bot || "Открыть бота";
          bindBtn.classList.remove("hidden");
        }
      }
      return;
    }
    var fmt = cab.balance_format || "{balance} ₽ · ~{days} дн.";
    balEl.textContent = fmt
      .replace("{balance}", String(Math.round(doc.balance_rub)))
      .replace("{days}", String(doc.days_left));
    var hint = $("cabinet-balance-hint");
    if (hint) {
      if (doc.billing_profile === "trial" && cab.balance_hint_trial) {
        hint.textContent = cab.balance_hint_trial;
      } else if (doc.billing_note) {
        hint.textContent = doc.billing_note;
      } else {
        hint.textContent = cab.balance_hint || "";
      }
    }
    if (doc.days_left <= 3) {
      balEl.classList.add("cabinet-balance--low");
    } else {
      balEl.classList.remove("cabinet-balance--low");
    }
    var cfgPanel = $("cabinet-configs-panel");
    var cfgList = $("cabinet-configs-list");
    if (cfgPanel && cfgList && isTelegramMiniApp()) {
      cfgList.innerHTML = "";
      var configs = doc.configurations || [];
      if (!configs.length) {
        var li0 = document.createElement("li");
        li0.textContent = cab.configs_empty || "";
        cfgList.appendChild(li0);
      } else {
        configs.forEach(function (c) {
          var li = document.createElement("li");
          li.textContent = (c.label || "Конфигурация") + " · до " + (c.expires || "—");
          var st = document.createElement("span");
          st.className = "config-list__status";
          st.textContent = c.active ? "активна" : "истекла";
          li.appendChild(st);
          cfgList.appendChild(li);
        });
      }
      cfgPanel.classList.remove("hidden");
    }
    var login = $("cabinet-login-panel");
    if (login && isTelegramMiniApp()) login.classList.add("hidden");
    var botBtn = $("btn-cabinet-bot");
    if (botBtn && doc.bot_url) {
      botBtn.href = doc.bot_url;
    }
    var bindBtn = $("btn-cabinet-bind");
    if (bindBtn) {
      var bindHref = "";
      try {
        bindHref = localStorage.getItem("bvpn_bind_url") || "";
      } catch (e) {
        bindHref = "";
      }
      if (bindHref && !doc.telegram_bound) {
        bindBtn.href = bindHref;
        bindBtn.classList.remove("hidden");
      } else if (doc.needs_telegram_bind && !doc.telegram_bound) {
        bindBtn.classList.add("hidden");
      } else {
        bindBtn.classList.add("hidden");
      }
    }
    try {
      if (doc.customer_id) localStorage.setItem(CID_KEY, doc.customer_id);
    } catch (e) {
      /* ignore */
    }
  }

  function showCabinetLoading() {
    var balEl = $("cabinet-balance");
    var err = $("cabinet-load-error");
    if (err) err.classList.add("hidden");
    if (balEl) balEl.textContent = "…";
  }

  function loadCabinetBalanceAttempt(retry) {
    if (isTelegramMiniApp()) {
      var uid = getTelegramUserId();
      if (!uid && retry < 8) {
        setTimeout(function () {
          loadCabinetBalanceAttempt(retry + 1);
        }, 120);
        return;
      }
      if (!uid) {
        showCabinetError(
          "Не удалось определить пользователя. Закрой Mini App и открой снова из бота."
        );
        return;
      }
      showCabinetLoading();
      trackFunnel("portal_cabinet_load_tg");
      fetch(API_CABINET, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telegram_id: uid }),
      })
        .then(function (r) {
          return r.json().then(function (j) {
            return { status: r.status, body: j };
          });
        })
        .then(function (res) {
          if (res.body && res.body.ok) {
            applyCabinetData(res.body);
            return;
          }
          applyCabinetData(
            res.body || {
              ok: false,
              message:
                res.status === 502
                  ? "Сервис кабинета временно недоступен. Попробуйте через минуту."
                  : "Аккаунт не найден. Нажмите /start в боте и откройте кабинет снова.",
            }
          );
        })
        .catch(function () {
          applyCabinetData({ ok: false, message: content.errors.generic });
        });
      return;
    }
    var cid = ($("cabinet-customer-id") && $("cabinet-customer-id").value) || "";
    var email = ($("cabinet-email") && $("cabinet-email").value) || "";
    try {
      if (email) localStorage.setItem(EMAIL_KEY, email.trim());
    } catch (e) {
      /* ignore */
    }
    trackFunnel("portal_cabinet_load");
    fetch(API_CABINET, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: cid.trim(),
        email: email.trim(),
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(applyCabinetData)
      .catch(function () {
        applyCabinetData({ ok: false });
      });
  }

  function loadCabinetBalance() {
    loadCabinetBalanceAttempt(0);
  }

  function resolveRouteView() {
    if (window.BVPN_INITIAL_VIEW) {
      return String(window.BVPN_INITIAL_VIEW).trim();
    }
    var path = (window.location.pathname || "").toLowerCase();
    if (path.indexOf("cabinet.html") >= 0) return "cabinet";
    var params = new URLSearchParams(window.location.search || "");
    var view = (params.get("view") || "").trim();
    if (view) return view;
    var raw = (window.location.hash || "").replace(/^#/, "").trim();
    if (raw) return raw;
    var tg = isTelegramMiniApp() ? getTelegramWebApp() : null;
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) {
      return String(tg.initDataUnsafe.start_param).trim();
    }
    return "";
  }

  function openCabinetView() {
    renderCabinet();
    show("home");
    trackFunnel("portal_view_cabinet");
    loadCabinetBalance();
    focusAccountSheet();
  }

  function applyRouteFromHash() {
    var raw = resolveRouteView();
    if (raw === "cabinet") {
      show("home");
      openCabinetView();
      return;
    }
    if (raw === "devices" || raw === "connect") {
      show("devices");
      trackFunnel("portal_view_devices");
      return;
    }
    var dm = raw.match(/^device=(iphone|android|windows|mac)$/);
    if (dm) {
      showDeviceDetail(dm[1]);
      return;
    }
    if (/^(iphone|android|windows|mac)$/.test(raw)) {
      showDeviceDetail(raw);
      return;
    }
    show("home");
  }

  function bindActions() {
    var cabBtn = $("btn-cabinet");
    if (cabBtn) {
      cabBtn.addEventListener("click", function () {
        try {
          history.replaceState(null, "", "?view=cabinet");
        } catch (e) {
          window.location.search = "?view=cabinet";
        }
        openCabinetView();
      });
    }
    var loadBal = $("btn-cabinet-load");
    if (loadBal) {
      loadBal.addEventListener("click", loadCabinetBalance);
    }
    var backCab = $("btn-back-home-cabinet");
    if (backCab) {
      backCab.addEventListener("click", function () {
        window.location.href = "/portal/";
      });
    }
    var btnConnect = $("btn-connect");
    if (btnConnect) {
      btnConnect.addEventListener("click", function () {
        var label = (content.buttons && content.buttons.connect_guide) || "";
        if (!isTelegramMiniApp() && !hasStoredSetup() && btnConnect.textContent === label) {
          window.location.href = "/portal/guide.html";
          return;
        }
        try {
          history.replaceState(null, "", "#devices");
        } catch (e) {
          window.location.hash = "devices";
        }
        show("devices");
        trackFunnel("portal_view_devices");
      });
    }
    var btnSetup = $("btn-setup");
    if (btnSetup) {
      btnSetup.addEventListener("click", function (ev) {
        if (isTelegramMiniApp() || getTelegramUserId() > 0) {
          ev.preventDefault();
          openTelegramSetup(ev);
          return;
        }
        if (hasStoredSetup()) {
          ev.preventDefault();
          try {
            history.replaceState(null, "", "#devices");
          } catch (e2) {
            window.location.hash = "devices";
          }
          show("devices");
          trackFunnel("portal_view_devices");
        }
      });
    }
    var btnSetupSecondary = $("btn-setup-secondary");
    if (btnSetupSecondary) {
      bindExternalLink(btnSetupSecondary);
    }
    var btnBackHome = $("btn-back-home");
    if (btnBackHome) {
      btnBackHome.addEventListener("click", function () {
        show("home");
      });
    }
    var btnBackDevices = $("btn-back-devices");
    if (btnBackDevices) {
      btnBackDevices.addEventListener("click", function () {
        show("devices");
      });
    }
    var btnStuck = $("btn-stuck");
    if (btnStuck) {
      btnStuck.addEventListener("click", function () {
        var helpPanel = $("help-stuck-panel");
        if (helpPanel) {
          helpPanel.open = true;
          helpPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      });
    }
    bindExternalLink($("btn-support"));
    bindExternalLink($("btn-device-support"));

    var btnEventsAck = $("btn-events-ack");
    if (btnEventsAck) btnEventsAck.addEventListener("click", function () {
      fetch(STATUS_JSON)
        .then(function (r) {
          return r.json();
        })
        .then(function (doc) {
          var gen = parseInt((doc.vpn_config || {}).generation, 10) || 0;
          writeAckGeneration(gen > 0 ? gen : 1);
          setEventsState("ok", content.events || {});
          $("events-card").scrollIntoView({ behavior: "smooth", block: "nearest" });
        })
        .catch(function () {
          writeAckGeneration(1);
          setEventsState("ok", content.events || {});
        });
    });
  }

  function showError(msg) {
    $("load-error").textContent = msg || content.errors.generic;
    $("load-error").classList.remove("hidden");
  }

  window.bvpnCopyText = copyToClipboard;

  fetch(CONTENT_URL)
    .then(function (r) {
      if (!r.ok) throw new Error("content load failed");
      return r.json();
    })
    .then(function (data) {
      content = data;
      initTelegram();
      if ($("hero-badge")) renderHome();
      if ($("device-grid")) renderDevices();
      renderCabinet();
      bindActions();
      bindSetupEntryButtons();
      applyRouteFromHash();
      var route = resolveRouteView();
      if (route !== "cabinet" && route !== "devices" && !/^device=/.test(route)) {
        trackFunnel("portal_view_home");
      }
      if (isTelegramMiniApp() || window.BVPN_FOCUS_ACCOUNT) {
        loadCabinetBalance();
      }
      if (window.BVPN_FOCUS_ACCOUNT) {
        show("home");
        focusAccountSheet();
      }
      var footMount = $("site-footer-mount");
      if (footMount && window.BenderPortalShared) {
        BenderPortalShared.renderSiteFooter(footMount, content);
        BenderPortalShared.bindStatusLinks(document);
      }
    })
    .catch(function () {
      showError(
        "Не удалось загрузить тексты. Откройте страницу через веб-сервер или с продакшн-домена."
      );
    });
})();
