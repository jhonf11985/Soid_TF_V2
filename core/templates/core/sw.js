/* Soid TF - Service Worker (mínimo) */
const CACHE_NAME = "soid-tf-cache-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// Opcional: cache básico de estáticos (simple y seguro)
self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Solo GET
  if (req.method !== "GET") return;

  // Evita cachear peticiones dinámicas típicas
  const url = new URL(req.url);
  if (url.pathname.startsWith("/admin")) return;
  if (url.pathname.startsWith("/accounts")) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(req);
      if (cached) return cached;

      const res = await fetch(req);
      // Cachea solo respuestas OK y del mismo origen
      if (res && res.status === 200 && url.origin === self.location.origin) {
        cache.put(req, res.clone());
      }
      return res;
    })
  );
});
