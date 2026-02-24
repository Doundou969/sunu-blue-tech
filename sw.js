/**
 * PecheurConnect v3.0 - Service Worker FINAL CORRIGÉ
 * Gestion Offline, Audio Wolof & Data Copernicus
 * Corrections : listener message manquant, gestion erreurs fetch améliorée
 */

const CACHE_VERSION = 'pecheurconnect-v3.0.3';
const CACHE_STATIC  = `${CACHE_VERSION}-static`;
const CACHE_DYNAMIC = `${CACHE_VERSION}-dynamic`;
const CACHE_DATA    = `${CACHE_VERSION}-data`;

const STATIC_ASSETS = [
    './',
    './index.html',
    './history.html',
    './comparator.html',
    './alerts-settings.html',
    './offline.html',
    './manifest.json',
    './icon-192.png',
    './icon-512.png'
];

// ================================================================
// INSTALLATION : Mise en cache des assets statiques
// ================================================================
self.addEventListener('install', event => {
    console.log('[SW] Installation de PecheurConnect v3.0...');
    event.waitUntil(
        caches.open(CACHE_STATIC)
            .then(cache => {
                console.log('[SW] Mise en cache des assets statiques...');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
            .catch(err => console.warn('[SW] Erreur pré-cache (non bloquant) :', err))
    );
});

// ================================================================
// ACTIVATION : Nettoyage et Prise de contrôle
// ================================================================
self.addEventListener('activate', event => {
    console.log('[SW] Activation de PecheurConnect v3.0...');
    event.waitUntil(
        Promise.all([
            // Supprime les anciens caches
            caches.keys().then(keys =>
                Promise.all(
                    keys.map(key => {
                        if (![CACHE_STATIC, CACHE_DYNAMIC, CACHE_DATA].includes(key)) {
                            console.log('[SW] Suppression du cache obsolète :', key);
                            return caches.delete(key);
                        }
                    })
                )
            ),
            // Prend le contrôle immédiatement
            self.clients.claim()
        ])
    );
});

// ================================================================
// STRATÉGIE DE FETCH (Le cœur du mode Offline)
// ================================================================
self.addEventListener('fetch', event => {
    // Ignorer les requêtes non-GET et les extensions Chrome
    if (event.request.method !== 'GET') return;
    if (event.request.url.startsWith('chrome-extension://')) return;

    const url = new URL(event.request.url);

    // 1. STRATÉGIE "NETWORK FIRST" : Données Météo & Copernicus
    // On veut les données les plus fraîches possibles. Si pas de réseau, on prend le cache.
    if (url.pathname.endsWith('.json') || url.href.includes('copernicus')) {
        event.respondWith(networkFirstStrategy(event.request));
        return;
    }

    // 2. STRATÉGIE "CACHE FIRST" : Assets, Scripts et Audio Wolof
    // Vital pour économiser la batterie et le forfait, et pour l'audio au large.
    event.respondWith(cacheFirstStrategy(event.request));
});

/**
 * Network First : tente le réseau, repli sur le cache
 * Utilisé pour les données JSON / Copernicus
 */
async function networkFirstStrategy(request) {
    // URL propre sans query string pour le cache (evite les mismatches avec ?v=timestamp)
    const urlClean = new URL(request.url);
    urlClean.search = '';
    const cacheKey = urlClean.toString();

    try {
        const networkResponse = await fetch(request);

        // Ne cacher que les reponses valides — stocker SANS le ?v=timestamp
        if (networkResponse && networkResponse.ok) {
            const cache = await caches.open(CACHE_DATA);
            cache.put(cacheKey, networkResponse.clone());
        }
        return networkResponse;

    } catch (err) {
        console.warn('[SW] Reseau indisponible, lecture du cache pour :', cacheKey);

        // Chercher avec l'URL propre (sans ?v=...) puis fallback
        const cached = await caches.match(cacheKey)
            || await caches.match(request);

        if (cached) {
            console.log('[SW] Donnees servies depuis le cache :', cacheKey);
            return cached;
        }

        // Reponse JSON vide valide pour ne pas bloquer l'app
        return new Response(
            JSON.stringify({ error: 'offline', message: 'Donnees non disponibles hors ligne' }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

/**
 * Cache First : sert depuis le cache, puis réseau en fallback
 * Utilisé pour les assets statiques, audio Wolof, scripts
 */
async function cacheFirstStrategy(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) return cachedResponse;

        const networkResponse = await fetch(request);

        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const cache = await caches.open(CACHE_DYNAMIC);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;

    } catch (err) {
        console.warn('[SW] Ressource non disponible :', request.url);

        // Fallback vers la page offline pour les navigations
        if (request.mode === 'navigate') {
            const offlinePage = await caches.match('./offline.html');
            if (offlinePage) return offlinePage;
        }

        // Réponse vide pour les autres ressources (évite les erreurs console)
        return new Response('', { status: 408, statusText: 'Hors ligne' });
    }
}

// ================================================================
// GESTION DES MESSAGES (depuis les pages clientes)
// CORRECTION : Ce listener manquant était la cause de l'erreur !
// "message channel closed before a response was received"
// ================================================================
self.addEventListener('message', event => {
    console.log('[SW] Message reçu :', event.data);

    // Garder le SW en vie pendant le traitement async
    event.waitUntil(
        handleMessage(event)
    );
});

async function handleMessage(event) {
    const { data, ports } = event;

    // Fonction utilitaire pour répondre (si MessageChannel est utilisé)
    const reply = (payload) => {
        if (ports && ports[0]) {
            ports[0].postMessage(payload);
        }
    };

    try {
        switch (data?.type) {

            case 'SKIP_WAITING':
                await self.skipWaiting();
                reply({ success: true, action: 'SKIP_WAITING' });
                break;

            case 'GET_VERSION':
                reply({ success: true, version: CACHE_VERSION });
                break;

            case 'GET_CACHE_STATUS':
                const keys = await caches.keys();
                const sizes = await Promise.all(
                    keys.map(async key => {
                        const cache = await caches.open(key);
                        const requests = await cache.keys();
                        return { name: key, count: requests.length };
                    })
                );
                reply({ success: true, caches: sizes });
                break;

            case 'CLEAR_CACHE':
                const allKeys = await caches.keys();
                await Promise.all(allKeys.map(key => caches.delete(key)));
                reply({ success: true, action: 'CLEAR_CACHE' });
                break;

            case 'PREFETCH_ZONE':
                // Pré-charger les données d'une zone spécifique
                if (data.zone) {
                    try {
                        const res = await fetch(`./logs/stats/${data.zone}.json`);
                        if (res.ok) {
                            const cache = await caches.open(CACHE_DATA);
                            await cache.put(`./logs/stats/${data.zone}.json`, res);
                            reply({ success: true, zone: data.zone });
                        } else {
                            reply({ success: false, error: 'Zone introuvable' });
                        }
                    } catch (e) {
                        reply({ success: false, error: e.message });
                    }
                } else {
                    reply({ success: false, error: 'Zone non spécifiée' });
                }
                break;

            default:
                console.warn('[SW] Type de message inconnu :', data?.type);
                reply({ success: false, error: `Type inconnu : ${data?.type}` });
        }

    } catch (err) {
        console.error('[SW] Erreur traitement message :', err);
        reply({ success: false, error: err.message });
    }
}

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
    try {
        console.log('[SW] Mise à jour des données de zone...');
        // Rafraîchir le fichier principal des stats
        const response = await fetch('./logs/stats/all_zones.json');
        if (response.ok) {
            const cache = await caches.open(CACHE_DATA);
            await cache.put('./logs/stats/all_zones.json', response);
            console.log('[SW] Données de zone mises à jour avec succès.');

            // Notifier les clients que les données sont fraîches
            const clients = await self.clients.matchAll();
            clients.forEach(client => {
                client.postMessage({ type: 'DATA_UPDATED', timestamp: new Date().toISOString() });
            });
        }
    } catch (err) {
        console.warn('[SW] Sync échouée (sera retentée) :', err.message);
    }
}

// ================================================================
// GESTION DES NOTIFICATIONS PUSH
// ================================================================
self.addEventListener('push', event => {
    const data = event.data
        ? event.data.json()
        : { title: 'Alerte Météo', body: 'Vérifiez vos paramètres de zone.' };

    const options = {
        body:    data.body,
        icon:    './assets/icons/icon-192x192.png',
        badge:  './assets/icons/badge-72x72.png',
        vibrate: [200, 100, 200],
        data:    { url: './history.html' }
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// ================================================================
// CLIC SUR NOTIFICATION
// ================================================================
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const targetUrl = event.notification.data?.url || './index.html';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                // Si une fenêtre est déjà ouverte, on la focus
                for (const client of clientList) {
                    if (client.url.includes(targetUrl) && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Sinon on ouvre une nouvelle fenêtre
                if (self.clients.openWindow) {
                    return self.clients.openWindow(targetUrl);
                }
            })
    );
});
