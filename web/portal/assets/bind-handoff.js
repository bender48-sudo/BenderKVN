/**
 * Portal → Telegram bind handoff helpers (pure, no secrets in telemetry).
 * Loaded before setup.js; exposed as window.BenderBindHandoff.
 */
(function (root) {
  "use strict";

  function parseBindUrl(bindUrl) {
    var u = (bindUrl || "").trim();
    if (!u) return null;
    try {
      var parsed = new URL(u);
      if (!/^(t\.me|telegram\.me)$/i.test(parsed.hostname)) return null;
      var bot = parsed.pathname.replace(/^\//, "").split("/")[0];
      var start = parsed.searchParams.get("start") || "";
      if (!bot || start.indexOf("bind_") !== 0) return null;
      var token = start.slice(5);
      if (!token || token.length < 16) return null;
      return {
        botUsername: bot,
        startPayload: start,
        startCommand: "/start " + start,
        tokenPrefix: token.slice(0, 6),
        httpsUrl: u,
        tgResolveUrl:
          "tg://resolve?domain=" +
          encodeURIComponent(bot) +
          "&start=" +
          encodeURIComponent(start),
      };
    } catch (e) {
      return null;
    }
  }

  function formatStartCommandPreview(startCommand, visiblePrefix) {
    var cmd = (startCommand || "").trim();
    var n = visiblePrefix == null ? 6 : visiblePrefix;
    var m = cmd.match(/^(\/start bind_)([a-f0-9]+)$/i);
    if (!m) return cmd;
    var tok = m[2];
    if (tok.length <= n) return cmd;
    return m[1] + tok.slice(0, n) + "\u2026";
  }

  root.BenderBindHandoff = {
    parseBindUrl: parseBindUrl,
    formatStartCommandPreview: formatStartCommandPreview,
  };
})(typeof window !== "undefined" ? window : globalThis);
