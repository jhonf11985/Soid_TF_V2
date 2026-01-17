/* =====================================================
   SOID TF - Service Worker v3
   Cache + Push + Badge + Click
   ===================================================== */

const CACHE_NAME = "soid-tf-cache-v3"; // ← subimos versión

/* =====================
   INSTALL / ACTIVATE
   ===================== */
self.addEventListener("install", (event) => {
  console.log("[SW] Instalando nueva versión...");
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  console.log("[SW] Activando y limpiando cachés viejos...");
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => {
              console.log("[SW] Eliminando caché viejo:", key);
              return caches.delete(key);
            })
        )
      )
      .then(() => self.clients.claim())
  );
});

/* =====================
   FETCH (cache/offline)
   ===================== */
self.addEventListener("fetch", (event) => {
  const req = event.request;

  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // No cachear admin, auth y API
  if (url.pathname.startsWith("/admin")) return;
  if (url.pathname.startsWith("/accounts")) return;
  if (url.pathname.startsWith("/api")) return;

  // HTML → Network First (guarda copia en cache)
  if (req.headers.get("Accept") && req.headers.get("Accept").includes("text/html")) {
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

  // Assets → Cache First + update
  if (
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".jpg") ||
    url.pathname.endsWith(".jpeg") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".woff2")
  ) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(req);

        const fetchPromise = fetch(req).then((res) => {
          if (res && res.status === 200) cache.put(req, res.clone());
          return res;
        });

        return cached || fetchPromise;
      })
    );
    return;
  }

  event.respondWith(fetch(req));
});

/* =====================
   PUSH NOTIFICATIONS
   ===================== */
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {}

  const title = data.title || "SOID";
  const body = data.body || "Tienes una notificación nueva.";
  const url = data.url || "/";
  const badgeCount = Number(data.badge_count || 0);

  event.waitUntil(
    (async () => {
      await self.registration.showNotification(title, {
        body,
        data: { url },
        icon: "/static/core/icons/icon-192.png",
        badge: "/static/core/icons/icon-192.png",
      });

      // Badge del icono (Android/Chrome/Edge)
      if (self.registration.setAppBadge) {
        if (badgeCount > 0) await self.registration.setAppBadge(badgeCount);
        else await self.registration.clearAppBadge();
      }
    })()
  );
});

/* =====================
   CLICK EN NOTIFICACIÓN
   ===================== */
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/";

  event.waitUntil(
    (async () => {
      const clientsArr = await clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });

      for (const client of clientsArr) {
        if ("focus" in client) {
          await client.focus();
          await client.navigate(url);
          return;
        }
      }

      if (clients.openWindow) await clients.openWindow(url);
    })()
  );
});
