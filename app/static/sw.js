// kodakondsuseksam service worker.
// - cache-first for /static/* (CSS/JS/manifest/icons)
// - network-first for /api/*
// - stale-while-revalidate for HTML pages
// - offline fallback: cached "/"
// Bump VERSION on every deploy so old caches are evicted.

const VERSION = "v13-2026-05-27-sk-favicon-tutor-strip";
const STATIC_CACHE = `kodakond-static-${VERSION}`;
const PAGES_CACHE = `kodakond-pages-${VERSION}`;
const RUNTIME_CACHE = `kodakond-rt-${VERSION}`;

const PRECACHE_URLS = [
  "/",
  "/static/style.css",
  "/static/app.js",
  "/static/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => ![STATIC_CACHE, PAGES_CACHE, RUNTIME_CACHE].includes(k))
          .map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // API: network-first, never cache (results are private/per-session).
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(req));
    return;
  }

  // Static assets: cache-first.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(cacheFirst(req, STATIC_CACHE));
    return;
  }

  // HTML pages: stale-while-revalidate, with offline fallback to "/".
  if (req.mode === "navigate" || (req.headers.get("accept") || "").includes("text/html")) {
    event.respondWith(staleWhileRevalidate(req, PAGES_CACHE));
    return;
  }

  // Anything else: try cache, then network.
  event.respondWith(cacheFirst(req, RUNTIME_CACHE));
});

async function cacheFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  try {
    const res = await fetch(req);
    if (res && res.ok) cache.put(req, res.clone()).catch(() => {});
    return res;
  } catch (e) {
    return hit || Response.error();
  }
}

async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  const networkPromise = fetch(req)
    .then((res) => {
      if (res && res.ok) cache.put(req, res.clone()).catch(() => {});
      return res;
    })
    .catch(() => null);
  if (cached) {
    // Kick off background refresh; serve cached now.
    networkPromise;
    return cached;
  }
  const fresh = await networkPromise;
  if (fresh) return fresh;
  // Offline + no cached copy: fall back to the home page.
  const fallback = await cache.match("/") || await caches.match("/");
  return fallback || new Response("Offline", {
    status: 503,
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
