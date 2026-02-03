/// <reference lib="webworker" />

const CACHE_NAME = "paris-sportif-v1";
const STATIC_CACHE = "paris-sportif-static-v1";
const DYNAMIC_CACHE = "paris-sportif-dynamic-v1";
const API_CACHE = "paris-sportif-api-v1";

// Static assets to cache on install
const STATIC_ASSETS = [
  "/",
  "/picks",
  "/matches",
  "/offline",
  "/icons/icon-192x192.png",
  "/icons/icon-512x512.png",
  "/logo.svg",
];

// API routes to cache with network-first strategy
const API_ROUTES = [
  "/api/v1/predictions/daily-picks",
  "/api/v1/matches",
];

// Install event - cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => {
        console.log("[SW] Caching static assets");
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              return (
                name.startsWith("paris-sportif-") &&
                name !== STATIC_CACHE &&
                name !== DYNAMIC_CACHE &&
                name !== API_CACHE
              );
            })
            .map((name) => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache or network
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith("http")) {
    return;
  }

  // API requests - network first, cache fallback
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // Static assets - cache first
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Pages - stale while revalidate
  event.respondWith(staleWhileRevalidate(request, DYNAMIC_CACHE));
});

// Cache first strategy
async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    return caches.match("/offline");
  }
}

// Network first strategy
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    // Return offline JSON for API requests
    return new Response(
      JSON.stringify({ error: "Offline", cached: false }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

// Stale while revalidate strategy
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((networkResponse) => {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    })
    .catch(() => cachedResponse || caches.match("/offline"));

  return cachedResponse || fetchPromise;
}

// Check if request is for static asset
function isStaticAsset(pathname) {
  return (
    pathname.startsWith("/icons/") ||
    pathname.startsWith("/_next/static/") ||
    pathname.endsWith(".svg") ||
    pathname.endsWith(".png") ||
    pathname.endsWith(".jpg") ||
    pathname.endsWith(".ico") ||
    pathname.endsWith(".woff2")
  );
}

// Push notification handling
self.addEventListener("push", (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body || "Nouveau pronostic disponible!",
    icon: "/icons/icon-192x192.png",
    badge: "/icons/badge-72x72.png",
    vibrate: [100, 50, 100],
    data: {
      url: data.url || "/picks",
    },
    actions: [
      { action: "view", title: "Voir" },
      { action: "close", title: "Fermer" },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || "Paris Sportif", options)
  );
});

// Notification click handling
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  if (event.action === "close") return;

  const url = event.notification.data?.url || "/picks";
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      // Focus existing window if available
      for (const client of clients) {
        if (client.url.includes(url) && "focus" in client) {
          return client.focus();
        }
      }
      // Open new window
      return self.clients.openWindow(url);
    })
  );
});

// Background sync for offline picks
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-picks") {
    event.waitUntil(syncPicks());
  }
});

async function syncPicks() {
  try {
    const response = await fetch("/api/v1/predictions/daily-picks");
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      await cache.put("/api/v1/predictions/daily-picks", response);
    }
  } catch (error) {
    console.error("[SW] Sync failed:", error);
  }
}
