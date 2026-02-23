/**
 * PecheurConnect v3.0 - Service Worker FINAL
 * Gestion Offline, Audio Wolof & Data Copernicus
 */

// ================================================================
// ACTIVATION : Nettoyage et Prise de contrôle
// ================================================================
self.addEventListener('activate', event => {
    console.log('[SW] Activation de PecheurConnect v3.0...');
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.map(key => {
                    // Supprime les anciens caches (y compris ceux de l'ancienne version SunuBlueTech)
                    if (![CACHE_STATIC, CACHE_DYNAMIC, CACHE_DATA].includes(key)) {
                        console.log('[SW] Suppression du cache obsolète :', key);
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    // Permet au SW de prendre le contrôle des pages immédiatement
    return self.clients.claim();
});

// ================================================================
// STRATÉGIE DE FETCH (Le cœur du mode Offline)
// ================================================================
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // 1. STRATÉGIE "NETWORK FIRST" : Données Météo & Copernicus
    // On veut les données les plus fraîches possibles. Si pas de réseau, on prend le cache.
    if (url.pathname.endsWith('.json') || url.href.includes('copernicus')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const clonedRes = response.clone();
                    caches.open(CACHE_DATA).then(cache => cache.put(event.request, clonedRes));
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // 2. STRATÉGIE "CACHE FIRST" : Assets, Scripts et Audio Wolof
    // Vital pour économiser la batterie et le forfait, et pour l'audio au large.
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            // Si le fichier est en cache, on le sert immédiatement
            if (cachedResponse) return cachedResponse;

            // Sinon, on va le chercher sur le réseau et on le met en cache
            return fetch(event.request).then(networkResponse => {
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }

                const responseToCache = networkResponse.clone();
                caches.open(CACHE_DYNAMIC).then(cache => {
                    cache.put(event.request, responseToCache);
                });
                return networkResponse;
            });
        }).catch(() => {
            // FAILSAFE : Si l'utilisateur est offline et demande une page non cachée
            if (event.request.mode === 'navigate') {
                return caches.match('./offline.html');
            }
        })
    );
});

// ================================================================
// SYNCHRONISATION EN ARRIÈRE-PLAN
// ================================================================
self.addEventListener('sync', event => {
    if (event.tag === 'sync-alerts') {
        console.log('[SW] Récupération forcée des alertes Copernicus...');
        event.waitUntil(updateAlertsOffline());
    }
});

async function updateAlertsOffline() {
    // Cette fonction peut être étendue pour synchroniser des données 
    // dès que le téléphone capte à nouveau du réseau.
    console.log('[SW] Système prêt pour la mise à jour des données de zone.');
}

// ================================================================
// GESTION DES NOTIFICATIONS PUSH
// ================================================================
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : { title: "Alerte Météo", body: "Vérifiez vos paramètres de zone." };
    
    const options = {
        body: data.body,
        icon: './assets/icons/icon-192x192.png',
        badge: './assets/icons/badge-72x72.png',
        vibrate: [200, 100, 200],
        data: { url: './history.html' }
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});
