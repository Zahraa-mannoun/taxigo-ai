/**
 * Main application logic: state, rendering, API calls and event wiring.
 * Depends on translations.js, voice.js, charts.js and notifications.js
 * having already been loaded (see index.html script order).
 */
(function () {
  "use strict";

  // Empty string ('') means same-origin -- the default for local dev and
  // for the bundled single-service Docker image. Override via config.js
  // (loaded before this script) for split-domain deployments.
  const API_BASE = window.TAXIGO_API_URL || "";
  const API_SECRET = window.TAXIGO_API_SECRET || "";

  const {
    t,
    isRtl,
    ONBOARDING_EXAMPLES,
    translateLocation,
    translateName,
    toArabicNumerals,
    formatDate: formatDateShared,
    formatTime: formatTimeShared,
    formatMoney: formatMoneyShared,
  } = window.TaxiGoI18n;

  const STATUS_KEY = {
    confirmed: "statusConfirmed",
    in_progress: "statusInProgress",
    completed: "statusCompleted",
    cancelled: "statusCancelled",
  };

  const state = {
    lang: localStorage.getItem("taxigo_lang") || "en",
    theme: localStorage.getItem("taxigo_theme") || "dark",
    activeBookings: [],
    historyBookings: [],
    filter: "all",
    search: "",
    sidebarTab: "bookings",
    conversationHistory: [],
    lastInputWasVoice: false,
    onboardingStep: 1,
    lastSyncedAt: Number(localStorage.getItem("taxigo_last_synced")) || null,
  };

  // ---------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }

  function todayISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function addDaysISO(isoDate, days) {
    const d = new Date(`${isoDate}T00:00:00`);
    d.setDate(d.getDate() + days);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  // Thin wrappers over the shared TaxiGoI18n formatters, bound to the
  // current UI language -- keeps call sites throughout this file unchanged.
  function formatTime(timeStr) {
    return formatTimeShared(timeStr, state.lang);
  }

  function formatDateLabel(dateStr) {
    return formatDateShared(dateStr, state.lang);
  }

  function formatMoney(amount) {
    return formatMoneyShared(amount, state.lang);
  }

  function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Pulls out every client name that might be embedded in this /chat
  // response's reply text, so localizeReplyText() knows what to translate.
  function extractClientNames(result) {
    const names = [];
    if (result.booking) names.push(result.booking.client_name);
    if (result.conflict) {
      if (result.conflict.conflicting_booking) names.push(result.conflict.conflicting_booking.client_name);
      if (result.conflict.pending_booking) names.push(result.conflict.pending_booking.client_name);
    }
    return names;
  }

  // Post-processes AI-generated reply text for display: translates any
  // recognized Lebanese location names and (AR only) common first names,
  // and (for AR/FR only) reformats the ISO dates / 12h times / dollar
  // amounts the backend embeds in its fixed English-authored templates into
  // the current language's conventions. EN is returned completely untouched.
  //
  // clientNames: names known to appear in THIS specific reply (pulled from
  // result.booking / result.conflict by the caller) -- translated by exact,
  // word-boundary-safe substitution rather than scanning the whole dictionary
  // against arbitrary text, which would risk false positives on ordinary
  // words that happen to also be names (e.g. "Grace").
  function localizeReplyText(text, clientNames) {
    if (!text || state.lang === "en") return text;
    let result = translateLocation(text, state.lang);

    if (state.lang === "ar" && clientNames && clientNames.length) {
      clientNames.filter(Boolean).forEach((name) => {
        const translated = translateName(name, state.lang);
        if (translated !== name) {
          result = result.replace(new RegExp(`\\b${escapeRegExp(name)}\\b`, "g"), translated);
        }
      });
    }

    result = result.replace(/\b\d{4}-\d{2}-\d{2}\b/g, (match) => formatDateShared(match, state.lang));

    result = result.replace(/\b(1[0-2]|0?[1-9]):([0-5][0-9])\s?(AM|PM)\b/gi, (match, h, m, period) => {
      const hour24 = period.toUpperCase() === "PM" ? (Number(h) % 12) + 12 : Number(h) % 12;
      return formatTimeShared(`${String(hour24).padStart(2, "0")}:${m}`, state.lang);
    });

    result = result.replace(/\$(\d+(?:\.\d{2})?)/g, (match, amount) => formatMoneyShared(amount, state.lang));

    // The backend's own format_date_localized/format_time_localized (Fix 5)
    // already emit Arabic month names and ص/م markers directly -- text like
    // "18 أغسطس 2026" never matches the ISO/AM-PM regexes above, so it skips
    // formatDateShared/formatTimeShared (and therefore toArabicNumerals)
    // entirely. Converting the whole result at the end catches those digits
    // too, consistent with every other AR surface (booking cards, etc.)
    // where no Western digit is ever shown. Safe to re-run over text the
    // regexes above already converted -- Arabic-Indic digits aren't in the
    // [0-9] class, so re-converting is a no-op there.
    if (state.lang === "ar") {
      result = toArabicNumerals(result);
    }

    return result;
  }

  async function api(path, options) {
    const headers = { "Content-Type": "application/json" };
    if (API_SECRET) headers["X-API-Secret"] = API_SECRET;
    const res = await fetch(`${API_BASE}${path}`, {
      headers,
      ...options,
    });
    if (!res.ok) {
      let detail = null;
      try {
        detail = await res.json();
      } catch (e) {
        /* ignore */
      }
      const err = new Error("api_error");
      err.detail = detail;
      err.status = res.status;
      throw err;
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ---------------------------------------------------------------------
  // i18n application
  // ---------------------------------------------------------------------
  function applyTranslations() {
    document.documentElement.lang = state.lang;
    document.documentElement.dir = isRtl(state.lang) ? "rtl" : "ltr";

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.getAttribute("data-i18n"), state.lang);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder"), state.lang));
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      el.setAttribute("title", t(el.getAttribute("data-i18n-title"), state.lang));
    });

    document.querySelectorAll(".lang-toggle button").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-lang") === state.lang);
    });

    renderSuggestionChips();
    renderLastSynced();

    const banner = document.getElementById("offline-banner");
    if (banner && !banner.classList.contains("hidden")) {
      banner.textContent = t("offlineBanner", state.lang);
    }
  }

  function setLang(lang) {
    if (lang === state.lang) return;
    state.lang = lang;
    localStorage.setItem("taxigo_lang", lang);
    applyTranslations();
    renderBookingsList();
    renderHistoryList();
    renderSummary();
    window.TaxiGoNotifications.setLang(lang);
    fetchGreeting();
  }

  // ---------------------------------------------------------------------
  // Theme
  // ---------------------------------------------------------------------
  function applyTheme() {
    document.documentElement.setAttribute("data-theme", state.theme);
    document.getElementById("theme-icon-moon").classList.toggle("hidden", state.theme === "light");
    document.getElementById("theme-icon-sun").classList.toggle("hidden", state.theme === "dark");
    document.getElementById("theme-toggle").title = t(
      state.theme === "dark" ? "themeToggleToLight" : "themeToggleToDark",
      state.lang
    );
  }

  function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem("taxigo_theme", state.theme);
    applyTheme();
    if (state.sidebarTab === "summary") renderWeeklyChartNow();
  }

  // ---------------------------------------------------------------------
  // Bookings list rendering
  // ---------------------------------------------------------------------
  function buildBookingCard(booking, opts) {
    const statusLabel = t(STATUS_KEY[booking.status] || "statusConfirmed", state.lang);
    const showActions = opts && opts.showActions !== false;

    let actionButtons = "";
    if (showActions && booking.status !== "cancelled" && booking.status !== "completed") {
      if (booking.status === "confirmed") {
        actionButtons += `<button data-action="in_progress" data-id="${booking.id}">${t("markInProgress", state.lang)}</button>`;
      }
      if (booking.status === "in_progress") {
        actionButtons += `<button data-action="completed" data-id="${booking.id}">${t("markCompleted", state.lang)}</button>`;
      }
      actionButtons += `<button data-action="cancel" data-id="${booking.id}" class="danger">${t("cancelBooking", state.lang)}</button>`;
    }
    // The data-client attribute drives the /clients/{name}/history lookup,
    // so it MUST stay the original stored name -- only the visible text
    // (clientDisplay, below) is translated.
    actionButtons += `<button data-action="client-history" data-client="${escapeHtml(booking.client_name)}">${t("viewClientHistory", state.lang)}</button>`;

    // Location and (common Lebanese first) names are translated for display
    // only -- the underlying booking object / DB values are never touched.
    const pickupDisplay = translateLocation(booking.pickup, state.lang);
    const dropoffDisplay = translateLocation(booking.dropoff, state.lang);
    const clientDisplay = translateName(booking.client_name, state.lang);
    const bookingNumber = state.lang === "ar" ? toArabicNumerals(booking.id) : booking.id;

    // In AR, the route reads right-to-left: keep pickup/dropoff in the same
    // DOM order as EN/FR (the surrounding RTL flex row visually reverses it
    // for us -- pickup ends up on the right, dropoff on the left) and just
    // swap the arrow glyph so it still points the right way.
    const arrow = state.lang === "ar" ? "←" : "→";

    return `
      <div class="booking-card status-${booking.status}" data-booking-id="${booking.id}">
        <div class="booking-card-top">
          <span class="booking-client">${escapeHtml(clientDisplay)} <span class="booking-number">#${bookingNumber}</span></span>
          <span class="status-badge status-${booking.status}">${statusLabel}</span>
        </div>
        <div class="booking-route">${escapeHtml(pickupDisplay)} ${arrow} ${escapeHtml(dropoffDisplay)}</div>
        <div class="booking-meta">
          <span>${formatDateLabel(booking.trip_date)} · ${formatTime(booking.trip_time)}</span>
          <span class="booking-fare">${formatMoney(booking.fare)}</span>
        </div>
        ${booking.notes ? `<div class="booking-notes">${escapeHtml(booking.notes)}</div>` : ""}
        <div class="booking-actions">${actionButtons}</div>
      </div>
    `;
  }

  function renderBookingsList() {
    const container = document.getElementById("bookings-list");
    if (!container) return;

    let items = state.activeBookings.slice();
    const today = todayISO();

    if (state.filter === "today") {
      items = items.filter((b) => b.trip_date === today);
    } else if (state.filter === "tomorrow") {
      items = items.filter((b) => b.trip_date === addDaysISO(today, 1));
    } else if (state.filter === "week") {
      const weekEnd = addDaysISO(today, 6);
      items = items.filter((b) => b.trip_date >= today && b.trip_date <= weekEnd);
    }

    if (state.search.trim()) {
      const q = state.search.trim().toLowerCase();
      items = items.filter((b) => {
        const pickupTranslated = translateLocation(b.pickup, state.lang).toLowerCase();
        const dropoffTranslated = translateLocation(b.dropoff, state.lang).toLowerCase();
        return (
          b.client_name.toLowerCase().includes(q) ||
          b.pickup.toLowerCase().includes(q) ||
          b.dropoff.toLowerCase().includes(q) ||
          pickupTranslated.includes(q) ||
          dropoffTranslated.includes(q)
        );
      });
    }

    items.sort((a, b) => (a.trip_date + a.trip_time).localeCompare(b.trip_date + b.trip_time));

    if (items.length === 0) {
      container.innerHTML = `<div class="empty-state">${t("noBookings", state.lang)}</div>`;
      return;
    }
    container.innerHTML = items.map((b) => buildBookingCard(b)).join("");
  }

  function renderHistoryList() {
    const container = document.getElementById("history-list");
    if (!container) return;

    const items = state.historyBookings
      .slice()
      .sort((a, b) => (b.trip_date + b.trip_time).localeCompare(a.trip_date + a.trip_time));

    const totalEarned = items.reduce((sum, b) => sum + Number(b.fare), 0);
    document.getElementById("history-total-earned").textContent = formatMoney(totalEarned);
    document.getElementById("history-total-trips").textContent =
      state.lang === "ar" ? toArabicNumerals(items.length) : String(items.length);

    if (items.length === 0) {
      container.innerHTML = `<div class="empty-state">${t("noBookings", state.lang)}</div>`;
      return;
    }
    container.innerHTML = items.map((b) => buildBookingCard(b, { showActions: false })).join("");
  }

  // ---------------------------------------------------------------------
  // Summary tab (earned/projected strip + weekly chart)
  // ---------------------------------------------------------------------
  let weeklyData = null;

  async function loadWeekly() {
    try {
      weeklyData = await api("/analytics/weekly");
      renderSummary();
    } catch (err) {
      /* non-fatal */
    }
  }

  function renderSummary() {
    if (!weeklyData) return;
    document.getElementById("summary-earned").textContent = formatMoney(weeklyData.total_earned);
    document.getElementById("summary-projected").textContent = formatMoney(weeklyData.total_projected);
    if (state.sidebarTab === "summary") renderWeeklyChartNow();
  }

  function renderWeeklyChartNow() {
    if (!weeklyData) return;
    window.TaxiGoCharts.renderWeeklyChart("weekly-chart", weeklyData.days, state.lang);
  }

  // ---------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------
  async function loadBookings() {
    try {
      state.activeBookings = await api("/bookings");
      renderBookingsList();
      // Only count this as a real sync if we're actually online -- if the
      // request succeeded while offline, it was served from the service
      // worker's cache, and "last synced" should keep pointing at the last
      // genuine network fetch, not this cache hit.
      if (navigator.onLine) markSynced();
    } catch (err) {
      /* non-fatal */
    }
  }

  async function loadHistory() {
    try {
      state.historyBookings = await api("/bookings/completed");
      renderHistoryList();
    } catch (err) {
      /* non-fatal */
    }
  }

  function refreshAll() {
    loadBookings();
    loadHistory();
    loadWeekly();
  }

  // ---------------------------------------------------------------------
  // Offline support: banner, "last synced" ticker, pending message queue,
  // and toasts (e.g. "Synced!" after reconnecting).
  // ---------------------------------------------------------------------
  const PENDING_MESSAGES_KEY = "taxigo_pending_messages";

  function loadPendingMessages() {
    try {
      const raw = JSON.parse(localStorage.getItem(PENDING_MESSAGES_KEY) || "[]");
      return Array.isArray(raw) ? raw : [];
    } catch (err) {
      return [];
    }
  }

  function savePendingMessages(list) {
    localStorage.setItem(PENDING_MESSAGES_KEY, JSON.stringify(list));
  }

  function queuePendingMessage(text) {
    const pending = loadPendingMessages();
    pending.push({ message: text, lang: state.lang, timestamp: Date.now() });
    savePendingMessages(pending);
  }

  function showOfflineBanner() {
    const el = document.getElementById("offline-banner");
    if (!el) return;
    el.textContent = t("offlineBanner", state.lang);
    el.classList.remove("hidden");
  }

  function hideOfflineBanner() {
    const el = document.getElementById("offline-banner");
    if (el) el.classList.add("hidden");
  }

  function showToast(message) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  function markSynced() {
    state.lastSyncedAt = Date.now();
    localStorage.setItem("taxigo_last_synced", String(state.lastSyncedAt));
    renderLastSynced();
  }

  function renderLastSynced() {
    const el = document.getElementById("sidebar-last-synced");
    if (!el) return;
    if (!state.lastSyncedAt) {
      el.textContent = "";
      return;
    }
    const minutes = Math.floor((Date.now() - state.lastSyncedAt) / 60000);
    el.textContent = minutes < 1 ? t("lastSyncedJustNow", state.lang) : t("lastSyncedMinutesAgo", state.lang, { minutes });
  }

  async function flushPendingMessages() {
    const pending = loadPendingMessages();
    if (pending.length === 0) return;
    savePendingMessages([]); // clear up front so a second reconnect event can't double-send

    for (const item of pending) {
      await dispatchChatRequest(item.message);
    }
    showToast(t("syncedNotification", state.lang));
  }

  function handleConnectivityChange() {
    if (navigator.onLine) {
      hideOfflineBanner();
      flushPendingMessages();
      refreshAll();
    } else {
      showOfflineBanner();
    }
  }

  // ---------------------------------------------------------------------
  // Chat
  // ---------------------------------------------------------------------
  function scrollChatToBottom() {
    const el = document.getElementById("chat-messages");
    el.scrollTop = el.scrollHeight;
  }

  function addChatBubble(text, role) {
    const el = document.getElementById("chat-messages");
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    bubble.textContent = text;
    el.appendChild(bubble);
    scrollChatToBottom();
    return bubble;
  }

  function addConflictBubble(conflict, replyText) {
    const el = document.getElementById("chat-messages");
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble conflict";

    const hasPending = !!conflict.pending_booking;
    bubble.innerHTML = `
      <div class="conflict-card-title">${t("conflictTitle", state.lang)}</div>
      <div>${escapeHtml(replyText)}</div>
      <div class="conflict-actions">
        ${hasPending ? `<button class="primary" id="force-book-btn">${t("conflictForceBook", state.lang)}</button>` : ""}
        <button id="pick-another-btn">${t("conflictPickAnother", state.lang)}</button>
      </div>
    `;
    el.appendChild(bubble);
    scrollChatToBottom();

    if (hasPending) {
      bubble.querySelector("#force-book-btn").addEventListener("click", async () => {
        try {
          await api("/force-book", { method: "POST", body: JSON.stringify(conflict.pending_booking) });
          bubble.remove();
          addChatBubble(t("statusConfirmed", state.lang), "assistant");
          refreshAll();
        } catch (err) {
          addChatBubble(t("connectionError", state.lang), "assistant");
        }
      });
    }
    bubble.querySelector("#pick-another-btn").addEventListener("click", () => bubble.remove());
  }

  function showTyping() {
    const el = document.getElementById("chat-messages");
    const typing = document.createElement("div");
    typing.className = "typing-indicator";
    typing.id = "typing-indicator";
    typing.innerHTML = "<span></span><span></span><span></span>";
    el.appendChild(typing);
    scrollChatToBottom();
  }

  function hideTyping() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
  }

  // Performs the actual /chat network call and renders the response. Shared
  // by live sends and by flushPendingMessages() -- callers are responsible
  // for having already shown the user's own message bubble.
  async function dispatchChatRequest(text) {
    const sendBtn = document.getElementById("send-btn");
    sendBtn.disabled = true;
    showTyping();

    try {
      const result = await api("/chat", {
        method: "POST",
        body: JSON.stringify({
          message: text,
          conversation_history: state.conversationHistory.slice(-12),
          lang: state.lang,
        }),
      });

      hideTyping();

      const clientNames = extractClientNames(result);
      const localizedReply = localizeReplyText(result.reply, clientNames);
      if (result.action === "conflict" && result.conflict) {
        addConflictBubble(result.conflict, localizedReply);
      } else {
        addChatBubble(localizedReply, "assistant");
      }
      // Conversation history sent back to the AI keeps the original
      // backend-authored text -- only the on-screen bubble is localized.
      state.conversationHistory.push({ role: "assistant", content: result.reply });

      if (state.lastInputWasVoice) {
        // Speak the localized text, not the raw backend reply -- result.reply
        // is always English-authored (see comment above); speaking it with
        // an Arabic/French utterance.lang just mispronounces English words
        // instead of actually speaking the target language.
        window.TaxiGoVoice.speak(localizedReply, state.lang);
        state.lastInputWasVoice = false;
      }

      if (result.refresh) {
        refreshAll();
      }
      return true;
    } catch (err) {
      hideTyping();
      if (!navigator.onLine) {
        queuePendingMessage(text);
        addChatBubble(t("noInternetChat", state.lang), "assistant");
      } else {
        addChatBubble(t("connectionError", state.lang), "assistant");
      }
      return false;
    } finally {
      sendBtn.disabled = false;
    }
  }

  async function sendMessage(text) {
    if (!text || !text.trim()) return;
    const input = document.getElementById("chat-input");

    addChatBubble(text, "user");
    state.conversationHistory.push({ role: "user", content: text });
    input.value = "";

    if (!navigator.onLine) {
      queuePendingMessage(text);
      addChatBubble(t("noInternetChat", state.lang), "assistant");
      return;
    }

    await dispatchChatRequest(text);
  }

  async function fetchGreeting() {
    const el = document.getElementById("chat-messages");
    let bubble = document.getElementById("greeting-bubble");
    try {
      const result = await api("/chat", {
        method: "POST",
        body: JSON.stringify({
          message: t("goodMorningPrompt", state.lang),
          conversation_history: [],
          lang: state.lang,
        }),
      });
      if (!bubble) {
        bubble = document.createElement("div");
        bubble.className = "chat-bubble assistant";
        bubble.id = "greeting-bubble";
        el.insertBefore(bubble, el.firstChild);
      }
      bubble.textContent = localizeReplyText(result.reply);
      scrollChatToBottom();
    } catch (err) {
      /* non-fatal: chat still usable without a greeting */
    }
  }

  function renderSuggestionChips() {
    const container = document.getElementById("suggestion-chips");
    if (!container) return;
    const keys = ["suggestion1", "suggestion2", "suggestion3", "suggestion4"];
    container.innerHTML = keys
      .map((k) => `<button class="suggestion-chip" data-text="${escapeHtml(t(k, state.lang))}">${escapeHtml(t(k, state.lang))}</button>`)
      .join("");
    container.querySelectorAll(".suggestion-chip").forEach((chip) => {
      chip.addEventListener("click", () => sendMessage(chip.getAttribute("data-text")));
    });
  }

  // ---------------------------------------------------------------------
  // Client history slide-in panel
  // ---------------------------------------------------------------------
  async function openClientHistory(clientName) {
    const overlay = document.getElementById("client-history-overlay");
    const panel = document.getElementById("client-history-panel");
    overlay.classList.add("open");
    panel.classList.add("open");
    // clientName (from data-client) is always the original stored name --
    // it's what the API call below needs. Only the heading TEXT is translated.
    document.getElementById("client-history-name").textContent = translateName(clientName, state.lang);
    document.getElementById("client-history-list").innerHTML = "";

    try {
      const data = await api(`/clients/${encodeURIComponent(clientName)}/history`);
      const earned = data.trips.reduce((sum, b) => (b.status === "completed" ? sum + Number(b.fare) : sum), 0);
      const projected = data.trips.reduce((sum, b) => sum + Number(b.fare), 0);
      document.getElementById("client-history-earned").textContent = formatMoney(earned);
      document.getElementById("client-history-projected").textContent = formatMoney(projected);
      document.getElementById("client-history-trips").textContent =
        state.lang === "ar" ? toArabicNumerals(data.total_trips) : String(data.total_trips);
      document.getElementById("client-history-list").innerHTML = data.trips.length
        ? data.trips.map((b) => buildBookingCard(b, { showActions: false })).join("")
        : `<div class="empty-state">${t("noBookings", state.lang)}</div>`;
    } catch (err) {
      document.getElementById("client-history-list").innerHTML = `<div class="empty-state">${t("loadError", state.lang)}</div>`;
    }
  }

  function closeClientHistory() {
    document.getElementById("client-history-overlay").classList.remove("open");
    document.getElementById("client-history-panel").classList.remove("open");
  }

  // ---------------------------------------------------------------------
  // Booking card action delegation (bookings list + history list)
  // ---------------------------------------------------------------------
  async function handleBookingAction(action, id, clientName) {
    if (action === "client-history") {
      openClientHistory(clientName);
      return;
    }
    if (action === "cancel") {
      if (!window.confirm(`${t("confirmCancelTitle", state.lang)}\n${t("confirmCancelBody", state.lang)}`)) return;
      try {
        await api(`/bookings/${id}`, { method: "DELETE" });
        refreshAll();
      } catch (err) {
        window.alert(t("connectionError", state.lang));
      }
      return;
    }
    if (action === "in_progress" || action === "completed") {
      try {
        await api(`/bookings/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: action }) });
        refreshAll();
      } catch (err) {
        window.alert(t("connectionError", state.lang));
      }
    }
  }

  function wireBookingListDelegation(containerId) {
    document.getElementById(containerId).addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-action]");
      if (!btn) return;
      handleBookingAction(btn.getAttribute("data-action"), btn.getAttribute("data-id"), btn.getAttribute("data-client"));
    });
  }

  // ---------------------------------------------------------------------
  // Sidebar tabs / mobile pane switching
  // ---------------------------------------------------------------------
  function setSidebarTab(tabName) {
    state.sidebarTab = tabName;
    document.querySelectorAll(".sidebar-tab").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
    });
    document.querySelectorAll(".tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === `tab-${tabName}`);
    });
    if (tabName === "summary") {
      renderWeeklyChartNow();
    } else {
      window.TaxiGoCharts.destroyChart();
    }
  }

  function setMobilePane(pane) {
    document.querySelectorAll(".mobile-pane").forEach((el) => el.classList.remove("active"));
    if (pane === "chat") {
      document.getElementById("view-chat").classList.add("active");
    } else {
      document.getElementById("sidebar").classList.add("active");
      setSidebarTab(pane);
    }
    document.querySelectorAll(".bottom-nav button").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-nav") === pane);
    });
  }

  // ---------------------------------------------------------------------
  // Onboarding
  // ---------------------------------------------------------------------
  function renderOnboardingExamples() {
    const container = document.getElementById("onboarding-examples");
    container.innerHTML = ONBOARDING_EXAMPLES.map((ex) => `<div>${ex}</div>`).join("");
  }

  function showOnboardingStep(step) {
    state.onboardingStep = step;
    [1, 2, 3].forEach((n) => {
      document.getElementById(`onboarding-step-${n}`).classList.toggle("hidden", n !== step);
    });
    document.querySelectorAll(".onboarding-steps-dots span").forEach((dot) => {
      dot.classList.toggle("active", Number(dot.getAttribute("data-step")) === step);
    });
    document.getElementById("onboarding-next").textContent =
      step === 3 ? t("onboardingGetStarted", state.lang) : t("onboardingNext", state.lang);
  }

  function finishOnboarding() {
    localStorage.setItem("taxigo_onboarded", "1");
    document.getElementById("onboarding-overlay").classList.add("hidden");
  }

  function maybeShowOnboarding() {
    if (localStorage.getItem("taxigo_onboarded")) return;
    renderOnboardingExamples();
    showOnboardingStep(1);
    document.getElementById("onboarding-overlay").classList.remove("hidden");
  }

  // ---------------------------------------------------------------------
  // PDF export (print API)
  // ---------------------------------------------------------------------
  async function exportPdf() {
    try {
      const data = await api("/analytics/export", { method: "POST", body: JSON.stringify({ scope: "today" }) });
      document.getElementById("print-date").textContent = new Date().toLocaleDateString(undefined, {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      });
      document.getElementById("print-table-body").innerHTML = data.trips
        .map(
          (b) => `
        <tr>
          <td>${escapeHtml(translateName(b.client_name, state.lang))}</td>
          <td>${escapeHtml(translateLocation(b.pickup, state.lang))}</td>
          <td>${escapeHtml(translateLocation(b.dropoff, state.lang))}</td>
          <td>${formatTime(b.trip_time)}</td>
          <td>${formatMoney(b.fare)}</td>
          <td>${escapeHtml(b.notes)}</td>
        </tr>`
        )
        .join("");
      window.print();
    } catch (err) {
      window.alert(t("connectionError", state.lang));
    }
  }

  // ---------------------------------------------------------------------
  // Voice input
  // ---------------------------------------------------------------------
  function setupMic() {
    const micBtn = document.getElementById("mic-btn");
    micBtn.addEventListener("click", () => {
      if (!window.TaxiGoVoice.isRecognitionSupported()) {
        window.alert(t("micNotSupported", state.lang));
        return;
      }
      if (window.TaxiGoVoice.isListening()) {
        window.TaxiGoVoice.stopListening();
        micBtn.classList.remove("recording");
        return;
      }
      micBtn.classList.add("recording");
      window.TaxiGoVoice.startListening(
        state.lang,
        (transcript) => {
          state.lastInputWasVoice = true;
          sendMessage(transcript);
        },
        (error) => {
          if (error === "permission_denied") window.alert(t("micPermissionDenied", state.lang));
          else if (error === "not_supported") window.alert(t("micNotSupported", state.lang));
        },
        () => micBtn.classList.remove("recording")
      );
    });
  }

  // ---------------------------------------------------------------------
  // Wiring
  // ---------------------------------------------------------------------
  function wireEvents() {
    document.getElementById("lang-toggle").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-lang]");
      if (btn) setLang(btn.getAttribute("data-lang"));
    });

    document.getElementById("theme-toggle").addEventListener("click", toggleTheme);

    document.getElementById("hamburger-btn").addEventListener("click", () => {
      document.getElementById("app-shell").classList.toggle("sidebar-collapsed");
    });

    document.querySelectorAll(".sidebar-tab").forEach((btn) => {
      btn.addEventListener("click", () => setSidebarTab(btn.getAttribute("data-tab")));
    });

    document.querySelectorAll(".bottom-nav button").forEach((btn) => {
      btn.addEventListener("click", () => setMobilePane(btn.getAttribute("data-nav")));
    });

    document.getElementById("search-input").addEventListener("input", (e) => {
      state.search = e.target.value;
      renderBookingsList();
    });

    document.querySelectorAll(".filter-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.filter = btn.getAttribute("data-filter");
        document.querySelectorAll(".filter-pill").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        renderBookingsList();
      });
    });

    wireBookingListDelegation("bookings-list");
    wireBookingListDelegation("history-list");
    wireBookingListDelegation("client-history-list");

    document.getElementById("client-history-close").addEventListener("click", closeClientHistory);
    document.getElementById("client-history-overlay").addEventListener("click", closeClientHistory);

    const chatInput = document.getElementById("chat-input");
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(chatInput.value);
      }
    });
    chatInput.addEventListener("input", () => {
      chatInput.style.height = "auto";
      chatInput.style.height = `${Math.min(chatInput.scrollHeight, 120)}px`;
    });
    document.getElementById("send-btn").addEventListener("click", () => sendMessage(chatInput.value));

    setupMic();

    document.getElementById("export-pdf-btn").addEventListener("click", exportPdf);
    document.getElementById("export-pdf-btn-2").addEventListener("click", exportPdf);

    document.getElementById("onboarding-next").addEventListener("click", () => {
      if (state.onboardingStep >= 3) finishOnboarding();
      else showOnboardingStep(state.onboardingStep + 1);
    });
    document.getElementById("onboarding-skip").addEventListener("click", finishOnboarding);
    document.getElementById("onboarding-enable-notif").addEventListener("click", () => {
      window.TaxiGoNotifications.requestNotificationPermission();
    });
    document.getElementById("onboarding-enable-mic").addEventListener("click", () => {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices
          .getUserMedia({ audio: true })
          .then((stream) => stream.getTracks().forEach((track) => track.stop()))
          .catch(() => {});
      }
    });

    window.TaxiGoNotifications.onBookingEvent(() => refreshAll());

    window.addEventListener("online", handleConnectivityChange);
    window.addEventListener("offline", handleConnectivityChange);
  }

  // ---------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------
  async function init() {
    if (!localStorage.getItem("taxigo_theme")) {
      localStorage.setItem("taxigo_theme", "dark");
      state.theme = "dark";
    }
    applyTheme();
    applyTranslations();
    wireEvents();

    if (!navigator.onLine) showOfflineBanner();
    renderLastSynced();
    setInterval(renderLastSynced, 60000);

    window.TaxiGoNotifications.init({ lang: state.lang });

    await Promise.all([loadBookings(), loadHistory(), loadWeekly()]);
    if (navigator.onLine) {
      fetchGreeting();
      flushPendingMessages();
    }
    maybeShowOnboarding();

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {});
    }

    const splash = document.getElementById("splash-screen");
    setTimeout(() => {
      splash.classList.add("fade-out");
      setTimeout(() => splash.remove(), 400);
    }, 900);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
