/**
 * Service worker: caches the static app shell (HTML/CSS/JS/icons) for
 * offline availability, cache-first with a background revalidation fetch.
 *
 * For the API, most endpoints are network-only -- this app is a live
 * dispatch tool, so stale booking data would generally be actively harmful.
 * The two read endpoints the driver actually needs to see while offline
 * (the active schedule and completed-trip history) are the exception:
 * they're fetched network-first, but the last successful response is kept
 * in a separate cache and served as a fallback when the network fails.
 */
// Bump this on every deploy that touches an APP_SHELL file. cacheFirstStatic()
// below serves the cached copy first and only refreshes the cache in the
// background for the *next* load -- without a version bump, a browser that
// already has the shell cached can keep running old JS/CSS indefinitely,
// including JS containing already-fixed bugs.
const CACHE_NAME = "taxigo-ai-shell-v3";
const API_CACHE_NAME = "taxigo-ai-api-v1";
const CURRENT_CACHES = [CACHE_NAME, API_CACHE_NAME];

const APP_SHELL = [
  "/",
  "/config.js",
  "/css/styles.css",
  "/js/translations.js",
  "/js/voice.js",
  "/js/charts.js",
  "/js/notifications.js",
  "/js/app.js",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

// GET endpoints whose last successful response is worth keeping around for
// offline viewing. Everything else under isApiRequest() stays network-only.
const CACHEABLE_API_PATHS = ["/bookings", "/bookings/completed"];

const API_PATH_PREFIXES = ["/chat", "/bookings", "/analytics", "/clients", "/notifications", "/force-book", "/health"];

function isApiRequest(url) {
  return API_PATH_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => !CURRENT_CACHES.includes(key)).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

// Cache-first for the static app shell: instant load offline, with a
// background fetch to keep the cache fresh for next time.
async function cacheFirstStatic(request) {
  const cached = await caches.match(request, { cacheName: CACHE_NAME });
  const networkFetch = fetch(request)
    .then((response) => {
      if (response.ok) {
        caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
      }
      return response;
    })
    .catch(() => cached);
  return cached || networkFetch;
}

// Network-first for the schedule-critical API reads: always prefer live
// data, but fall back to the last good response when the network fails.
async function networkFirstApi(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request, { cacheName: API_CACHE_NAME });
    if (cached) return cached;
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (event.request.method !== "GET" || url.origin !== self.location.origin) {
    return; // let the browser handle non-GET and cross-origin requests natively
  }

  if (CACHEABLE_API_PATHS.includes(url.pathname)) {
    event.respondWith(networkFirstApi(event.request));
    return;
  }

  if (isApiRequest(url)) {
    return; // other API GETs (chat/analytics/clients/notifications/health): network only
  }

  event.respondWith(cacheFirstStatic(event.request));
});
