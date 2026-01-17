/* =====================================================
   SOID TF - Service Worker v4
   Cache + Push + Badge + Click
   ===================================================== */

const CACHE_NAME = "soid-tf-cache-v5";

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

  // Solo interceptar GET requests
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // ============================================
  // RUTAS QUE NO DEBEN SER INTERCEPTADAS
  // Dejar que el navegador las maneje directamente
  // ============================================
  if (url.pathname.startsWith("/admin")) return;
  if (url.pathname.startsWith("/accounts")) return;
  if (url.pathname.startsWith("/api")) return;
  if (url.pathname.startsWith("/notificaciones")) return;  // <-- IMPORTANTE

  // ============================================
  // HTML → Network First (guarda copia en cache)
  // ============================================
  if (req.headers.get("Accept") && req.headers.get("Accept").includes("text/html")) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          // Solo cachear respuestas exitosas
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return res;
        })
        .catch(() => {
          // Si falla la red, intentar desde cache
          return caches.match(req).then((cachedRes) => {
            if (cachedRes) return cachedRes;
            // Si no hay cache, devolver página offline básica
            return new Response(
              "<html><body><h1>Sin conexión</h1><p>Intenta de nuevo cuando tengas internet.</p></body></html>",
              { headers: { "Content-Type": "text/html; charset=utf-8" } }
            );
          });
        })
    );
    return;
  }

  // ============================================
  // Assets estáticos → Cache First + update
  // ============================================
  if (
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".jpg") ||
    url.pathname.endsWith(".jpeg") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".woff2") ||
    url.pathname.endsWith(".ico")
  ) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(req);

        // Actualizar cache en background
        const fetchPromise = fetch(req)
          .then((res) => {
            if (res && res.ok) {
              cache.put(req, res.clone());
            }
            return res;
          })
          .catch(() => null); // Ignorar errores de red para assets

        // Devolver cache si existe, sino esperar fetch
        return cached || fetchPromise || new Response("", { status: 404 });
      })
    );
    return;
  }

  // ============================================
  // Otras peticiones GET → Network only (sin cache)
  // No interceptamos, dejamos que el navegador maneje
  // ============================================
  // No llamamos event.respondWith() - el navegador maneja la petición
});

/* =====================
   PUSH NOTIFICATIONS
   ===================== */
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    console.warn("[SW] Error parseando push data:", e);
  }

  const title = data.title || "SOID";
  const body = data.body || "Tienes una notificación nueva.";
  const url = data.url || "/";
  const badgeCount = Number(data.badge_count || 0);

  event.waitUntil(
    (async () => {
      // Mostrar notificación
      await self.registration.showNotification(title, {
        body,
        data: { url },
        icon: "/static/core/icons/icon-192.png",
        badge: "/static/core/icons/icon-192.png",
        vibrate: [200, 100, 200],
        tag: "soid-notification",
        renotify: true,
      });

      // Avisar a la app abierta para refrescar campanita
      try {
        const clientsArr = await self.clients.matchAll({
          type: "window",
          includeUncontrolled: true,
        });

        for (const client of clientsArr) {
          client.postMessage({
            type: "PUSH_RECIBIDO",
            badge_count: badgeCount,
            url,
            title,
            body,
          });
        }
      } catch (e) {
        console.warn("[SW] Error enviando mensaje a clients:", e);
      }

      // Badge del icono (Android/Chrome/Edge)
      try {
        if (self.registration.setAppBadge) {
          if (badgeCount > 0) {
            await self.registration.setAppBadge(badgeCount);
          } else {
            await self.registration.clearAppBadge();
          }
        }
      } catch (e) {
        console.warn("[SW] Error actualizando badge:", e);
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

      // Buscar ventana existente y enfocarla
      for (const client of clientsArr) {
        if ("focus" in client) {
          await client.focus();
          if (client.navigate) {
            await client.navigate(url);
          }
          return;
        }
      }

      // Si no hay ventana abierta, abrir una nueva
      if (clients.openWindow) {
        await clients.openWindow(url);
      }
    })()
  );
});