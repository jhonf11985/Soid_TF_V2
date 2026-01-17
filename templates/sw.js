/* =====================================================
   SOID TF - Service Worker v5
   Cache + Push + Badge + Click + PWA Install Fix
   ===================================================== */

const CACHE_NAME = "soid-tf-cache-v6";

// URLs que siempre queremos pre-cachear
const PRECACHE_URLS = [
  "/",
  "/offline/",  // Página offline personalizada (crear si no existe)
];

/* =====================
   INSTALL
   ===================== */
self.addEventListener("install", (event) => {
  console.log("[SW] Instalando versión v5...");
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log("[SW] Pre-cacheando recursos esenciales");
        // No fallar si alguna URL no existe
        return Promise.allSettled(
          PRECACHE_URLS.map(url => 
            cache.add(url).catch(err => console.warn(`[SW] No se pudo cachear: ${url}`, err))
          )
        );
      })
      .then(() => self.skipWaiting())
  );
});

/* =====================
   ACTIVATE
   ===================== */
self.addEventListener("activate", (event) => {
  console.log("[SW] Activando y limpiando cachés viejos...");
  
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log("[SW] Eliminando caché viejo:", key);
            return caches.delete(key);
          })
      ))
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
  // ============================================
  const excludedPaths = [
    "/admin",
    "/accounts",
    "/api",
    "/notificaciones",
    "/sw.js",           // El propio service worker
    "/manifest.json",   // Manifest siempre fresco
  ];
  
  if (excludedPaths.some(path => url.pathname.startsWith(path))) {
    return;
  }

  // ============================================
  // HTML → Network First con fallback a cache
  // ============================================
  if (req.headers.get("Accept")?.includes("text/html")) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          // Solo cachear respuestas exitosas (200-299)
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return res;
        })
        .catch(async () => {
          // Si falla la red, intentar desde cache
          const cachedRes = await caches.match(req);
          if (cachedRes) return cachedRes;
          
          // Intentar página offline
          const offlinePage = await caches.match("/offline/");
          if (offlinePage) return offlinePage;
          
          // Fallback básico
          return new Response(
            `<!DOCTYPE html>
            <html lang="es">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title>Sin Conexión - SOID</title>
              <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                  font-family: 'Poppins', -apple-system, sans-serif;
                  background: linear-gradient(135deg, #0097a7 0%, #006064 100%);
                  min-height: 100vh;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  padding: 20px;
                }
                .container {
                  background: white;
                  border-radius: 16px;
                  padding: 40px;
                  text-align: center;
                  max-width: 400px;
                  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }
                .icon { font-size: 64px; margin-bottom: 20px; }
                h1 { color: #0097a7; margin-bottom: 10px; font-size: 24px; }
                p { color: #666; margin-bottom: 20px; }
                button {
                  background: #0097a7;
                  color: white;
                  border: none;
                  padding: 12px 32px;
                  border-radius: 8px;
                  font-size: 16px;
                  cursor: pointer;
                }
                button:hover { background: #00838f; }
              </style>
            </head>
            <body>
              <div class="container">
                <div class="icon">📡</div>
                <h1>Sin Conexión</h1>
                <p>No hay conexión a internet. Verifica tu conexión e intenta de nuevo.</p>
                <button onclick="location.reload()">Reintentar</button>
              </div>
            </body>
            </html>`,
            { headers: { "Content-Type": "text/html; charset=utf-8" } }
          );
        })
    );
    return;
  }

  // ============================================
  // Assets estáticos → Cache First con update en background
  // ============================================
  const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.woff2', '.woff', '.ico', '.webp'];
  
  if (staticExtensions.some(ext => url.pathname.endsWith(ext))) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(req);

        // Actualizar cache en background (no bloqueante)
        const fetchPromise = fetch(req)
          .then((res) => {
            if (res && res.ok) {
              cache.put(req, res.clone());
            }
            return res;
          })
          .catch(() => null);

        // Devolver cache si existe, sino esperar fetch
        if (cached) {
          return cached;
        }
        
        const networkRes = await fetchPromise;
        if (networkRes) {
          return networkRes;
        }
        
        // Fallback para assets no encontrados
        return new Response("", { status: 404 });
      })
    );
    return;
  }

  // ============================================
  // Otras peticiones GET → No interceptar
  // ============================================
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
    try {
      data = { body: event.data?.text() || "Nueva notificación" };
    } catch (e2) {
      data = { body: "Nueva notificación" };
    }
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
        badge: "/static/core/icons/icon-72.png",
        vibrate: [200, 100, 200],
        tag: "soid-notification-" + Date.now(),
        renotify: true,
        requireInteraction: false,
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
        if ("setAppBadge" in self.navigator) {
          if (badgeCount > 0) {
            await self.navigator.setAppBadge(badgeCount);
          } else {
            await self.navigator.clearAppBadge();
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

      // Buscar ventana existente con el mismo origen
      for (const client of clientsArr) {
        if (client.url.startsWith(self.location.origin) && "focus" in client) {
          await client.focus();
          // Navegar a la URL si es diferente
          if (client.url !== self.location.origin + url) {
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

/* =====================
   MESSAGE (comunicación con la app)
   ===================== */
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") {
    self.skipWaiting();
  }
  
  if (event.data === "GET_VERSION") {
    event.ports[0]?.postMessage({ version: CACHE_NAME });
  }
});