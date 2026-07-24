/**
 * All user-facing strings for TaxiGo AI, in English / Arabic / French.
 * Every piece of UI chrome text must be looked up through here -- never
 * hardcode a visible string anywhere else in the frontend.
 */
(function (global) {
  "use strict";

  const TRANSLATIONS = {
    en: {
      dir: "ltr",
      appName: "TaxiGo AI",
      splashTagline: "Your AI dispatch assistant",

      navChat: "Chat",
      navBookings: "Bookings",
      navHistory: "History",
      navSummary: "Summary",

      chatPlaceholder: "Type a message… e.g. \"Book Ali tomorrow 3pm from Hamra to the airport\"",
      send: "Send",
      typing: "TaxiGo AI is typing…",
      micStart: "Start voice input",
      micStop: "Stop voice input",
      micNotSupported: "Voice input isn't supported in this browser.",
      micPermissionDenied: "Microphone access was denied.",

      suggestion1: "Book Ali tomorrow at 3pm from Hamra to the airport",
      suggestion2: "What's on my schedule today?",
      suggestion3: "How much did I earn today?",
      suggestion4: "Mark Sara's trip as completed",

      searchPlaceholder: "Search by client, pickup or drop-off…",
      filterAll: "All",
      filterToday: "Today",
      filterTomorrow: "Tomorrow",
      filterWeek: "This Week",
      noBookings: "No bookings match here yet.",
      tripNotes: "Notes",
      fareLabel: "Fare",
      pickupLabel: "Pickup",
      dropoffLabel: "Drop-off",
      viewClientHistory: "View client history",
      markInProgress: "Mark in progress",
      markCompleted: "Mark completed",
      cancelBooking: "Cancel trip",
      confirmCancelTitle: "Cancel this trip?",
      confirmCancelBody: "This can't be undone from here.",
      confirmYes: "Yes, cancel it",
      confirmNo: "No, keep it",

      statusConfirmed: "Confirmed",
      statusInProgress: "In Progress",
      statusCompleted: "Completed",
      statusCancelled: "Cancelled",

      totalEarned: "Total earned",
      totalTrips: "Total trips",

      earnedLabel: "Earned",
      projectedLabel: "Projected",
      weeklyChartTitle: "Last 7 Days",
      exportPdfButton: "Export today's schedule (PDF)",

      printTitle: "TaxiGo AI — Schedule",
      printClient: "Client",
      printPickup: "Pickup",
      printDropoff: "Drop-off",
      printTime: "Time",
      printFee: "Fee",
      printNotes: "Notes",

      clientHistoryTitle: "Client History",
      close: "Close",

      notificationsTitle: "Notifications",
      noNotifications: "No notifications yet.",

      onboardingStep1Title: "Welcome to TaxiGo AI",
      onboardingStep1Body: "Your AI dispatcher. Chat naturally in English, Arabic or French to add trips, update your schedule, and track earnings — no forms to fill.",
      onboardingStep2Title: "Add a booking by chatting",
      onboardingStep2Body: "Just describe the trip like you would to a colleague. Try phrases like these:",
      onboardingStep3Title: "Stay on top of your day",
      onboardingStep3Body: "Enable notifications and microphone access so TaxiGo AI can remind you before pickups and let you speak instead of type.",
      onboardingSkip: "Skip",
      onboardingNext: "Next",
      onboardingEnableNotifications: "Enable notifications",
      onboardingEnableMic: "Enable microphone",
      onboardingGetStarted: "Get started",

      themeToggleToDark: "Switch to dark mode",
      themeToggleToLight: "Switch to light mode",
      menu: "Menu",

      conflictTitle: "Scheduling conflict",
      conflictForceBook: "Book anyway",
      conflictPickAnother: "I'll change it",

      connectionError: "Couldn't reach the server. Check your connection and try again.",
      loadError: "Something went wrong loading this. Please refresh.",
      goodMorningPrompt: "Give me a short, friendly good morning greeting to start my day.",

      installApp: "Install app",

      offlineBanner: "You're offline. Showing last saved schedule.",
      noInternetChat: "No internet connection. Your bookings are still visible.",
      messageQueuedOffline: "You're offline -- I'll send this as soon as you're back online.",
      syncedNotification: "Synced!",
      lastSyncedJustNow: "Last synced: just now",
      lastSyncedMinutesAgo: "Last synced: {minutes} min ago",
    },

    ar: {
      dir: "rtl",
      appName: "TaxiGo AI",
      splashTagline: "مساعدك الذكي لتنظيم الرحلات",

      navChat: "الدردشة",
      navBookings: "الحجوزات",
      navHistory: "السجل",
      navSummary: "الملخص",

      chatPlaceholder: "اكتب رسالة… مثلاً: احجزلي لعلي بكرا الساعة 3 من الحمرا عالمطار",
      send: "إرسال",
      typing: "TaxiGo AI عم يكتب…",
      micStart: "ابدأ الإدخال الصوتي",
      micStop: "أوقف الإدخال الصوتي",
      micNotSupported: "الإدخال الصوتي مش مدعوم بهالمتصفح.",
      micPermissionDenied: "تم رفض إذن استخدام المايكروفون.",

      suggestion1: "احجزلي لعلي بكرا الساعة 3 من الحمرا عالمطار",
      suggestion2: "شو عندي رحلات اليوم؟",
      suggestion3: "قديش ربحت اليوم؟",
      suggestion4: "خلصت رحلة سارة",

      searchPlaceholder: "دوّر باسم الزبون أو مكان الانطلاق أو الوصول…",
      filterAll: "الكل",
      filterToday: "اليوم",
      filterTomorrow: "بكرا",
      filterWeek: "هالأسبوع",
      noBookings: "ما في حجوزات هون لهلق.",
      tripNotes: "ملاحظات",
      fareLabel: "الأجرة",
      pickupLabel: "الانطلاق",
      dropoffLabel: "الوصول",
      viewClientHistory: "شوف سجل الزبون",
      markInProgress: "علّم قيد التنفيذ",
      markCompleted: "علّم مكتملة",
      cancelBooking: "الغِ الرحلة",
      confirmCancelTitle: "تريد إلغاء هالرحلة؟",
      confirmCancelBody: "ما فيك ترجع فيها من هون.",
      confirmYes: "إيه، الغيها",
      confirmNo: "لا، خليها",

      statusConfirmed: "مؤكدة",
      statusInProgress: "جارية",
      statusCompleted: "مكتملة",
      statusCancelled: "ملغية",

      totalEarned: "المجموع المكتسب",
      totalTrips: "عدد الرحلات",

      earnedLabel: "المكتسب",
      projectedLabel: "المتوقع",
      weeklyChartTitle: "آخر 7 أيام",
      exportPdfButton: "تصدير جدول اليوم (PDF)",

      printTitle: "TaxiGo AI — الجدول",
      printClient: "الزبون",
      printPickup: "الانطلاق",
      printDropoff: "الوصول",
      printTime: "الوقت",
      printFee: "الأجرة",
      printNotes: "ملاحظات",

      clientHistoryTitle: "سجل الزبون",
      close: "إغلاق",

      notificationsTitle: "الإشعارات",
      noNotifications: "ما في إشعارات لهلق.",

      onboardingStep1Title: "أهلاً فيك بـ TaxiGo AI",
      onboardingStep1Body: "مساعدك الذكي لتنظيم الرحلات. احكي معه عادي بالعربي أو الإنكليزي أو الفرنسي لتضيف رحلات وتحدّث جدولك وتتابع أرباحك — بلا فورمات.",
      onboardingStep2Title: "ضيف حجز عن طريق الدردشة",
      onboardingStep2Body: "احكي عن الرحلة متل ما بتحكي لرفيقك بالشغل. جرب عبارات متل هيدي:",
      onboardingStep3Title: "خلّيك مسيطر على يومك",
      onboardingStep3Body: "فعّل الإشعارات وإذن المايكروفون حتى TaxiGo AI يذكّرك قبل كل رحلة ويخليك تحكي بدل ما تكتب.",
      onboardingSkip: "تخطي",
      onboardingNext: "التالي",
      onboardingEnableNotifications: "فعّل الإشعارات",
      onboardingEnableMic: "فعّل المايكروفون",
      onboardingGetStarted: "ابدأ",

      themeToggleToDark: "بدّل للوضع الداكن",
      themeToggleToLight: "بدّل للوضع الفاتح",
      menu: "القائمة",

      conflictTitle: "تعارض بالمواعيد",
      conflictForceBook: "احجز رغم هيك",
      conflictPickAnother: "رح غيّرها",

      connectionError: "ما قدرنا نوصل للسيرفر. تأكد من الاتصال وجرب كمان مرة.",
      loadError: "صار في خطأ بالتحميل. جرب تحدّث الصفحة.",
      goodMorningPrompt: "عطيني صباح الخير قصيرة وودية لبلش يومي.",

      installApp: "ثبّت التطبيق",

      offlineBanner: "أنت غير متصل. يتم عرض آخر جدول محفوظ.",
      noInternetChat: "لا يوجد اتصال. رحلاتك لا تزال مرئية.",
      messageQueuedOffline: "أنت غير متصل -- رح ابعتها فور ما يرجع الاتصال.",
      syncedNotification: "تمت المزامنة!",
      lastSyncedJustNow: "آخر مزامنة: هلق",
      lastSyncedMinutesAgo: "آخر مزامنة: من {minutes} دقيقة",
    },

    fr: {
      dir: "ltr",
      appName: "TaxiGo AI",
      splashTagline: "Votre assistant de répartition IA",

      navChat: "Chat",
      navBookings: "Réservations",
      navHistory: "Historique",
      navSummary: "Résumé",

      chatPlaceholder: "Écrivez un message… ex. « Réserve Ali demain 15h de Hamra à l'aéroport »",
      send: "Envoyer",
      typing: "TaxiGo AI est en train d'écrire…",
      micStart: "Démarrer la saisie vocale",
      micStop: "Arrêter la saisie vocale",
      micNotSupported: "La saisie vocale n'est pas prise en charge sur ce navigateur.",
      micPermissionDenied: "L'accès au microphone a été refusé.",

      suggestion1: "Réserve Ali demain 15h de Hamra à l'aéroport",
      suggestion2: "Quel est mon programme aujourd'hui ?",
      suggestion3: "Combien ai-je gagné aujourd'hui ?",
      suggestion4: "Marque le trajet de Sara comme terminé",

      searchPlaceholder: "Rechercher par client, prise en charge ou destination…",
      filterAll: "Tous",
      filterToday: "Aujourd'hui",
      filterTomorrow: "Demain",
      filterWeek: "Cette semaine",
      noBookings: "Aucune réservation ici pour l'instant.",
      tripNotes: "Notes",
      fareLabel: "Tarif",
      pickupLabel: "Prise en charge",
      dropoffLabel: "Destination",
      viewClientHistory: "Voir l'historique du client",
      markInProgress: "Marquer en cours",
      markCompleted: "Marquer terminé",
      cancelBooking: "Annuler le trajet",
      confirmCancelTitle: "Annuler ce trajet ?",
      confirmCancelBody: "Cette action est irréversible depuis ici.",
      confirmYes: "Oui, annuler",
      confirmNo: "Non, garder",

      statusConfirmed: "Confirmé",
      statusInProgress: "En cours",
      statusCompleted: "Terminé",
      statusCancelled: "Annulé",

      totalEarned: "Total gagné",
      totalTrips: "Total des trajets",

      earnedLabel: "Gagné",
      projectedLabel: "Prévu",
      weeklyChartTitle: "7 derniers jours",
      exportPdfButton: "Exporter le programme du jour (PDF)",

      printTitle: "TaxiGo AI — Planning",
      printClient: "Client",
      printPickup: "Départ",
      printDropoff: "Arrivée",
      printTime: "Heure",
      printFee: "Tarif",
      printNotes: "Notes",

      clientHistoryTitle: "Historique du client",
      close: "Fermer",

      notificationsTitle: "Notifications",
      noNotifications: "Aucune notification pour le moment.",

      onboardingStep1Title: "Bienvenue sur TaxiGo AI",
      onboardingStep1Body: "Votre répartiteur IA. Discutez naturellement en anglais, arabe ou français pour ajouter des trajets, mettre à jour votre programme et suivre vos gains — sans aucun formulaire.",
      onboardingStep2Title: "Ajoutez une réservation en discutant",
      onboardingStep2Body: "Décrivez simplement le trajet comme à un collègue. Essayez des phrases comme celles-ci :",
      onboardingStep3Title: "Gardez le contrôle de votre journée",
      onboardingStep3Body: "Activez les notifications et le microphone pour que TaxiGo AI vous rappelle avant chaque prise en charge et vous permette de parler au lieu d'écrire.",
      onboardingSkip: "Passer",
      onboardingNext: "Suivant",
      onboardingEnableNotifications: "Activer les notifications",
      onboardingEnableMic: "Activer le microphone",
      onboardingGetStarted: "Commencer",

      themeToggleToDark: "Passer en mode sombre",
      themeToggleToLight: "Passer en mode clair",
      menu: "Menu",

      conflictTitle: "Conflit d'horaire",
      conflictForceBook: "Réserver quand même",
      conflictPickAnother: "Je vais changer",

      connectionError: "Impossible de joindre le serveur. Vérifiez votre connexion et réessayez.",
      loadError: "Une erreur est survenue. Merci de rafraîchir la page.",
      goodMorningPrompt: "Donne-moi une courte salutation matinale amicale pour commencer ma journée.",

      installApp: "Installer l'application",

      offlineBanner: "Vous êtes hors ligne. Affichage du dernier planning.",
      noInternetChat: "Pas de connexion. Vos réservations sont toujours visibles.",
      messageQueuedOffline: "Vous êtes hors ligne -- ce message sera envoyé dès que la connexion reviendra.",
      syncedNotification: "Synchronisé !",
      lastSyncedJustNow: "Dernière synchro : à l'instant",
      lastSyncedMinutesAgo: "Dernière synchro : il y a {minutes} min",
    },
  };

  // Fixed multilingual example phrases shown in onboarding step 2 --
  // deliberately NOT translated per-language, since the point is to show
  // the driver they can type in any of the three languages.
  const ONBOARDING_EXAMPLES = [
    "🇬🇧 \"Book Ali tomorrow at 3pm from Hamra to the airport\"",
    "🇱🇧 \"احجزلي لعلي بكرا الساعة 3 من الحمرا عالمطار\"",
    "🇫🇷 \"Réserve Ali demain 15h de Hamra à l'aéroport\"",
  ];

  const RTL_LANGS = ["ar"];

  function t(key, lang, vars) {
    const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
    let text = dict[key] !== undefined ? dict[key] : (TRANSLATIONS.en[key] || key);
    if (vars) {
      Object.keys(vars).forEach((k) => {
        text = text.replace(new RegExp(`\\{${k}\\}`, "g"), vars[k]);
      });
    }
    return text;
  }

  function isRtl(lang) {
    return RTL_LANGS.indexOf(lang) !== -1;
  }

  // --------------------------------------------------------------------
  // Location name translation (Fix 6). Client names are NEVER looked up
  // here -- only pickup/dropoff location strings should ever be passed in.
  // --------------------------------------------------------------------
  const LOCATIONS = {
    'beirut': { ar: 'بيروت', fr: 'Beyrouth' },
    'tripoli': { ar: 'طرابلس', fr: 'Tripoli' },
    'saida': { ar: 'صيدا', fr: 'Saïda' },
    'sidon': { ar: 'صيدا', fr: 'Saïda' },
    'tyre': { ar: 'صور', fr: 'Tyr' },
    'sour': { ar: 'صور', fr: 'Tyr' },
    'jounieh': { ar: 'جونيه', fr: 'Jounieh' },
    'zahle': { ar: 'زحلة', fr: 'Zahlé' },
    'baalbek': { ar: 'بعلبك', fr: 'Baalbek' },
    'nabatieh': { ar: 'النبطية', fr: 'Nabatieh' },
    'aley': { ar: 'عاليه', fr: 'Aley' },
    'byblos': { ar: 'جبيل', fr: 'Byblos' },
    'jbeil': { ar: 'جبيل', fr: 'Byblos' },
    'batroun': { ar: 'البترون', fr: 'Batroun' },
    'chouf': { ar: 'الشوف', fr: 'Chouf' },
    'metn': { ar: 'المتن', fr: 'Metn' },
    'kesrouan': { ar: 'كسروان', fr: 'Kesrouan' },
    'akkar': { ar: 'عكار', fr: 'Akkar' },
    'hamra': { ar: 'الحمرا', fr: 'Hamra' },
    'downtown': { ar: 'وسط بيروت', fr: 'Centre-ville' },
    'verdun': { ar: 'فردان', fr: 'Verdun' },
    'achrafieh': { ar: 'الأشرفية', fr: 'Achrafieh' },
    'ashrafieh': { ar: 'الأشرفية', fr: 'Achrafieh' },
    'mar mikhael': { ar: 'مار مخايل', fr: 'Mar Mikhael' },
    'gemmayzeh': { ar: 'الجميزة', fr: 'Gemmayzeh' },
    'raouche': { ar: 'الروشة', fr: 'Raouché' },
    'corniche': { ar: 'الكورنيش', fr: 'Corniche' },
    'sodeco': { ar: 'سوديكو', fr: 'Sodeco' },
    'badaro': { ar: 'بدارو', fr: 'Badaro' },
    'sanayeh': { ar: 'الصنايع', fr: 'Sanayeh' },
    'ras beirut': { ar: 'رأس بيروت', fr: 'Ras Beyrouth' },
    'dekwaneh': { ar: 'الدكوانة', fr: 'Dekwaneh' },
    'sin el fil': { ar: 'سن الفيل', fr: 'Sin el Fil' },
    'bourj hammoud': { ar: 'برج حمود', fr: 'Bourj Hammoud' },
    'jdeideh': { ar: 'الجديدة', fr: 'Jdeideh' },
    'cola': { ar: 'كولا', fr: 'Cola' },
    'tayouneh': { ar: 'الطيونة', fr: 'Tayouneh' },
    'chiyah': { ar: 'الشياح', fr: 'Chiyah' },
    'ghobeiry': { ar: 'الغبيري', fr: 'Ghobeiry' },
    'haret hreik': { ar: 'حارة حريك', fr: 'Haret Hreik' },
    'dahiyeh': { ar: 'الضاحية', fr: 'Dahiyeh' },
    'airport': { ar: 'المطار', fr: 'Aéroport' },
    'rafic hariri airport': { ar: 'مطار رفيق الحريري', fr: 'Aéroport Rafic Hariri' },
    'port': { ar: 'المرفأ', fr: 'Port' },
    'port of beirut': { ar: 'مرفأ بيروت', fr: 'Port de Beyrouth' },
    'hospital': { ar: 'المستشفى', fr: 'Hôpital' },
    'aub': { ar: 'الجامعة الأمريكية', fr: 'AUB' },
    'lau': { ar: 'الجامعة اللبنانية الأمريكية', fr: 'LAU' },
    'usj': { ar: 'جامعة القديس يوسف', fr: 'USJ' },
    'lebanese university': { ar: 'الجامعة اللبنانية', fr: 'Université Libanaise' },
    'mall': { ar: 'المول', fr: 'Centre commercial' },
    'city centre': { ar: 'سيتي سنتر', fr: 'City Centre' },
    'dbayeh': { ar: 'ضبيه', fr: 'Dbayeh' },
    'antelias': { ar: 'أنطلياس', fr: 'Antelias' },
    'zalka': { ar: 'الزلقا', fr: 'Zalka' },
    'naccache': { ar: 'النقاش', fr: 'Naccache' },
    'annar': { ar: 'النار', fr: 'Annar' },
  };

  function translateLocation(text, targetLang) {
    if (!text || targetLang === 'en') return text;
    let result = text;
    const lower = text.toLowerCase();
    if (LOCATIONS[lower]) return LOCATIONS[lower][targetLang] || text;
    Object.entries(LOCATIONS).forEach(([en, translations]) => {
      const regex = new RegExp(`\\b${en}\\b`, 'gi');
      if (regex.test(result)) {
        result = result.replace(regex, translations[targetLang] || en);
      }
    });
    return result;
  }

  // --------------------------------------------------------------------
  // Locale-aware date/time/money formatting (Fix 5). EN is left byte-for-byte
  // as it was before -- only AR/FR get the new formats. Shared by app.js
  // and charts.js so there's one source of truth for both.
  // --------------------------------------------------------------------
  const AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
  const FR_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  const AR_PERIOD = { AM: "ص", PM: "م" };

  // dateStr: "YYYY-MM-DD". withYear defaults true; charts.js passes false
  // for compact axis labels.
  function formatDate(dateStr, lang, withYear) {
    if (!dateStr) return "";
    if (lang === "ar" || lang === "fr") {
      const [y, m, d] = dateStr.split("-").map(Number);
      const months = lang === "ar" ? AR_MONTHS : FR_MONTHS;
      return withYear === false ? `${d} ${months[m - 1]}` : `${d} ${months[m - 1]} ${y}`;
    }
    // en: unchanged short format
    const date = new Date(`${dateStr}T00:00:00`);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  // timeStr: "HH:MM" or "HH:MM:SS", 24h in, formatted per language out.
  function formatTime(timeStr, lang) {
    if (!timeStr) return "";
    const [hStr, mStr] = timeStr.split(":");
    let h = parseInt(hStr, 10);
    const m = (mStr || "00").padStart(2, "0");

    if (lang === "fr") {
      return `${String(h).padStart(2, "0")}:${m}`;
    }

    const period = h >= 12 ? "PM" : "AM";
    let h12 = h % 12;
    if (h12 === 0) h12 = 12;
    if (lang === "ar") {
      return `${h12}:${m} ${AR_PERIOD[period]}`;
    }
    return `${h12}:${m} ${period}`; // en: unchanged
  }

  function formatMoney(amount, lang) {
    const fixed = Number(amount).toFixed(2);
    if (lang === "fr") return `${fixed.replace(".", ",")} $`;
    if (lang === "ar") return `${fixed}$`;
    return `$${fixed}`; // en: unchanged
  }

  global.TaxiGoI18n = {
    TRANSLATIONS,
    ONBOARDING_EXAMPLES,
    t,
    isRtl,
    LOCATIONS,
    translateLocation,
    formatDate,
    formatTime,
    formatMoney,
  };
})(window);
