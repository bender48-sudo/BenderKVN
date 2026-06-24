(function () {
  "use strict";

  const CONTENT_URL = "/portal/content/ru.json";
  const STATUS_JSON = "/api/ops/status.json";
  function statusPageUrl() {
    if (window.BenderPortalShared) return BenderPortalShared.statusPageUrl();
    return "/status";
  }
  const SUPPORT_URL = "https://t.me/Bender_KVN_bot";
  const BOT_SHOW_ID_URL = SUPPORT_URL + "?start=show_id";
  const SETUP_PATH = "/setup/";
  const API_FUNNEL = "/setup/api/funnel-event";
  const API_CABINET = "/setup/api/cabinet";
  const API_CAPACITY = "/setup/api/capacity";
  const API_TELEGRAM_SETUP = "/setup/api/telegram-setup";
  const REF_KEY = "bvpn_ref_code";
  const REF_FORMAT_RE = /^[A-Za-z0-9_-]{4,64}$/;
  const DAILY_RATE_RUB = 6.66;
  const ACK_KEY = "bvpn_vpn_config_ack";
  const SUB_URL_KEY = "bvpn_subscription_url";
  const CID_KEY = "bvpn_customer_id";
  const EMAIL_KEY = "bvpn_customer_email";

  let content = null;

  function $(id) {
    return document.getElementById(id);
  }

  function referralUiEnabled() {
    return !!(content && content.meta && content.meta.referral_ui_enabled);
  }

  // K7: нарратив дефицита (набор ограничен / закрытие доступа / «растём по приглашениям»)
  // показываем только в target-режиме — за тем же флагом, что счётчик 300-cap.
  // Интерим: вход открыт, ничего про закрытость не обещаем.
  function scarcityNarrativeEnabled() {
    return !!(content && content.meta && content.meta.capacity_api_enabled);
  }

  function resolveCabinetStateKey(doc) {
    if (!doc || !doc.ok) return "no_subscription";
    var configs = doc.configurations || [];
    var activeCount =
      typeof doc.active_config_count === "number"
        ? doc.active_config_count
        : configs.filter(function (c) {
            return c.active || c.status === "active";
          }).length;
    if (
      doc.billing_profile === "expired" ||
      (doc.days_left <= 0 && doc.balance_rub <= 0 && doc.billing_profile !== "legacy" && doc.billing_profile !== "trial")
    ) {
      return "expired";
    }
    if (doc.billing_profile === "wallet" && typeof doc.days_left === "number" && doc.days_left <= 3) {
      return "expiring_soon";
    }
    if (doc.billing_profile === "trial") {
      return activeCount >= 1 ? "trial_connected" : "trial_no_device";
    }
    if (doc.billing_profile === "wallet") {
      return activeCount >= 1 ? "paid_active" : "trial_no_device";
    }
    return "no_subscription";
  }

  // §4: посостоянийная копь карточки «Мой доступ». Legacy (ручной доступ) — своя ветка.
  function homeStateCopy(doc) {
    var cab = (content && content.cabinet) || {};
    var states = cab.states || {};
    if (!doc || !doc.ok) return states.no_subscription || null;
    if (doc.billing_profile === "legacy") return null;
    return states[resolveCabinetStateKey(doc)] || null;
  }

  function formatDateInDays(days) {
    var d = new Date();
    d.setDate(d.getDate() + (parseInt(days, 10) || 0));
    var dd = ("0" + d.getDate()).slice(-2);
    var mm = ("0" + (d.getMonth() + 1)).slice(-2);
    return dd + "." + mm + "." + d.getFullYear();
  }

  // K1/D3: длительность триала — из entitlement API, не хардкод вёрстки. Интерим-дефолт 90.
  function trialDays(doc) {
    var v = doc && (doc.trial_entitlement_days != null ? doc.trial_entitlement_days : doc.trial_days);
    var n = parseInt(v, 10);
    return n > 0 ? n : 90;
  }

  // {name} → ", Имя"/"" · {days} → дни остатка · {date} → today+days (D12) · {trial_days} → entitlement
  function fillStateText(str, doc) {
    if (!str) return "";
    var name = getTelegramUserFirstName();
    var raw = doc && (doc.trial_days_left != null ? doc.trial_days_left : doc.days_left);
    var days = typeof raw === "number" && raw >= 0 ? raw : parseInt(raw, 10) || 0;
    return str
      .replace("{name}", name ? ", " + name : "")
      .replace(/\{trial_days\}/g, String(trialDays(doc)))
      .replace(/\{days\}/g, String(days))
      .replace(/\{date\}/g, formatDateInDays(days));
  }

  function cabinetPrimaryCtaLabel(doc) {
    var cab = (content && content.cabinet) || {};
    var map = cab.cta_by_state || {};
    var key = resolveCabinetStateKey(doc);
    return fillStateText(map[key] || cab.action_setup || "Получить настройку", doc);
  }

  function cabinetTabsEnabled() {
    return !!$("cabinet-bottom-nav");
  }

  function cabinetPrimaryCtaHref(doc) {
    var key = resolveCabinetStateKey(doc);
    // D6: пополнение — на вкладку Баланс (там сумма + «Пополнить в боте»), не молча в TG.
    if (key === "expiring_soon" || key === "expired") {
      return "#tab=balance";
    }
    if (key === "slot_full") {
      return botUrlWithReferral();
    }
    if (key === "trial_connected" || key === "paid_active") {
      if (isCabinetDedicatedPage() || isTelegramMiniApp()) return "#devices";
      return SETUP_PATH + "#devices";
    }
    if (key === "trial_no_device" || key === "no_subscription") {
      if (isCabinetDedicatedPage() || isTelegramMiniApp()) return "#devices";
      return SETUP_PATH;
    }
    if (isCabinetDedicatedPage() || isTelegramMiniApp()) return "#devices";
    return SETUP_PATH;
  }

  function wizardCopy() {
    return (content && content.wizard) || {};
  }

  function goWizardStep(n) {
    if (n <= 1) {
      openConnectWizard();
      return;
    }
    var dev = window.BVPN_WIZARD_DEVICE;
    if (dev) {
      showDeviceDetail(dev);
    } else {
      openConnectWizard();
    }
  }

  function renderWizardProgress(activeStep) {
    var wz = wizardCopy();
    var labels = wz.steps || [];
    [ $("wizard-progress"), $("wizard-progress-detail") ].forEach(function (mount) {
      if (!mount) return;
      mount.innerHTML = "";
      mount.setAttribute("aria-label", wz.progress_aria || "Шаги подключения VPN");
      labels.forEach(function (label, idx) {
        var stepNum = idx + 1;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "wizard-progress__item";
        if (stepNum === activeStep) btn.classList.add("wizard-progress__item--active");
        if (stepNum < activeStep) btn.classList.add("wizard-progress__item--done");
        btn.textContent = label;
        btn.addEventListener("click", function () {
          goWizardStep(stepNum);
        });
        mount.appendChild(btn);
      });
      // активный таб виден при горизонтальном скролле
      var act = mount.querySelector(".wizard-progress__item--active");
      if (act && act.scrollIntoView) {
        try {
          act.scrollIntoView({ inline: "center", block: "nearest" });
        } catch (e) {}
      }
    });
  }

  function openConnectWizard() {
    renderDevices();
    renderWizardProgress(1);
    show("devices");
    trackFunnel("portal_view_devices");
  }

  function showWizardVerifyPanel(mode, message) {
    var wz = wizardCopy();
    var panel = $("wizard-step-verify");
    var trouble = $("wizard-step-trouble");
    var title = $("wizard-verify-title");
    var body = $("wizard-verify-body");
    var retry = $("btn-wizard-verify-retry");
    var skip = $("btn-wizard-verify-skip");
    if (trouble) trouble.classList.add("hidden");
    if (panel) panel.classList.remove("hidden");
    renderWizardProgress(mode === "ok" ? 5 : 5);
    if (title) title.textContent = wz.verify_title || "Проверка подключения";
    if (body) body.textContent = message || wz.verify_pending || "";
    if (retry) {
      retry.textContent = wz.verify_retry || "Проверить снова";
      retry.classList.toggle("hidden", mode === "ok");
    }
    if (skip) {
      skip.textContent = wz.verify_skip || "Пропустить проверку";
      skip.classList.toggle("hidden", mode === "ok");
    }
    if (mode === "fail") {
      if (trouble) trouble.classList.remove("hidden");
      renderWizardProgress(6);
    }
  }

  function showWizardTrouble() {
    var wz = wizardCopy();
    var panel = $("wizard-step-trouble");
    if ($("wizard-trouble-title")) {
      $("wizard-trouble-title").textContent = wz.trouble_title || "Не получилось подключить?";
    }
    if ($("wizard-trouble-lead")) {
      $("wizard-trouble-lead").textContent = wz.trouble_lead || "";
    }
    var list = $("wizard-trouble-steps");
    if (list) {
      list.innerHTML = "";
      (wz.trouble_steps || []).forEach(function (step) {
        var li = document.createElement("li");
        li.textContent = step;
        list.appendChild(li);
      });
    }
    var sup = $("btn-wizard-trouble-support");
    if (sup) {
      sup.textContent = wz.trouble_support || "Написать в поддержку";
      sup.href = SUPPORT_URL;
      bindExternalLink(sup);
    }
    var err = $("btn-wizard-trouble-errors");
    if (err) {
      err.textContent = wz.trouble_errors_link || "Частые ошибки";
    }
    if (panel) panel.classList.remove("hidden");
    renderWizardProgress(6);
  }

  function renderWizardConfigActions(subUrl) {
    var wz = wizardCopy();
    if ($("wizard-step-config-title")) {
      $("wizard-step-config-title").textContent = wz.step_config_title || "Импортируй настройку";
    }
    if ($("wizard-step-config-lead")) {
      $("wizard-step-config-lead").textContent = wz.step_config_lead || "";
    }
    if ($("wizard-connected-lead")) {
      $("wizard-connected-lead").textContent = wz.connected_lead || "";
    }
    var copyBtn = $("btn-wizard-copy");
    if (copyBtn) {
      copyBtn.textContent = wz.copy_link || "Скопировать ссылку";
      copyBtn.disabled = !subUrl;
    }
    var happBtn = $("btn-wizard-happ");
    if (happBtn) {
      happBtn.textContent = wz.open_happ || "Открыть в Happ";
      happBtn.href = subUrl || "#";
      if (subUrl) bindExternalLink(happBtn);
    }
    var connectedBtn = $("btn-wizard-connected");
    if (connectedBtn) {
      connectedBtn.textContent = wz.connected_cta || "Я подключился";
    }
  }

  function verifyWizardConnection() {
    var wz = wizardCopy();
    showWizardVerifyPanel("pending", wz.verify_pending || "Проверяем…");
    var payload = {};
    var tgId = getTelegramUserId();
    if (tgId > 0) payload.telegram_user_id = tgId;
    try {
      var cid = localStorage.getItem(CID_KEY) || "";
      var em = localStorage.getItem(EMAIL_KEY) || "";
      if (cid) payload.customer_id = cid;
      if (em) payload.email = em;
    } catch (e) {
      /* ignore */
    }
    if (!payload.telegram_user_id && !payload.customer_id && !payload.email) {
      showWizardVerifyPanel("fail", wz.verify_api_fail || wz.no_sub_hint || "");
      showWizardTrouble();
      return;
    }
    fetch(API_CABINET, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (doc) {
        window.BVPN_CABINET_DOC = doc;
        var active =
          doc && doc.ok &&
          ((typeof doc.active_config_count === "number" && doc.active_config_count >= 1) ||
            (doc.configurations || []).some(function (c) {
              return c.active || c.status === "active";
            }));
        if (active) {
          showWizardVerifyPanel("ok", wz.verify_ok || "Настройка активна.");
          if ($("wizard-verify-body") && wz.verify_ok_hint) {
            $("wizard-verify-body").textContent =
              (wz.verify_ok || "") + " " + wz.verify_ok_hint;
          }
          trackFunnel("portal_wizard_verify_ok");
        } else {
          showWizardVerifyPanel("fail", wz.verify_pending || "");
          showWizardTrouble();
          trackFunnel("portal_wizard_verify_pending");
        }
      })
      .catch(function () {
        showWizardVerifyPanel("fail", wz.verify_api_fail || "");
        showWizardTrouble();
      });
  }

  function bindWizardActions() {
    var copyBtn = $("btn-wizard-copy");
    if (copyBtn && copyBtn.dataset.bvpnWizardBound !== "1") {
      copyBtn.dataset.bvpnWizardBound = "1";
      copyBtn.addEventListener("click", function () {
        var url = readStoredSubscriptionUrl();
        if (!url) {
          showToast(wizardCopy().no_sub_hint || "Сначала получи настройку в боте.", "error");
          return;
        }
        copyTextWithInlineFallback(url, {
          onSuccess: function () {
            showToast(wizardCopy().copy_ok || "Ссылка скопирована");
            trackFunnel("portal_wizard_copy_link");
          },
        });
      });
    }
    var connectedBtn = $("btn-wizard-connected");
    if (connectedBtn && connectedBtn.dataset.bvpnWizardBound !== "1") {
      connectedBtn.dataset.bvpnWizardBound = "1";
      connectedBtn.addEventListener("click", function () {
        trackFunnel("portal_wizard_connected");
        verifyWizardConnection();
      });
    }
    var retryBtn = $("btn-wizard-verify-retry");
    if (retryBtn && retryBtn.dataset.bvpnWizardBound !== "1") {
      retryBtn.dataset.bvpnWizardBound = "1";
      retryBtn.addEventListener("click", verifyWizardConnection);
    }
    var skipBtn = $("btn-wizard-verify-skip");
    if (skipBtn && skipBtn.dataset.bvpnWizardBound !== "1") {
      skipBtn.dataset.bvpnWizardBound = "1";
      skipBtn.addEventListener("click", function () {
        if (cabinetTabsEnabled()) {
          show("home");
          setCabinetTab("access");
        } else {
          show("home");
        }
      });
    }
  }

  function renderWizardStaticCopy() {
    var wz = wizardCopy();
    if ($("wizard-step-app-title")) {
      $("wizard-step-app-title").textContent = wz.step_app_title || "Установи Happ";
    }
    if ($("wizard-step-app-lead")) {
      $("wizard-step-app-lead").textContent = wz.step_app_lead || "";
    }
    if ($("wizard-verify-title")) {
      $("wizard-verify-title").textContent = wz.verify_title || "Проверка подключения";
    }
  }


  function setCabinetTab(tab) {
    if (!cabinetTabsEnabled()) return;
    tab = tab || "home";
    document.querySelectorAll("[data-cabinet-tab]").forEach(function (el) {
      el.classList.toggle("hidden", el.getAttribute("data-cabinet-tab") !== tab);
    });
    document.querySelectorAll("[data-cabinet-tab-btn]").forEach(function (btn) {
      var active = btn.getAttribute("data-cabinet-tab-btn") === tab;
      btn.classList.toggle("cabinet-bottom-nav__item--active", active);
      btn.setAttribute("aria-current", active ? "page" : "false");
    });
    try {
      history.replaceState(null, "", "#tab=" + tab);
    } catch (e) {
      window.location.hash = "tab=" + tab;
    }
    trackFunnel("portal_cabinet_tab_" + tab);
  }

  function applyCabinetTabFromHash() {
    if (!cabinetTabsEnabled()) return;
    var raw = (window.location.hash || "").replace(/^#/, "");
    var m = raw.match(/^tab=(home|access|balance|support)$/);
    if (m) {
      setCabinetTab(m[1]);
      return;
    }
    // Non-tab deep-links (devices/connect/device) are owned by applyRouteFromHash —
    // don't clobber the hash back to #tab=home here.
    if (/^(devices|connect|device)/.test(raw)) return;
    setCabinetTab("home");
  }

  function renderCabinetBottomNav() {
    if (!cabinetTabsEnabled()) return;
    var nav = (content.cabinet && content.cabinet.nav) || {};
    var ids = {
      home: "cab-nav-home",
      access: "cab-nav-access",
      balance: "cab-nav-balance",
      support: "cab-nav-support",
    };
    Object.keys(ids).forEach(function (key) {
      var btn = $(ids[key]);
      if (!btn) return;
      var labelEl = btn.querySelector(".cabinet-bottom-nav__label");
      var text = nav[key] || key;
      if (labelEl) labelEl.textContent = text;
      else btn.textContent = text;
    });
  }

  function bindCabinetQuickTiles() {
    document.querySelectorAll("[data-cabinet-tab-jump]").forEach(function (btn) {
      if (btn.dataset.bvpnQuickBound === "1") return;
      btn.dataset.bvpnQuickBound = "1";
      btn.addEventListener("click", function () {
        setCabinetTab(btn.getAttribute("data-cabinet-tab-jump"));
      });
    });
  }

  function updateCabinetWelcome(doc) {
    var cab = (content && content.cabinet) || {};
    var welcome = $("cabinet-welcome");
    var sub = $("cabinet-welcome-sub");
    if (!welcome) return;
    var st = homeStateCopy(doc);
    var name = getTelegramUserFirstName();
    if (st && st.greet) {
      welcome.textContent = fillStateText(st.greet, doc);
    } else {
      var tpl = cab.home_welcome || "Добро пожаловать{name}!";
      welcome.textContent = tpl.replace("{name}", name ? ", " + name : "");
    }
    if (sub) {
      if (st && st.lead) {
        sub.textContent = fillStateText(st.lead, doc);
      } else {
        sub.textContent =
          (doc && doc.ok && doc.billing_profile === "trial"
            ? cab.home_welcome_trial
            : cab.home_welcome_sub) ||
          cab.lead_subline_tg ||
          "Баланс, устройства и настройка — в одном кабинете.";
      }
    }
  }

  function updateCabinetMetrics(doc) {
    var cab = (content && content.cabinet) || {};
    var ma = $("cabinet-metric-a");
    var mb = $("cabinet-metric-b");
    var mc = $("cabinet-metric-c");
    var la = $("cabinet-metric-a-label");
    var lb = $("cabinet-metric-b-label");
    var lc = $("cabinet-metric-c-label");
    var lead = $("cabinet-access-card-lead");
    if (la) la.textContent = cab.metric_days_label || "дней";
    if (lb) lb.textContent = cab.metric_device_label || "устройство";
    if (lc) lc.textContent = cab.metric_trial_extra_label || "без лимита";
    if ($("cabinet-access-card-title")) {
      $("cabinet-access-card-title").textContent = cab.access_card_title || "Мой доступ";
    }
    if (!doc || !doc.ok) {
      if (ma) ma.textContent = "90";
      if (mb) mb.textContent = "1";
      if (mc) mc.textContent = "∞";
      if (lead) lead.textContent = cab.access_card_lead_trial || cab.home_hint || "";
      return;
    }
    var activeCfg =
      typeof doc.active_config_count === "number"
        ? doc.active_config_count
        : (doc.configurations || []).filter(function (c) {
            return c.active || c.status === "active";
          }).length;
    var slotLimit = doc.device_slot_limit || doc.slot_limit || 1;
    if (resolveCabinetStateKey(doc) === "no_subscription") {
      // §4 A — новичок: тройка {trial_days} · 1 · ∞ (без баланса/списания). Дни — из entitlement.
      if (ma) ma.textContent = String(trialDays(doc));
      if (mb) mb.textContent = "1";
      if (mc) mc.textContent = "∞";
    } else if (doc.billing_profile === "trial") {
      if (ma) ma.textContent = String(doc.trial_days_left || doc.days_left || "90");
      if (mb) mb.textContent = activeCfg + "/" + slotLimit;
      if (mc) mc.textContent = "∞";
      if (lead) lead.textContent = cab.access_card_lead_trial || cab.balance_hint_trial || "";
    } else {
      if (ma) ma.textContent = String(doc.days_left || "0");
      if (mb) mb.textContent = activeCfg + "/" + slotLimit;
      if (mc) mc.textContent = "6,66₽";
      if (la) la.textContent = cab.metric_balance_days_label || "дней по балансу";
      if (lc) lc.textContent = cab.metric_rate_label || "в день";
      if (lead) lead.textContent = cab.access_card_lead_paid || cab.balance_hint || "";
    }
    var stLead = homeStateCopy(doc);
    if (lead && stLead && stLead.text) {
      lead.textContent = fillStateText(stLead.text, doc);
    }
    var qb = $("cabinet-quick-balance-value");
    if (qb) qb.textContent = Math.round(doc.balance_rub || 0) + " ₽";
    var qa = $("cabinet-quick-access-value");
    if (qa) qa.textContent = activeCfg + "/" + slotLimit;
  }

  function bindCabinetTabNav() {
    if (!cabinetTabsEnabled()) return;
    document.querySelectorAll("[data-cabinet-tab-btn]").forEach(function (btn) {
      if (btn.dataset.bvpnTabBound === "1") return;
      btn.dataset.bvpnTabBound = "1";
      btn.addEventListener("click", function () {
        setCabinetTab(btn.getAttribute("data-cabinet-tab-btn"));
      });
    });
    bindCabinetQuickTiles();
  }

  function updateCabinetPrimaryCta(doc) {
    var primary = $("btn-cabinet-primary");
    if (!primary) return;
    var cab = (content && content.cabinet) || {};
    var label = cabinetPrimaryCtaLabel(doc || {});
    var href = cabinetPrimaryCtaHref(doc || {});
    primary.textContent = label;
    primary.href = href;
    if (/^https?:\/\//i.test(href)) {
      bindExternalLink(primary);
      primary.onclick = null;
    } else if (href.indexOf("#devices") >= 0) {
      delete primary.dataset.bvpnBound;
      primary.onclick = function (ev) {
        ev.preventDefault();
        openConnectWizard();
      };
    } else if (href.indexOf("#tab=balance") >= 0) {
      delete primary.dataset.bvpnBound;
      primary.onclick = function (ev) {
        ev.preventDefault();
        setCabinetTab("balance");
      };
    } else {
      delete primary.dataset.bvpnBound;
      primary.onclick = null;
    }
    var hint = $("cabinet-home-hint");
    if (hint) {
      if (doc && doc.ok && doc.billing_profile === "trial" && cab.balance_hint_trial) {
        hint.textContent = cab.balance_hint_trial;
      } else {
        hint.textContent = cab.home_hint || cab.lead_subline_tg || "";
      }
    }
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

  function getTelegramUserFirstName() {
    var tg = getTelegramWebApp();
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
      var name = (tg.initDataUnsafe.user.first_name || "").trim();
      if (name) return name;
    }
    return "";
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

  function isLocalQaPreview() {
    var h = (window.location.hostname || "").toLowerCase();
    return h === "127.0.0.1" || h === "localhost";
  }

  function isCabinetDedicatedPage() {
    if (window.BVPN_FOCUS_ACCOUNT) return true;
    return (window.location.pathname || "").toLowerCase().indexOf("cabinet.html") >= 0;
  }

  function hasStoredCabinetIdentity() {
    if (getTelegramUserId() > 0) return true;
    try {
      if ((localStorage.getItem(CID_KEY) || "").trim()) return true;
      if ((localStorage.getItem(EMAIL_KEY) || "").trim()) return true;
    } catch (e) {
      /* ignore */
    }
    return false;
  }

  function shouldShowCabinetAccountPanel() {
    if (isTelegramMiniApp()) return true;
    if (!isCabinetDedicatedPage()) return hasStoredCabinetIdentity();
    return !!window.BVPN_CABINET_ACCOUNT_VISIBLE;
  }

  function shouldAutoLoadCabinet() {
    if (isTelegramMiniApp()) return true;
    if (isCabinetDedicatedPage()) {
      if (isLocalQaPreview() && getTelegramUserId() > 0) return true;
      return false;
    }
    return hasStoredCabinetIdentity();
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

  function copyTextWithInlineFallback(text, opts) {
    opts = opts || {};
    var done = opts.onSuccess;
    var fail = opts.onFail;
    var value = String(text || "");
    if (!value) return;
    copyToClipboard(value)
      .then(function () {
        if (done) done();
      })
      .catch(function () {
        if (fail) fail(value);
      });
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
    /* Portal uses fixed dark-glass surfaces; syncing Telegram text_color/hint_color
       (e.g. black from a light TG theme) makes cabinet copy unreadable on dark cards. */
    var tgChromeBg = tp.bg_color || "#050508";
    if (typeof tg.setHeaderColor === "function") {
      try {
        tg.setHeaderColor(tgChromeBg);
      } catch (e) {
        /* ignore */
      }
    }
    if (typeof tg.setBackgroundColor === "function") {
      try {
        tg.setBackgroundColor(tgChromeBg);
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

  function setEventsCardVisible(visible) {
    var card = $("events-card");
    if (card) {
      if (visible) card.classList.remove("hidden");
      else card.classList.add("hidden");
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
    setEventsCardVisible(mode !== "ok");

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
    setEventsCardVisible(false);
    var ev = content.events || {};
    if ($("events-title")) {
      $("events-title").textContent = ev.title || "Обновления VPN";
    }
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
      var homeCtaTg = $("home-cta");
      if (homeCtaTg) homeCtaTg.classList.remove("hidden");
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
      primary.textContent = btns.landing_primary_tg || btns.landing_tg || btns.setup_browser_alt || "Telegram";
      primary.href = botUrlWithReferral();
      bindExternalLink(primary);
      primary.classList.remove("hidden");
      if (secondary) secondary.classList.add("hidden");
      if (connect) connect.classList.add("hidden");
      var homeCtaBrowser = $("home-cta");
      if (homeCtaBrowser) homeCtaBrowser.classList.add("hidden");
    }
    if (topup) topup.classList.add("hidden");
    if (sepTopup) sepTopup.classList.add("hidden");
  }

  function refFromUrl() {
    try {
      var params = new URLSearchParams(window.location.search || "");
      var ref = (params.get("ref") || "").trim();
      if (!ref && window.location.hash.indexOf("ref_") >= 0) {
        ref = window.location.hash.replace(/^#/, "").replace(/^ref_/, "");
      }
      return ref;
    } catch (e) {
      return "";
    }
  }

  function isRefFormatValid(ref) {
    return !!ref && REF_FORMAT_RE.test(ref);
  }

  function renderInvalidRef() {
    var panel = $("invalid-ref-panel");
    var paths = $("landing-paths");
    var refWelcome = $("referral-welcome");
    var inv = (content && content.invalid_ref) || {};
    var rawRef = refFromUrl();
    if (!panel || !rawRef || isRefFormatValid(rawRef)) {
      if (panel) panel.classList.add("hidden");
      return false;
    }
    if ($("invalid-ref-title") && inv.title) {
      $("invalid-ref-title").textContent = inv.title;
    }
    if ($("invalid-ref-lead") && inv.lead) {
      $("invalid-ref-lead").textContent = inv.lead;
    }
    var sup = $("btn-invalid-ref-support");
    if (sup) {
      sup.textContent = inv.cta_support || "Написать в поддержку";
      sup.href = SUPPORT_URL;
      bindExternalLink(sup);
    }
    var home = $("btn-invalid-ref-home");
    if (home && inv.cta_home) home.textContent = inv.cta_home;
    panel.classList.remove("hidden");
    if (paths) paths.classList.add("hidden");
    if (refWelcome) refWelcome.classList.add("hidden");
    return true;
  }

  function renderTopupPresets() {
    var mount = $("cabinet-topup-chips");
    var cab = (content && content.cabinet) || {};
    var presets = cab.topup_presets || [];
    if (!mount || !presets.length) return;
    mount.innerHTML = "";
    presets.forEach(function (preset) {
      var days = parseInt(preset.days, 10) || 0;
      var amount = Math.round(days * DAILY_RATE_RUB);
      var chip = document.createElement("a");
      chip.className = "cabinet-chip";
      chip.href = botUrlWithReferral();
      chip.setAttribute("data-topup", String(amount));
      chip.textContent =
        (preset.label || days + " дн.") + " (≈ " + amount + " ₽)";
      mount.appendChild(chip);
    });
    mount.querySelectorAll(".cabinet-chip").forEach(function (chip) {
      bindExternalLink(chip);
    });
  }

  function preserveReferralFromUrl() {
    try {
      var ref = refFromUrl();
      if (ref && isRefFormatValid(ref)) {
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

  function hideCapacityCard() {
    var card = $("slots-card");
    if (card) card.classList.add("hidden");
  }

  function applyCapacityDoc(doc) {
    var card = $("slots-card");
    var home = content.home || {};
    if (!card || !doc || !doc.ok) return false;
    var val = $("slots-value");
    var hint = $("slots-hint");
    var cap = doc.access_cap || 30000;
    if (!doc.registration_open) {
      if (val) val.textContent = "0";
      if (hint) hint.textContent = home.slots_closed || "";
    } else {
      var fmt = home.slots_format || "{remaining} мест";
      if (val) {
        val.textContent = fmt.replace("{remaining}", String(doc.remaining_slots));
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
    return true;
  }

  function loadCapacity() {
    var card = $("slots-card");
    var home = content.home || {};
    var meta = content.meta || {};
    if (!card) return;
    if (isTelegramMiniApp()) {
      hideCapacityCard();
      return;
    }
    if ($("slots-title") && home.slots_title) {
      $("slots-title").textContent = home.slots_title;
    }
    if (isLocalQaPreview()) {
      var fx = new URLSearchParams(window.location.search || "").get(
        "qa_capacity_fixture"
      );
      if (fx) {
        var fixtures = {
          slots_high: {
            ok: true,
            registration_open: true,
            remaining_slots: 25000,
            active_configurations: 5000,
            access_cap: 30000,
          },
          slots_low: {
            ok: true,
            registration_open: true,
            remaining_slots: 120,
            active_configurations: 29880,
            access_cap: 30000,
          },
          slots_zero: {
            ok: true,
            registration_open: false,
            remaining_slots: 0,
            active_configurations: 30000,
            access_cap: 30000,
          },
        };
        if (applyCapacityDoc(fixtures[fx])) return;
      }
    }
    // No live capacity API — hide counter card; hero_badge shows invite-only limit.
    if (meta.capacity_api_enabled !== true) {
      hideCapacityCard();
      return;
    }
    fetch(API_CAPACITY, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(function (r) {
        return r.json();
      })
      .then(function (doc) {
        if (!applyCapacityDoc(doc)) throw new Error("capacity");
      })
      .catch(function () {
        hideCapacityCard();
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

  function renderHeroStats(home, tg) {
    var card = $("hero-stats");
    var row = $("hero-stats-row");
    if (!card || !row) return;
    var stats = home.hero_stats || [];
    if (tg || !stats.length) {
      card.classList.add("hidden");
      return;
    }
    if ($("hero-stats-title")) $("hero-stats-title").textContent = home.hero_stats_title || "";
    row.innerHTML = "";
    stats.forEach(function (s) {
      var item = document.createElement("div");
      item.className = "hero-stats__item";
      var v = document.createElement("span");
      v.className = "hero-stats__value";
      v.textContent = s.value;
      var u = document.createElement("span");
      u.className = "hero-stats__unit";
      u.textContent = s.unit;
      item.appendChild(v);
      item.appendChild(u);
      row.appendChild(item);
    });
    card.classList.remove("hidden");
  }

  function renderBenefits(home, tg) {
    var wrap = $("landing-benefits");
    var grid = $("benefit-tiles");
    if (!wrap || !grid) return;
    var items = home.benefits || [];
    if (tg || !items.length) {
      wrap.classList.add("hidden");
      return;
    }
    if ($("benefits-title")) $("benefits-title").textContent = home.benefits_title || "";
    grid.innerHTML = "";
    items.forEach(function (b) {
      var tile = document.createElement("div");
      tile.className = "benefit-tile glass";
      var ic = document.createElement("span");
      ic.className = "benefit-tile__icon";
      ic.textContent = b.icon || "•";
      var t = document.createElement("p");
      t.className = "benefit-tile__title";
      t.textContent = b.title || "";
      var d = document.createElement("p");
      d.className = "benefit-tile__text muted";
      d.textContent = b.text || "";
      tile.appendChild(ic);
      tile.appendChild(t);
      tile.appendChild(d);
      grid.appendChild(tile);
    });
    wrap.classList.remove("hidden");
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
    if ($("landing-tg-after") && home.landing_tg_after) {
      $("landing-tg-after").textContent = home.landing_tg_after;
    }
    if ($("landing-email-after") && home.landing_email_after) {
      $("landing-email-after").textContent = home.landing_email_after;
    }
    if ($("landing-limit-note") && home.landing_limit_note) {
      $("landing-limit-note").textContent = home.landing_limit_note;
    }
    var tgBtn = $("btn-landing-tg");
    if (tgBtn) {
      tgBtn.textContent =
        btns.landing_primary_tg || btns.landing_tg || btns.setup_browser_alt || "Начать — 90 дней в Telegram";
      tgBtn.href = botUrlWithReferral();
      bindExternalLink(tgBtn);
    }
    var emBtn = $("btn-landing-email");
    if (emBtn) {
      emBtn.textContent = btns.landing_email || btns.setup_browser || "Временный доступ на 1 сутки";
      emBtn.href = SETUP_PATH;
    }
    var refNote = $("referral-note");
    if (refNote) {
      try {
        if (localStorage.getItem(REF_KEY) && home.referral_preserve_note) {
          refNote.textContent = home.referral_preserve_note;
          refNote.classList.remove("hidden");
        } else {
          refNote.classList.add("hidden");
        }
      } catch (e) {
        refNote.classList.add("hidden");
      }
    }
    panel.classList.remove("hidden");
    var homeCta = $("home-cta");
    if (homeCta) {
      if (isTelegramMiniApp()) homeCta.classList.remove("hidden");
      else homeCta.classList.add("hidden");
    }
    var blocked = $("tg-blocked-banner");
    if (blocked) blocked.classList.add("hidden");
  }

  function renderExistingUserEntry() {
    var panel = $("landing-existing-user");
    var home = content.home || {};
    var btns = content.buttons || {};
    if (!panel || isTelegramMiniApp()) {
      if (panel) panel.classList.add("hidden");
      return;
    }
    if (hasStoredCabinetIdentity()) {
      panel.classList.add("hidden");
      return;
    }
    if ($("landing-existing-title") && home.landing_existing_title) {
      $("landing-existing-title").textContent = home.landing_existing_title;
    }
    if ($("landing-existing-lead") && home.landing_existing_lead) {
      $("landing-existing-lead").textContent = home.landing_existing_lead;
    }
    var openBtn = $("btn-open-account-fold");
    if (openBtn) {
      openBtn.textContent = home.landing_existing_cta || btns.cabinet || "Открыть личный кабинет";
      openBtn.onclick = function () {
        var fold = $("account-fold");
        if (fold) {
          fold.open = true;
          fold.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      };
    }
    panel.classList.remove("hidden");
  }

  function configureBrowserAccountFold() {
    if (isTelegramMiniApp() || isCabinetDedicatedPage()) return;
    var home = content.home || {};
    var fold = $("account-fold");
    var lead = $("cabinet-lead-inline");
    var actions = document.querySelector("#account-fold .sheet__actions");
    var bindBtn = $("btn-cabinet-bind");
    var botBtn = $("btn-cabinet-bot");
    var foldTitle = $("account-fold-title");
    if (foldTitle && home.landing_existing_title) {
      foldTitle.textContent = home.landing_existing_title + " · " + (home.account_fold_title || "Личный кабинет");
    }
    if (!hasStoredCabinetIdentity()) {
      if (lead && home.account_fold_lead_browser) {
        lead.textContent = home.account_fold_lead_browser;
      }
      if (actions) actions.classList.add("hidden");
      if (bindBtn) bindBtn.classList.add("hidden");
      if (botBtn) botBtn.classList.add("hidden");
      if (fold) fold.open = false;
      return;
    }
    if (actions) actions.classList.remove("hidden");
    if (fold) fold.open = true;
  }

  function renderPhilosophy() {
    var fold = $("fold-about");
    if (fold && $("why-limited") && !$("why-limited").classList.contains("hidden")) {
      fold.classList.add("hidden");
      return;
    }
    var pos = content.positioning;
    var body = $("fold-about-body");
    var title = $("fold-about-title");
    if (!pos || !body) return;
    if (title) title.textContent = content.home.about_fold_title || "О сервисе";
    // K7: invite/limit — нарратив дефицита, только в target-режиме. Интерим — нейтральный support-блок.
    var blocks = scarcityNarrativeEnabled()
      ? [
          ["invite_title", "invite_body"],
          ["limit_title", "limit_body"],
          ["support_title", "support_body"],
        ]
      : [["support_title", "support_body"]];
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
    renderHeroStats(home, tg);
    renderBenefits(home, tg);
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
      if (!tg || hasStoredSetup()) {
        blockedBanner.classList.add("hidden");
      }
    }
    if ($("happ-note") && content.happ) {
      $("happ-note").textContent = content.happ.phone_and_pc;
    }
    preserveReferralFromUrl();
    loadCapacity();
    if (!renderInvalidRef()) {
      renderLandingPaths();
      renderReferralWelcome();
    }
    renderJourney();
    renderWhyLimited();
    renderExistingUserEntry();
    configureBrowserAccountFold();
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
    window.BVPN_WIZARD_DEVICE = deviceId;
    var subUrl = readStoredSubscriptionUrl();
    renderDeviceSubscriptionQr(subUrl);
    renderWizardConfigActions(subUrl);
    renderWizardStaticCopy();
    renderWizardProgress(2);
    var wz = wizardCopy();
    $("device-detail-title").textContent = dev.install_title;
    var list = $("device-install-steps");
    list.innerHTML = "";
    var storeKey = dev.install_store_key || dev.id;
    var stores = content.happ_install || {};
    var store = stores[storeKey] || stores.generic;
    var storeLink = $("wizard-store-link");
    if (storeLink) {
      if (store && store.url) {
        storeLink.textContent = "↓ " + (store.label || "Скачать Happ");
        storeLink.href = store.url;
        storeLink.classList.remove("hidden");
      } else {
        storeLink.classList.add("hidden");
      }
    }
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
    steps.forEach(function (step) {
      var li = document.createElement("li");
      li.textContent = step;
      list.appendChild(li);
    });
    if (dev.alt_client && dev.id === "windows") {
      var note = document.createElement("p");
      note.className = "muted";
      note.textContent = dev.alt_client;
      list.parentElement.appendChild(note);
    }
    var verifyPanel = $("wizard-step-verify");
    var troublePanel = $("wizard-step-trouble");
    if (verifyPanel) verifyPanel.classList.add("hidden");
    if (troublePanel) troublePanel.classList.add("hidden");
    show("device");
  }

  function mountSharedSupport() {
    var mount = $("support-block-mount");
    if (mount && window.BenderPortalShared) {
      BenderPortalShared.renderSupportBlock(mount, content);
      mount.classList.remove("hidden");
    }
  }

  function renderWhyLimited() {
    var panel = $("why-limited");
    var home = content.home || {};
    if (!panel || isTelegramMiniApp() || !scarcityNarrativeEnabled()) {
      if (panel) panel.classList.add("hidden");
      return;
    }
    var title = $("why-limited-title");
    var body = $("why-limited-body");
    if (title && home.why_limited_title) title.textContent = home.why_limited_title;
    if (body && home.why_limited_body) {
      body.innerHTML = "";
      home.why_limited_body.split("\n\n").forEach(function (para) {
        if (!para.trim()) return;
        var p = document.createElement("p");
        p.textContent = para.trim();
        body.appendChild(p);
      });
    }
    panel.classList.remove("hidden");
  }

  function renderCabinetFaq() {
    var fold = $("cabinet-faq-fold");
    var list = $("cabinet-faq-list");
    var faq = content.faq;
    if (!fold || !list || !faq) return;
    if ($("cabinet-faq-title") && faq.title) {
      $("cabinet-faq-title").textContent = faq.title;
    }
    list.innerHTML = "";
    (faq.items || []).slice(0, 6).forEach(function (item) {
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
    if (isTelegramMiniApp() || isCabinetDedicatedPage()) {
      if (cabinetTabsEnabled()) {
        fold.classList.add("hidden");
        return;
      }
      fold.classList.remove("hidden");
    }
  }

  function browserCabinetUtilityItems() {
    var cab = content.cabinet || {};
    var statusHref = statusPageUrl();
    var items = [];
    var hasConfig = !!window.BVPN_CABINET_HAS_CONFIG || hasStoredSetup();
    var hasLoadedAccount = !!window.BVPN_CABINET_ACCOUNT_VISIBLE;
    if (hasConfig) {
      items.push({ label: cab.action_guide || "Инструкция", href: "/portal/guide.html" });
    }
    if (hasLoadedAccount) {
      items.push({ label: cab.action_status || "Статус", href: statusHref });
    }
    items.push({ label: cab.action_support || "Поддержка", href: SUPPORT_URL });
    return items;
  }

  function configureSharedSupportVisibility() {
    var mount = $("support-block-mount");
    if (!mount) return;
    if (isCabinetDedicatedPage() && !isTelegramMiniApp() && !shouldShowCabinetAccountPanel()) {
      mount.classList.add("hidden");
      return;
    }
    if (!isTelegramMiniApp() && !isCabinetDedicatedPage() && !hasStoredCabinetIdentity()) {
      mount.classList.add("hidden");
      return;
    }
    mount.classList.remove("hidden");
  }

  function renderCabinetActions() {
    var cab = content.cabinet || {};
    var wrap = $("cabinet-actions");
    if (!wrap) return;
    if (cabinetTabsEnabled() && (isTelegramMiniApp() || isCabinetDedicatedPage())) {
      wrap.classList.add("hidden");
      wrap.innerHTML = "";
      return;
    }
    if (!isTelegramMiniApp() && !isCabinetDedicatedPage()) {
      wrap.classList.add("hidden");
      return;
    }
    if (!isTelegramMiniApp() && !shouldShowCabinetAccountPanel()) {
      wrap.classList.add("hidden");
      return;
    }
    wrap.innerHTML = "";
    var items = isTelegramMiniApp()
      ? [
          { label: cab.action_setup || "Получить настройку", href: "/setup/" },
          { label: cab.action_guide || "Инструкция", href: "/portal/guide.html" },
          { label: cab.action_topup || "Пополнить баланс", href: SUPPORT_URL },
        ]
      : browserCabinetUtilityItems();
    if (referralUiEnabled()) {
      items.splice(3, 0, {
        label: cab.action_invite || "Пригласить друга",
        href: botUrlWithReferral(),
      });
    }
    items.push({ label: cab.action_support || "Поддержка", href: SUPPORT_URL });
    if (!items.length) {
      wrap.classList.add("hidden");
      return;
    }
    var title = document.createElement("p");
    title.className = "sheet__label";
    title.textContent = cab.actions_title || "Действия";
    wrap.appendChild(title);
    var grid = document.createElement("div");
    grid.className = "cabinet-actions__grid";
    items.forEach(function (item) {
      var a = document.createElement("a");
      a.className = "cabinet-action-card";
      a.href = item.href;
      a.textContent = item.label;
      if (/^https?:\/\/(t\.me|telegram\.me)/i.test(item.href)) {
        bindExternalLink(a);
      }
      grid.appendChild(a);
    });
    wrap.appendChild(grid);
    wrap.classList.remove("hidden");
  }

  function updateCabinetChrome() {
    if (!isCabinetDedicatedPage() && !isTelegramMiniApp()) return;
    if (isCabinetDedicatedPage()) document.body.classList.add("cabinet-page");
    var cab = content.cabinet || {};
    var grace = $("cabinet-grace");
    var sheet = $("account-sheet");
    var shell = $("cabinet-account-shell");
    var bottomNav = $("cabinet-bottom-nav");
    var recover = $("cabinet-recover-fold");
    var tg = isTelegramMiniApp();
    var showAccount = shouldShowCabinetAccountPanel();
    var tabs = cabinetTabsEnabled();

    if ($("cabinet-grace-title")) {
      $("cabinet-grace-title").textContent = cab.grace_title || "Открой ЛК из Telegram-бота";
    }
    if ($("cabinet-grace-lead")) {
      $("cabinet-grace-lead").textContent = cab.grace_lead || "";
    }
    if ($("cabinet-grace-tg-note")) {
      $("cabinet-grace-tg-note").textContent = cab.grace_path_tg_note || "";
    }
    if ($("cabinet-grace-email-note")) {
      $("cabinet-grace-email-note").textContent = cab.grace_path_email_note || "";
    }
    var graceBot = $("btn-cabinet-grace-bot");
    if (graceBot) {
      graceBot.textContent = cab.grace_cta_bot || cab.open_bot || "Открыть Telegram-бота";
      graceBot.href = botUrlWithReferral();
      bindExternalLink(graceBot);
    }
    var graceTrial = $("btn-cabinet-grace-trial");
    if (graceTrial) {
      graceTrial.textContent =
        cab.grace_cta_trial || content.buttons.setup_browser || "Временный доступ на 1 сутки";
      graceTrial.href = SETUP_PATH;
    }
    if ($("cabinet-recover-title")) {
      $("cabinet-recover-title").textContent =
        cab.recover_fold_title || "Уже получал доступ на сайте?";
    }
    if ($("cabinet-recover-lead")) {
      $("cabinet-recover-lead").textContent = cab.recover_fold_lead || "";
    }

    if (showAccount) {
      if (grace) grace.classList.add("hidden");
      if (tabs) {
        if (shell) shell.classList.remove("hidden");
        if (bottomNav) bottomNav.classList.remove("hidden");
        applyCabinetTabFromHash();
      } else if (sheet) {
        sheet.classList.remove("hidden");
      }
    } else {
      if (grace) grace.classList.remove("hidden");
      if (shell) shell.classList.add("hidden");
      if (bottomNav) bottomNav.classList.add("hidden");
      if (sheet && !tabs) sheet.classList.add("hidden");
    }
    if (recover) {
      if (!tg || isCabinetDedicatedPage()) recover.classList.remove("hidden");
      else recover.classList.add("hidden");
    }
    initCabinetTelegramIdHelper();
    renderCabinetActions();
    configureSharedSupportVisibility();
  }

  function showCabinetTelegramIdPanel(tid) {
    var cab = content.cabinet || {};
    var panel = $("cabinet-recover-id-panel");
    var label = $("cabinet-recover-id-label");
    var value = $("cabinet-recover-id-value");
    var copyBtn = $("btn-cabinet-copy-tg-id");
    var fallback = $("cabinet-recover-id-fallback");
    var fallbackLabel = $("cabinet-recover-id-fallback-label");
    var fallbackCode = $("cabinet-recover-id-fallback-code");
    if (!panel || !tid) return;
    if (label) label.textContent = cab.recover_tg_id_yours || "Твой Telegram ID:";
    if (value) value.textContent = String(tid);
    if (copyBtn) copyBtn.textContent = cab.recover_tg_id_copy || "Скопировать ID";
    if (fallback) fallback.classList.add("hidden");
    panel.classList.remove("hidden");
    if (copyBtn) {
      copyBtn.onclick = function () {
        copyTextWithInlineFallback(String(tid), {
          onSuccess: function () {
            if (fallback) fallback.classList.add("hidden");
            showToast(cab.recover_tg_id_copied || "ID скопирован");
          },
          onFail: function (idStr) {
            if (fallbackLabel) {
              fallbackLabel.textContent =
                cab.recover_tg_id_copy_manual || "Выдели и скопируй:";
            }
            if (fallbackCode) fallbackCode.textContent = idStr;
            if (fallback) fallback.classList.remove("hidden");
          },
        });
      };
    }
  }

  function initCabinetTelegramIdHelper() {
    var cab = content.cabinet || {};
    var hint = $("cabinet-recover-tg-hint");
    var btn = $("btn-cabinet-show-tg-id");
    if (hint) {
      hint.textContent =
        cab.recover_tg_id_hint ||
        "Не знаешь свой Telegram ID? Открой бота — он покажет ID автоматически.";
    }
    if (!btn) return;
    btn.textContent = cab.recover_tg_id_btn || "Узнать мой Telegram ID";
    btn.onclick = function () {
      if (hasTelegramInitContext()) {
        var tid = getTelegramUserId();
        if (tid > 0) {
          showCabinetTelegramIdPanel(tid);
          return;
        }
        showToast(
          cab.recover_tg_id_unavailable ||
            "Не удалось определить ID. Открой бота по кнопке выше.",
          "error"
        );
        return;
      }
      window.open(BOT_SHOW_ID_URL, "_blank", "noopener,noreferrer");
    };
  }

  function renderCabinetProfile() {
    var fold = $("cabinet-profile-fold");
    var prof = ((content && content.cabinet) || {}).profile || {};
    if (!fold || !prof.title) return;
    if ($("cabinet-profile-title")) $("cabinet-profile-title").textContent = prof.title;
    if ($("cabinet-profile-lead")) $("cabinet-profile-lead").textContent = prof.lead || "";
    if ($("cabinet-profile-stub")) {
      $("cabinet-profile-stub").textContent = prof.stub_note || "";
      $("cabinet-profile-stub").classList.toggle("hidden", !prof.stub_note);
    }
    if ($("cabinet-profile-manage-hint")) {
      $("cabinet-profile-manage-hint").textContent = prof.manage_hint || "";
    }
    var logout = $("cabinet-profile-logout");
    if (logout) {
      logout.textContent = prof.logout_label || "Выйти из кабинета";
      logout.onclick = cabinetLogout;
    }
    if ($("cabinet-profile-logout-hint")) {
      $("cabinet-profile-logout-hint").textContent = prof.logout_hint || "";
    }
    var del = $("cabinet-profile-delete");
    if (del) {
      del.textContent = prof.delete_request_label || "Запросить удаление данных";
      del.href = SUPPORT_URL;
      bindExternalLink(del);
    }
    if ($("cabinet-profile-delete-hint")) {
      $("cabinet-profile-delete-hint").textContent = prof.delete_request_hint || "";
    }
    if (isTelegramMiniApp() && cabinetTabsEnabled()) {
      fold.classList.remove("hidden");
    }
  }

  function profileRow(label, value, muted) {
    var row = document.createElement("div");
    row.className = "profile-list__row";
    var dt = document.createElement("dt");
    dt.textContent = label;
    var dd = document.createElement("dd");
    if (muted) dd.classList.add("muted");
    dd.textContent = value;
    row.appendChild(dt);
    row.appendChild(dd);
    return row;
  }

  function renderCabinetProfileData(doc) {
    var list = $("cabinet-profile-list");
    var prof = ((content && content.cabinet) || {}).profile || {};
    if (!list) return;
    list.innerHTML = "";
    var p = (doc && doc.profile) || {};
    var empty = prof.value_empty || "не указан";
    list.appendChild(profileRow(prof.email_label || "Email", p.email || empty, !p.email));
    list.appendChild(profileRow(prof.phone_label || "Телефон", p.phone || empty, !p.phone));
    var langLabel = p.language === "en" ? prof.lang_en || "English" : prof.lang_ru || "Русский";
    list.appendChild(profileRow(prof.language_label || "Язык", langLabel, false));
    var notif = p.notifications || {};
    var on = prof.notif_on || "включены";
    var off = prof.notif_off || "выкл.";
    var notifVal =
      (prof.notif_telegram || "Telegram") + ": " + (notif.telegram ? on : off) +
      " · " + (prof.notif_email || "Email") + ": " + (notif.email ? on : off);
    list.appendChild(profileRow(prof.notifications_label || "Уведомления", notifVal, true));
    var consents = p.consents || [];
    var verPrefix = prof.consent_version_prefix || "версия";
    var accepted = prof.consent_accepted || "принято";
    if (!consents.length) {
      list.appendChild(profileRow(prof.consents_label || "Согласия", prof.consent_none || "нет", true));
    } else {
      consents.forEach(function (c) {
        var name = c.doc === "privacy"
          ? prof.consent_privacy || "Политика конфиденциальности"
          : prof.consent_rules || "Правила сервиса";
        var val = accepted + " · " + verPrefix + " " + (c.version || "1");
        list.appendChild(profileRow(name, val, true));
      });
    }
  }

  function cabinetLogout() {
    try {
      localStorage.removeItem(CID_KEY);
      localStorage.removeItem(EMAIL_KEY);
    } catch (e) {
      /* ignore */
    }
    window.BVPN_CABINET_ACCOUNT_VISIBLE = false;
    var tg = isTelegramMiniApp() ? getTelegramWebApp() : null;
    if (tg && typeof tg.close === "function") {
      tg.close();
      return;
    }
    window.location.href = "/portal/";
  }

  function renderCabinet() {
    var cab = content.cabinet || {};
    var tg = isTelegramMiniApp();
    var dedicated = isCabinetDedicatedPage();
    if ($("cabinet-title")) {
      $("cabinet-title").textContent = cab.title || "Личный кабинет";
    }
    if ($("cabinet-lead")) {
      $("cabinet-lead").textContent = tg ? cab.lead_tg : cab.lead_web;
    }
    if ($("cabinet-lead-inline")) {
      if (dedicated) {
        $("cabinet-lead-inline").textContent = tg
          ? cab.lead_subline_tg ||
            cab.lead_subline ||
            "Здесь баланс, настройки устройств, инструкции и поддержка."
          : cab.lead_subline_web ||
            cab.lead_web ||
            "Полный личный кабинет открывается из Telegram-бота. В браузере здесь — временный доступ, инструкция и поддержка.";
      } else {
        $("cabinet-lead-inline").textContent = tg ? cab.lead_tg : cab.lead_web;
      }
    }
    if ($("cabinet-access-heading")) {
      $("cabinet-access-heading").textContent = cab.access_title || (cab.nav && cab.nav.access) || "Доступ";
    }
    if ($("account-heading") && cabinetTabsEnabled()) {
      $("account-heading").textContent = cab.balance_title || (cab.nav && cab.nav.balance) || "Баланс";
    }
    if ($("cabinet-support-heading")) {
      $("cabinet-support-heading").textContent =
        cab.support_title || (cab.nav && cab.nav.support) || "Поддержка";
    }
    var supportBtn = $("btn-cabinet-support");
    if (supportBtn) {
      supportBtn.textContent = cab.action_support || "Поддержка";
      supportBtn.href = SUPPORT_URL;
      bindExternalLink(supportBtn);
    }
    var topupBtn = $("btn-cabinet-topup");
    if (topupBtn) {
      topupBtn.textContent = cab.action_topup || "Пополнить баланс";
      topupBtn.href = botUrlWithReferral();
      bindExternalLink(topupBtn);
    }
    if ($("cabinet-balance-label")) {
      $("cabinet-balance-label").textContent = cab.balance_hero_label || cab.balance_label || "Текущий баланс";
    }
    if ($("cabinet-topup-title")) {
      $("cabinet-topup-title").textContent = cab.topup_title || "Пополнение баланса";
    }
    if ($("cabinet-topup-lead")) {
      $("cabinet-topup-lead").textContent =
        cab.topup_lead || "Выберите сумму — пополнение откроется в Telegram-боте.";
    }
    var topupNote = $("cabinet-topup-payment-note");
    var topupMeta = (content && content.topup) || {};
    if (topupNote && topupMeta.payment_note) {
      topupNote.textContent = topupMeta.payment_note;
    }
    renderCabinetProfile();
    if ($("cabinet-support-lead")) {
      $("cabinet-support-lead").textContent = cab.support_lead || content.support.message_hint || "";
    }
    if ($("cabinet-support-info-title")) {
      $("cabinet-support-info-title").textContent = cab.home_info_link || "Информация и документы";
    }
    if ($("cabinet-support-info-sub")) {
      $("cabinet-support-info-sub").textContent = cab.support_info_sub || "FAQ · правила · оферта";
    }
    if ($("cabinet-quick-balance-label")) {
      $("cabinet-quick-balance-label").textContent = cab.quick_balance || (cab.nav && cab.nav.balance) || "Баланс";
    }
    if ($("cabinet-quick-access-label")) {
      $("cabinet-quick-access-label").textContent = cab.quick_access || (cab.nav && cab.nav.access) || "Доступ";
    }
    if ($("cabinet-quick-info-label")) {
      $("cabinet-quick-info-label").textContent = cab.quick_info || "Информация";
    }
    if ($("cabinet-quick-support-label")) {
      $("cabinet-quick-support-label").textContent = cab.quick_support || (cab.nav && cab.nav.support) || "Поддержка";
    }
    renderTopupPresets();
    updateCabinetWelcome(window.BVPN_CABINET_DOC || null);
    updateCabinetMetrics(window.BVPN_CABINET_DOC || null);
    renderCabinetBottomNav();
    updateCabinetPrimaryCta(window.BVPN_CABINET_DOC || null);
    if ($("cabinet-configs-title")) {
      $("cabinet-configs-title").textContent = cab.configs_title || "Конфигурации";
    }
    if ($("cabinet-device-rule")) {
      $("cabinet-device-rule").textContent = cab.configs_device_rule || "";
    }
    var reuseNote = $("cabinet-device-reuse-note");
    if (reuseNote) {
      if (cab.configs_reuse_warning) {
        reuseNote.textContent = cab.configs_reuse_warning;
        reuseNote.classList.remove("hidden");
      } else {
        reuseNote.classList.add("hidden");
      }
    }
    var billingFuture = $("cabinet-devices-billing-note");
    if (billingFuture) {
      if (cab.configs_billing_future) {
        billingFuture.textContent = cab.configs_billing_future;
        billingFuture.classList.remove("hidden");
      } else {
        billingFuture.classList.add("hidden");
      }
    }
    // §3.7/§9.6: «Добавить устройство» — через поддержку (платный мульти-девайс gated).
    var addDev = $("btn-add-device");
    if (addDev) {
      addDev.textContent = cab.add_device_cta || cab.new_device_cta || "Добавить устройство через поддержку";
      addDev.href = botUrlWithReferral();
      bindExternalLink(addDev);
    }
    var addHint = $("add-device-hint");
    if (addHint) addHint.textContent = cab.add_device_hint || "";
    if ($("cabinet-device-rule-more")) {
      $("cabinet-device-rule-more").textContent = cab.configs_device_rule_more || "";
    }
    if ($("cabinet-location-line")) {
      $("cabinet-location-line").textContent = cab.location_line || "";
    }
    // D5: три действия разведены в коде; «Удалить слот» inert/скрыт до платного мульти-девайса.
    var delSlot = $("btn-delete-slot");
    if (delSlot) {
      delSlot.textContent = cab.delete_slot_cta || "Удалить слот";
      delSlot.href = botUrlWithReferral();
      bindExternalLink(delSlot);
      delSlot.classList.add("hidden");
    }
    var delSlotHint = $("delete-slot-hint");
    if (delSlotHint) delSlotHint.textContent = cab.delete_slot_hint || "";
    var replaceDev = $("btn-replace-device");
    if (replaceDev) {
      replaceDev.textContent = cab.replace_device_cta || "Заменить устройство";
      replaceDev.href = botUrlWithReferral();
      bindExternalLink(replaceDev);
    }
    var replaceHint = $("replace-device-hint");
    if (replaceHint) replaceHint.textContent = cab.replace_device_hint || "";
    var unbindDev = $("btn-unbind-device");
    if (unbindDev) {
      unbindDev.textContent = cab.unbind_device_cta || "Отвязать устройство";
      unbindDev.href = botUrlWithReferral();
      bindExternalLink(unbindDev);
    }
    var unbindHint = $("unbind-device-hint");
    if (unbindHint) unbindHint.textContent = cab.unbind_device_hint || "";
    if ($("cabinet-page-title")) {
      $("cabinet-page-title").textContent = cab.title || "Личный кабинет BenderVPN";
    }
    updateCabinetChrome();
    renderCabinetActions();
    renderCabinetFaq();
    var balLabel = $("cabinet-balance-label");
    var balVal = $("cabinet-balance");
    var balHint = $("cabinet-balance-hint");
    if (balLabel) balLabel.textContent = cab.balance_label || "Баланс";
    if (balVal) balVal.textContent = cab.balance_na || "—";
    if (balHint) balHint.textContent = cab.balance_hint || "";
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
    var botGhost = $("btn-cabinet-bot");
    if (botGhost) botGhost.textContent = cab.open_bot || "Открыть бота";
    var setupGhost = $("btn-cabinet-setup");
    if (setupGhost) {
      if (tg) {
        setupGhost.textContent =
          cab.setup_tg || (content.buttons && content.buttons.setup_tg) || "QR для Happ";
        setupGhost.href = "#";
      } else if (content.buttons && content.buttons.setup_browser) {
        setupGhost.textContent = content.buttons.setup_browser;
        setupGhost.href = SETUP_PATH;
      }
    }
    var bindBtn = $("btn-cabinet-bind");
    if (bindBtn) {
      bindBtn.textContent = cab.bind_tg || "Привязать Telegram";
    }
    if (botGhost) bindExternalLink(botGhost);
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
      var recoverFold = $("cabinet-recover-fold");
      if (recoverFold) recoverFold.classList.add("hidden");
    }
    configureBrowserAccountFold();
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

  function updateCabinetServerHealth() {
    // Агрегат серверов из публичного статуса (без отдельных локаций — канон §8.2).
    var wrap = $("cabinet-server-health");
    var dot = $("cabinet-server-health-dot");
    var txt = $("cabinet-server-health-text");
    if (!wrap || !txt) return;
    fetch(STATUS_JSON, { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("status json");
        return r.json();
      })
      .then(function (doc) {
        var vpn = ((doc || {}).components || {}).vpn || {};
        var summary = vpn.summary || "";
        if (!summary) {
          wrap.hidden = true;
          return;
        }
        txt.textContent = summary;
        if (dot) {
          dot.className = "cabinet-server-health__dot";
          var state = vpn.state || doc.overall || "ok";
          if (state === "ok") dot.classList.add("cabinet-server-health__dot--ok");
          else if (state === "degraded")
            dot.classList.add("cabinet-server-health__dot--warn");
          else dot.classList.add("cabinet-server-health__dot--unknown");
        }
        wrap.hidden = false;
      })
      .catch(function () {
        wrap.hidden = true;
      });
  }

  // §5: однострочники под сгибом home. Статичная копь из home_facts.
  function renderHomeFacts() {
    var f = (content && content.cabinet && content.cabinet.home_facts) || {};
    function set(id, val) {
      var el = $(id);
      if (el && val != null) el.textContent = val;
    }
    set("fact-nolimit-title", f.nolimit_title);
    set("fact-nolimit-text", f.nolimit_text);
    set("fact-private-title", f.private_title);
    set("fact-private-text", f.private_text);
    set("fact-devices-title", f.devices_title);
    set("fact-devices-text", f.devices_text);
    set("fact-devices-more", f.devices_more);
    set("fact-devices-more-text", f.devices_more_text);
    set("fact-connect-title", f.connect_title);
    set("fact-connect-text", f.connect_text);
    set("fact-connect-cta", f.connect_cta);
    set("fact-help-title", f.help_title);
    set("fact-help-text", f.help_text);
    set("fact-help-cta", f.help_cta);
    var connect = $("fact-connect");
    if (connect && !connect.dataset.bvpnBound) {
      connect.dataset.bvpnBound = "1";
      connect.addEventListener("click", function () {
        openConnectWizard();
      });
    }
    var help = $("fact-help");
    if (help) {
      help.href = SUPPORT_URL;
      bindExternalLink(help);
    }
  }

  function applyCabinetData(doc) {
    window.BVPN_CABINET_DOC = doc || null;
    var cab = content.cabinet || {};
    var balEl = $("cabinet-balance");
    var err = $("cabinet-load-error");
    if (err) err.classList.add("hidden");
    if (!doc || !doc.ok) {
      if (
        isCabinetDedicatedPage() &&
        !isTelegramMiniApp() &&
        !window.BVPN_CABINET_ACCOUNT_VISIBLE
      ) {
        updateCabinetChrome();
        renderCabinetActions();
        return;
      }
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
    var amount = String(Math.round(doc.balance_rub));
    var lowBalance =
      doc.billing_profile === "wallet" &&
      typeof doc.days_left === "number" &&
      doc.days_left <= 3;
    var balEl = $("cabinet-balance");
    if (balEl) {
      balEl.textContent = amount + " ₽";
      balEl.classList.toggle("cabinet-balance--low", lowBalance);
    }
    var hint = $("cabinet-balance-hint");
    if (hint) {
      var daysSuffix = (cab.balance_days_suffix || "хватит ~{days} дн.").replace(
        "{days}",
        String(doc.days_left)
      );
      if (doc.billing_note || doc.billing_note_text) {
        hint.textContent = doc.billing_note || doc.billing_note_text;
      } else if (doc.billing_profile === "trial" && cab.balance_hint_trial) {
        hint.textContent = cab.balance_hint_trial;
      } else {
        hint.textContent = (cab.balance_hint || "") + (daysSuffix ? " · " + daysSuffix : "");
      }
    }
    var accessEl = $("cabinet-access-state");
    if (accessEl) {
      accessEl.classList.add("cabinet-status-pill");
      if (doc.billing_profile === "legacy") {
        accessEl.textContent = cab.access_legacy || "Ручной доступ";
        accessEl.dataset.status = "legacy";
      } else {
        // §4: текст пилюли + тон по состоянию (фикс «оранжевого овала»).
        var pillKey = resolveCabinetStateKey(doc);
        var pillTone = {
          no_subscription: "inactive",
          trial_no_device: "trial",
          trial_connected: "active",
          paid_active: "active",
          expiring_soon: "warn",
          expired: "paused",
          slot_full: "warn",
        };
        var pillCopy = (cab.states && cab.states[pillKey]) || {};
        accessEl.textContent = pillCopy.pill || cab.access_active || "Доступ";
        accessEl.dataset.status = pillTone[pillKey] || "active";
      }
    }
    updateCabinetWelcome(doc);
    updateCabinetMetrics(doc);
    updateCabinetServerHealth();
    var cfgPanel = $("cabinet-configs-panel");
    var cfgList = $("cabinet-configs-list");
    var cfgSummary = $("cabinet-configs-summary");
    if (cfgPanel && cfgList && (isTelegramMiniApp() || isCabinetDedicatedPage())) {
      cfgList.innerHTML = "";
      var configs = doc.configurations || [];
      var activeCount =
        typeof doc.active_config_count === "number"
          ? doc.active_config_count
          : configs.filter(function (c) {
              return c.active || c.status === "active";
            }).length;
      if ($("cabinet-configs-title")) {
        $("cabinet-configs-title").textContent =
          cab.configs_title || "Мои устройства / настройки";
      }
      if (cfgSummary) {
        var countFmt = cab.configs_active_count || "Активные настройки: {count}";
        var countLine = countFmt.replace("{count}", String(activeCount));
        if (doc.multiple_configs_anomaly || activeCount > 1) {
          cfgSummary.textContent =
            countLine +
            ". " +
            (cab.configs_multi_anomaly ||
              "Обнаружено несколько активных настроек — напишите в поддержку.");
          cfgSummary.classList.remove("hidden");
        } else if (activeCount >= 1) {
          cfgSummary.textContent =
            countLine + ". " + (cab.configs_mvp_note || "");
          cfgSummary.classList.remove("hidden");
        } else if (activeCount === 0) {
          cfgSummary.textContent = cab.configs_empty || countLine;
          cfgSummary.classList.remove("hidden");
        } else {
          cfgSummary.textContent = "";
          cfgSummary.classList.add("hidden");
        }
      }
      if (!configs.length) {
        var li0 = document.createElement("li");
        li0.textContent = cab.configs_empty || "Активных настроек нет.";
        cfgList.appendChild(li0);
      } else {
        configs.forEach(function (c) {
          var li = document.createElement("li");
          var parts = [(c.label || "Конфигурация") + " · до " + (c.expires || c.expires_at || "—")];
          if (c.is_current || c.is_primary) {
            parts.push(cab.config_primary_badge || "текущая");
          }
          li.textContent = parts.join(" · ");
          var st = document.createElement("span");
          st.className = "config-list__status";
          var isActive = c.active || c.status === "active";
          st.textContent = isActive
            ? cab.config_status_active || "активна"
            : cab.config_status_expired || "истекла";
          li.appendChild(st);
          cfgList.appendChild(li);
        });
      }
      if ($("cabinet-device-rule")) {
        if (doc.multiple_configs_anomaly || activeCount > 1) {
          $("cabinet-device-rule").textContent = cab.configs_multi_anomaly || "";
        } else {
          $("cabinet-device-rule").textContent = cab.configs_device_rule || "";
        }
      }
      var reuseEl = $("cabinet-device-reuse-note");
      if (reuseEl && cab.configs_reuse_warning && activeCount >= 1) {
        reuseEl.textContent = cab.configs_reuse_warning;
        reuseEl.classList.remove("hidden");
      }
      var billNote = $("cabinet-devices-billing-note");
      if (billNote && cab.configs_billing_future && doc.billing_profile === "wallet") {
        billNote.textContent = cab.configs_billing_future;
        billNote.classList.remove("hidden");
      }
      cfgPanel.classList.remove("hidden");
      window.BVPN_CABINET_HAS_CONFIG = activeCount >= 1;
    }
    if (isCabinetDedicatedPage()) {
      if (doc.ok) window.BVPN_CABINET_ACCOUNT_VISIBLE = true;
      updateCabinetChrome();
    }
    updateCabinetPrimaryCta(doc);
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
    renderCabinetProfileData(doc);
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
    if (!cid.trim() && !email.trim()) {
      return;
    }
    window.BVPN_CABINET_ACCOUNT_VISIBLE = true;
    updateCabinetChrome();
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
    var params = new URLSearchParams(window.location.search || "");
    var view = (params.get("view") || "").trim();
    if (view) return view;
    var raw = (window.location.hash || "").replace(/^#/, "").trim();
    if (raw) return raw;
    var path = (window.location.pathname || "").toLowerCase();
    if (path.indexOf("cabinet.html") >= 0) return "cabinet";
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
    if (shouldAutoLoadCabinet()) {
      loadCabinetBalance();
    }
    if (!isCabinetDedicatedPage()) {
      focusAccountSheet();
    }
  }

  function applyRouteFromHash() {
    var raw = resolveRouteView();
    if (/^tab=(home|access|balance|support)$/.test(raw)) {
      show("home");
      if (shouldShowCabinetAccountPanel()) applyCabinetTabFromHash();
      return;
    }
    if (raw === "cabinet") {
      show("home");
      if (isCabinetDedicatedPage()) {
        if (isTelegramMiniApp()) loadCabinetBalance();
        var tabHash = (window.location.hash || "").replace(/^#/, "");
        if (/^tab=(home|access|balance|support)$/.test(tabHash) && shouldShowCabinetAccountPanel()) {
          applyCabinetTabFromHash();
        }
      } else {
        openCabinetView();
      }
      return;
    }
    if (raw === "devices" || raw === "connect") {
      openConnectWizard();
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
      loadBal.addEventListener("click", function () {
        window.BVPN_CABINET_ACCOUNT_VISIBLE = true;
        loadCabinetBalance();
      });
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
        openConnectWizard();
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
          openConnectWizard();
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
        if (cabinetTabsEnabled()) {
          show("home");
          setCabinetTab("home");
        } else {
          show("home");
        }
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

  // ЛОКАЛЬНЫЙ предпросмотр состояний home (§4) — только localhost, ?qa_state=KEY.
  // Не влияет на прод: гейт isLocalQaPreview(); мок-doc вместо API кабинета.
  function maybeApplyQaStateFixture() {
    if (!isLocalQaPreview()) return false;
    var key = (new URLSearchParams(window.location.search || "").get("qa_state") || "").trim();
    if (!key) return false;
    var active = [{ active: true, status: "active" }];
    var presets = {
      no_subscription: { ok: true, billing_profile: null, balance_rub: 0, days_left: 0, active_config_count: 0, device_slot_limit: 1 },
      trial_no_device: { ok: true, billing_profile: "trial", trial_days_left: 87, days_left: 87, balance_rub: 0, active_config_count: 0, device_slot_limit: 1 },
      trial_connected: { ok: true, billing_profile: "trial", trial_days_left: 87, days_left: 87, balance_rub: 0, active_config_count: 1, device_slot_limit: 1, configurations: active },
      paid_active: { ok: true, billing_profile: "wallet", days_left: 24, balance_rub: 160, active_config_count: 1, device_slot_limit: 1, configurations: active },
      expiring_soon: { ok: true, billing_profile: "wallet", days_left: 2, balance_rub: 13, active_config_count: 1, device_slot_limit: 1, configurations: active },
      expired: { ok: true, billing_profile: "expired", days_left: 0, balance_rub: 0, active_config_count: 0, device_slot_limit: 1 },
    };
    var doc = presets[key];
    if (!doc) return false;
    window.BVPN_CABINET_ACCOUNT_VISIBLE = true;
    show("home");
    updateCabinetChrome();
    applyCabinetData(doc);
    return true;
  }

  function fetchContentWithRetry(attempts) {
    return fetch(CONTENT_URL, { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("content load failed: " + r.status);
        return r.json();
      })
      .catch(function (e) {
        if (attempts > 1) {
          return new Promise(function (res) {
            setTimeout(res, 600);
          }).then(function () {
            return fetchContentWithRetry(attempts - 1);
          });
        }
        throw e;
      });
  }

  fetchContentWithRetry(3)
    .then(function (data) {
      content = data;
      initTelegram();
      if ($("hero-badge")) renderHome();
      if ($("device-grid")) renderDevices();
      renderCabinet();
      renderHomeFacts();
      renderWizardStaticCopy();
      bindActions();
      bindCabinetTabNav();
      bindWizardActions();
      bindSetupEntryButtons();
      applyRouteFromHash();
      maybeApplyQaStateFixture();
      window.addEventListener("hashchange", function () {
        var raw = (window.location.hash || "").replace(/^#/, "");
        if (/^(devices|connect|device|cabinet)/.test(raw)) applyRouteFromHash();
      });
      var route = resolveRouteView();
      if (route !== "cabinet" && route !== "devices" && !/^device=/.test(route)) {
        trackFunnel("portal_view_home");
      }
      if (isCabinetDedicatedPage()) {
        var initRoute = resolveRouteView();
        var keepView =
          initRoute === "devices" ||
          initRoute === "connect" ||
          initRoute === "device" ||
          /^device=/.test(initRoute);
        if (!keepView) show("home");
        if (shouldAutoLoadCabinet()) {
          loadCabinetBalance();
        }
      } else if (isTelegramMiniApp() || window.BVPN_FOCUS_ACCOUNT) {
        if (shouldAutoLoadCabinet()) {
          loadCabinetBalance();
        }
      }
      var footMount = $("site-footer-mount");
      if (footMount && window.BenderPortalShared) {
        if (!isTelegramMiniApp()) {
          BenderPortalShared.renderSiteFooter(footMount, content);
        } else {
          footMount.classList.add("hidden");
        }
        BenderPortalShared.bindStatusLinks(document);
      }
      if (isTelegramMiniApp()) {
        var supMount = $("support-block-mount");
        if (supMount) supMount.classList.add("hidden");
      } else {
        mountSharedSupport();
        configureSharedSupportVisibility();
      }
    })
    .catch(function () {
      showError(
        "Не удалось загрузить страницу. Проверьте интернет и обновите страницу."
      );
    });
})();
