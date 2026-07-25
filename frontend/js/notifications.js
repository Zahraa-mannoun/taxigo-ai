/**
 * Socket.IO connection + notification bell panel + browser notifications.
 */
(function (global) {
  "use strict";

  // Same overrides as app.js -- empty means same-origin / no secret required.
  const API_BASE = global.TAXIGO_API_URL || "";
  const API_SECRET = global.TAXIGO_API_SECRET || "";

  let socket = null;
  let currentLang = "en";
  let notifications = [];
  let bookingEventHandler = null;

  const bellBtn = () => document.getElementById("notif-bell-btn");
  const panel = () => document.getElementById("notif-panel");
  const list = () => document.getElementById("notif-list");
  const badge = () => document.getElementById("notif-badge");

  function connectSocket() {
    if (socket || typeof io === "undefined") return;

    // io()'s first arg is the server URL; passing undefined for same-origin
    // (empty API_BASE) keeps existing behavior, a real URL targets the API
    // when the frontend is hosted separately.
    socket = io(API_BASE || undefined, { transports: ["websocket", "polling"] });

    socket.on("reminder", (payload) => {
      addNotification(payload);
      maybeShowBrowserNotification(payload);
      if (global.TaxiGoVoice) {
        const msg = reminderMessageFor(payload);
        global.TaxiGoVoice.speak(msg, currentLang);
      }
    });

    ["booking_created", "booking_updated", "booking_cancelled", "booking_status_updated"].forEach((evt) => {
      socket.on(evt, (booking) => {
        if (bookingEventHandler) bookingEventHandler(evt, booking);
      });
    });
  }

  function addNotification(payload) {
    notifications.unshift(payload);
    if (notifications.length > 50) notifications.pop();
    renderList();
    showBadge();
  }

  function showBadge() {
    const el = badge();
    if (el) el.classList.remove("hidden");
  }

  function clearBadge() {
    const el = badge();
    if (el) el.classList.add("hidden");
  }

  function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Backend reminders embed raw English pickup/dropoff names and the client's
  // stored (original) name in all three message_* variants -- run the
  // language-matched one through translateLocation()/translateName() so no
  // untranslated place or first name leaks into the AR UI, normalize the
  // EN/FR "->" into a real arrow glyph, and (AR only) switch to Arabic-Indic
  // digits for the embedded minutes-until countdown. The Arabic template
  // already reads "من X إلى Y" rather than using an arrow character, so
  // there's nothing to flip there -- only EN/FR need the "->" swap.
  function reminderMessageFor(payload) {
    let msg =
      currentLang === "ar" ? payload.message_ar : currentLang === "fr" ? payload.message_fr : payload.message_en;

    msg = TaxiGoI18n.translateLocation(msg, currentLang);

    if (payload.client_name) {
      const translatedName = TaxiGoI18n.translateName(payload.client_name, currentLang);
      if (translatedName !== payload.client_name) {
        msg = msg.replace(new RegExp(`\\b${escapeRegExp(payload.client_name)}\\b`, "g"), translatedName);
      }
    }

    if (currentLang === "ar") {
      msg = TaxiGoI18n.toArabicNumerals(msg);
    } else {
      msg = msg.replace(/->/g, "→");
    }

    return msg;
  }

  function renderList() {
    const container = list();
    if (!container) return;

    if (notifications.length === 0) {
      container.innerHTML = `<div class="notif-item">${TaxiGoI18n.t("noNotifications", currentLang)}</div>`;
      return;
    }

    container.innerHTML = notifications
      .map((n) => {
        const msg = reminderMessageFor(n);
        const time = n.fired_at ? new Date(n.fired_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) : "";
        return `<div class="notif-item"><div>${escapeHtml(msg)}</div><div class="notif-time">${time}</div></div>`;
      })
      .join("");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  async function loadRecentNotifications() {
    try {
      const res = await fetch(`${API_BASE}/notifications/recent`, {
        headers: API_SECRET ? { "X-API-Secret": API_SECRET } : {},
      });
      if (!res.ok) return;
      const data = await res.json();
      notifications = data.notifications || [];
      renderList();
      if (notifications.length > 0) showBadge();
    } catch (err) {
      // Non-fatal: bell just starts empty.
    }
  }

  function togglePanel() {
    const p = panel();
    if (!p) return;
    const willOpen = !p.classList.contains("open");
    p.classList.toggle("open", willOpen);
    if (willOpen) clearBadge();
  }

  function closePanel() {
    const p = panel();
    if (p) p.classList.remove("open");
  }

  function setLang(lang) {
    currentLang = lang;
    renderList();
  }

  function requestNotificationPermission() {
    if (!("Notification" in global)) return Promise.resolve("unsupported");
    return Notification.requestPermission();
  }

  function maybeShowBrowserNotification(payload) {
    if (!("Notification" in global) || Notification.permission !== "granted") return;
    new Notification(TaxiGoI18n.t("appName", currentLang), { body: reminderMessageFor(payload) });
  }

  function onBookingEvent(handler) {
    bookingEventHandler = handler;
  }

  function init(options) {
    currentLang = (options && options.lang) || "en";
    connectSocket();
    loadRecentNotifications();

    if (bellBtn()) {
      bellBtn().addEventListener("click", (e) => {
        e.stopPropagation();
        togglePanel();
      });
    }

    document.addEventListener("click", (e) => {
      const p = panel();
      if (p && p.classList.contains("open") && !p.contains(e.target) && e.target !== bellBtn()) {
        closePanel();
      }
    });
  }

  global.TaxiGoNotifications = {
    init,
    setLang,
    onBookingEvent,
    requestNotificationPermission,
    closePanel,
  };
})(window);
