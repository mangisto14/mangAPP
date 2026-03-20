const CACHE = "mangapp-v1";
const STATIC = ["/", "/index.html"];

// Install: cache the app shell
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(STATIC))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch strategy:
//   /api/* → network-first, fall back to cache
//   everything else → cache-first, fall back to network
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  if (url.pathname.startsWith("/api/")) {
    // Network-first for API
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE).then((cache) => cache.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
  } else {
    // Cache-first for static assets
    e.respondWith(
      caches.match(e.request).then(
        (cached) =>
          cached ||
          fetch(e.request).then((res) => {
            const clone = res.clone();
            caches.open(CACHE).then((cache) => cache.put(e.request, clone));
            return res;
          })
      )
    );
  }
});
