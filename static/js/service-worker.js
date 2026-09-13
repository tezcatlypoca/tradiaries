// Service worker Tradiaries — cache runtime des assets statiques uniquement.
const CACHE_NAME = 'tradiaries-cache-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
        ))
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const { request } = event;
    if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) {
        return;
    }

    // Pages HTML : network-first. Toujours chercher la version fraîche du serveur, 
    // mais mettre en cache pour offline. Les données financières restent à jour tant 
    // que le réseau fonctionne, et l'app reste accessible hors ligne.
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).then((response) => {
                // Cache la réponse réussie pour offline
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                }
                return response;
            }).catch(() => caches.match(request))
        );
        return;
    }

    // Assets statiques : cache d'abord, réseau en secours + mise à jour du cache.
    if (request.url.includes('/static/')) {
        event.respondWith(
            caches.match(request).then((cached) => {
                const network = fetch(request).then((response) => {
                    if (response.ok) {
                        // Cloner avant d'utiliser la réponse (ne peut être clonée qu'une fois)
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
                    }
                    return response;
                }).catch(() => cached);
                return cached || network;
            })
        );
    }
});
