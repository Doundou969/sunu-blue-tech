/**
 * PecheurConnect v3.0 - Service Worker
 * Mode offline, cache stratégies, sync background
 */

const CACHE_VERSION = 'pecheurconnect-v3.0.0';
const CACHE_STATIC = CACHE_VERSION + '-static';
const CACHE_DYNAMIC = CACHE_VERSION + '-dynamic';
const CACHE_DATA = CACHE_VERSION + '-data';

// Fichiers à mettre en cache lors de l'installation
const STATIC_ASSETS = [
  './',
  './index.html',
  './history.html',
  './comparator.html',
  './export.html',
  './alerts-settings.html',
  './admin.html',
  './offline.html',
  './manifest.json',
  './translations.js',
  './alerts.js',
  './predictions.js',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css',
  'https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css',
  'https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.0',
  'https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap'
];

// Fichiers de données à mettre en cache
const DATA_ASSETS = [
  './data.json'
];

// ================================================================
// INSTALLATION
// ================================================================
self.addEventListener('install', event => {
  console.log('[SW] Installation en cours...');
  
  event.waitUntil(
    Promise.all([
      // Cache statique
      caches.open(CACHE_STATIC).then(cache => {
        console.log('[SW] Mise en cache des assets statiques');
        return cache.addAll(STATIC_ASSETS.map(url => new Request(url, { cache: 'reload' })));
      }),
      
      // Cache données
      caches.open(CACHE_DATA).then(cache => {
        console.log('[SW] Mise en cache des données');
        return cache.addAll(DATA_ASSETS.map(url => new Request(url, { cache: 'reload' })));
      })
    ])
    .then(() => {
      console.log('[SW] Installation terminée');
      return self.skipWaiting(); // Activation immédiate
    })
    .catch(err => {
      console.error('[SW] Erreur installation:', err);
    })
  );
});

// ================================================================
// ACTIVATION
// ================================================================
self.addEventListener('activate', event => {
  console.log('[SW] Activation en cours...');
  
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          // Supprimer anciens caches
          if (key !== CACHE_STATIC && key !== CACHE_DYNAMIC && key !== CACHE_DATA) {
            console.log('[SW] Suppression ancien cache:', key);
            return caches.delete(key);
          }
        })
      );
    })
    .then(() => {
      console.log('[SW] Activation terminée');
      return self.clients.claim(); // Prendre contrôle immédiat
    })
  );
});

// ================================================================
// FETCH - STRATÉGIES DE CACHE
// ================================================================
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Ignorer requêtes non-GET
  if (request.method !== 'GET') return;
  
  // Ignorer requêtes browser-sync, chrome extensions, etc.
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
  if (url.hostname === 'localhost' && url.port === '3001') return;
  
  // ============================================================
  // STRATÉGIE 1 : Cache First pour assets statiques
  // ============================================================
  if (
    request.url.includes('leaflet') ||
    request.url.includes('chart.js') ||
    request.url.includes('fonts.googleapis') ||
    request.url.includes('cdn.jsdelivr') ||
    request.url.includes('.css') ||
    request.url.includes('.woff') ||
    request.url.includes('.woff2') ||
    request.url.endsWith('.js') && !request.url.includes('data.json')
  ) {
    event.respondWith(cacheFirst(request, CACHE_STATIC));
    return;
  }
  
  // ============================================================
  // STRATÉGIE 2 : Network First pour données (avec fallback cache)
  // ============================================================
  if (
    request.url.includes('data.json') ||
    request.url.includes('/logs/') ||
    request.url.includes('/api/')
  ) {
    event.respondWith(networkFirst(request, CACHE_DATA));
    return;
  }
  
  // ============================================================
  // STRATÉGIE 3 : Network First pour pages HTML
  // ============================================================
  if (
    request.url.endsWith('.html') ||
    request.url.endsWith('/') ||
    request.destination === 'document'
  ) {
    event.respondWith(networkFirst(request, CACHE_STATIC));
    return;
  }
  
  // ============================================================
  // STRATÉGIE 4 : Network First par défaut avec fallback offline
  // ============================================================
  event.respondWith(
    fetch(request)
      .then(response => {
        // Mettre en cache dynamique si succès
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_DYNAMIC).then(cache => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Fallback cache ou page offline
        return caches.match(request).then(cached => {
          return cached || caches.match('./offline.html');
        });
      })
  );
});

// ================================================================
// STRATÉGIE : Cache First
// ================================================================
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  
  if (cached) {
    // Retourner cache et mettre à jour en arrière-plan
    updateCache(request, cacheName);
    return cached;
  }
  
  // Si pas en cache, récupérer du réseau
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.error('[SW] Erreur fetch:', error);
    throw error;
  }
}

// ================================================================
// STRATÉGIE : Network First
// ================================================================
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    
    if (response && response.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    
    const cached = await caches.match(request);
    if (cached) return cached;
    
    // Si page HTML, retourner page offline
    if (request.destination === 'document') {
      return caches.match('./offline.html');
    }
    
    throw error;
  }
}

// ================================================================
// MISE À JOUR CACHE EN ARRIÈRE-PLAN
// ================================================================
async function updateCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, response);
    }
  } catch (error) {
    // Échec silencieux - on garde le cache
  }
}

// ================================================================
// MESSAGES DU CLIENT
// ================================================================
self.addEventListener('message', event => {
  console.log('[SW] Message reçu:', event.data);
  
  if (event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
  
  if (event.data.action === 'clearCache') {
    event.waitUntil(
      caches.keys().then(keys => {
        return Promise.all(keys.map(key => caches.delete(key)));
      })
      .then(() => {
        event.ports[0].postMessage({ success: true });
      })
    );
  }
  
  if (event.data.action === 'cacheSize') {
    event.waitUntil(
      caches.keys().then(async keys => {
        let totalSize = 0;
        
        for (const key of keys) {
          const cache = await caches.open(key);
          const requests = await cache.keys();
          
          for (const request of requests) {
            const response = await cache.match(request);
            const blob = await response.blob();
            totalSize += blob.size;
          }
        }
        
        event.ports[0].postMessage({ 
          size: totalSize,
          sizeFormatted: formatBytes(totalSize)
        });
      })
    );
  }
});

// ================================================================
// BACKGROUND SYNC (optionnel)
// ================================================================
self.addEventListener('sync', event => {
  console.log('[SW] Background Sync:', event.tag);
  
  if (event.tag === 'sync-data') {
    event.waitUntil(syncData());
  }
});

async function syncData() {
  try {
    const response = await fetch('./data.json');
    if (response.ok) {
      const cache = await caches.open(CACHE_DATA);
      cache.put('./data.json', response);
      console.log('[SW] Données synchronisées');
    }
  } catch (error) {
    console.error('[SW] Erreur sync:', error);
  }
}

// ================================================================
// PUSH NOTIFICATIONS (optionnel)
// ================================================================
self.addEventListener('push', event => {
  console.log('[SW] Push notification reçue');
  
  let data = { title: 'PecheurConnect', body: 'Nouvelle alerte' };
  
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: 'https://cdn-icons-png.flaticon.com/128/2965/2965315.png',
    badge: 'https://cdn-icons-png.flaticon.com/72/2965/2965315.png',
    vibrate: [200, 100, 200],
    data: data,
    actions: [
      { action: 'view', title: 'Voir' },
      { action: 'close', title: 'Fermer' }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('./')
    );
  }
});

// ================================================================
// HELPERS
// ================================================================
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

console.log('[SW] Service Worker chargé - Version', CACHE_VERSION);
