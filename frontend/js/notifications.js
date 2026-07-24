/**
 * Socket.IO connection + notification bell panel + browser notifications.
 */
(function (global) {
  "use strict";

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

    socket = io({ transports: ["websocket", "polling"] });

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

  // Backend reminders embed raw English pickup/dropoff names even in the
  // Arabic message (message_ar) -- run them through translateLocation() so
  // no untranslated location names leak into the Arabic UI. No French
  // reminder text exists yet, so FR falls back to English here.
  function reminderMessageFor(payload) {
    const msg = currentLang === "ar" ? payload.message_ar : payload.message_en;
    return TaxiGoI18n.translateLocation(msg, currentLang);
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
      const res = await fetch("/notifications/recent");
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
