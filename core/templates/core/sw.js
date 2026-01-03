/* Soid TF - Service Worker v2 */
const CACHE_NAME = "soid-tf-cache-v2"; // ← Cambia este número cuando hagas cambios importantes

self.addEventListener("install", (event) => {
  console.log("[SW] Instalando nueva versión...");
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  console.log("[SW] Activando y limpiando cachés viejos...");
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log("[SW] Eliminando caché viejo:", key);
            return caches.delete(key);
          })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Solo GET
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // No cachear rutas dinámicas
  if (url.pathname.startsWith("/admin")) return;
  if (url.pathname.startsWith("/accounts")) return;
  if (url.pathname.startsWith("/api")) return;

  // HTML → Network First (siempre intenta traer fresco)
  if (req.headers.get("Accept")?.includes("text/html")) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // CSS, JS, imágenes → Cache First con actualización en background
  if (
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".jpg") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".woff2")
  ) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(req);
        
        // Actualiza en background
        const fetchPromise = fetch(req).then((res) => {
          if (res && res.status === 200) {
            cache.put(req, res.clone());
          }
          return res;
        });

        return cached || fetchPromise;
      })
    );
    return;
  }

  // Resto → Network only
  event.respondWith(fetch(req));
});