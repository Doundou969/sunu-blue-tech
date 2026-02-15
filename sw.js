const CACHE_NAME = 'pecheurconnect-v1.0.3';
const DATA_CACHE_NAME = 'pecheurconnect-data-v1';

// Fichiers à mettre en cache pour fonctionnement hors ligne
const FILES_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './offline.html',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'https://cdn-icons-png.flaticon.com/512/2965/2965315.png'
];

// Installation du Service Worker
self.addEventListener('install', (evt) => {
  console.log('[ServiceWorker] Install');
  
  evt.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[ServiceWorker] Pre-caching offline page');
      return cache.addAll(FILES_TO_CACHE);
    })
  );
  
  self.skipWaiting();
});

// Activation du Service Worker
self.addEventListener('activate', (evt) => {
  console.log('[ServiceWorker] Activate');
  
  evt.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        if (key !== CACHE_NAME && key !== DATA_CACHE_NAME) {
          console.log('[ServiceWorker] Removing old cache', key);
          return caches.delete(key);
        }
      }));
    })
  );
  
  self.clients.claim();
});

// Stratégie de récupération des données
self.addEventListener('fetch', (evt) => {
  
  // Stratégie Network First pour data.json (toujours fresh)
  if (evt.request.url.includes('data.json')) {
    evt.respondWith(
      caches.open(DATA_CACHE_NAME).then((cache) => {
        return fetch(evt.request)
          .then((response) => {
            // Mettre à jour le cache avec les nouvelles données
            cache.put(evt.request.url, response.clone());
            return response;
          })
          .catch(() => {
            // Si pas de réseau, utiliser le cache
            return cache.match(evt.request);
          });
      })
    );
    return;
  }
  
  // Stratégie Cache First pour les autres ressources
  evt.respondWith(
    caches.match(evt.request).then((response) => {
      return response || fetch(evt.request).catch(() => {
        // Si offline et pas dans le cache, montrer la page offline
        if (evt.request.mode === 'navigate') {
          return caches.match('./offline.html');
        }
      });
    })
  );
});

// Gestion des messages depuis l'app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Notification push (pour futures alertes)
self.addEventListener('push', (event) => {
  const data = event.data.json();
  
  const options = {
    body: data.body,
    icon: 'https://cdn-icons-png.flaticon.com/512/2965/2965315.png',
    badge: 'https://cdn-icons-png.flaticon.com/128/2965/2965315.png',
    vibrate: [200, 100, 200],
    tag: 'pecheurconnect-alert',
    requireInteraction: true,
    actions: [
      {
        action: 'view',
        title: 'Voir la carte'
      },
      {
        action: 'close',
        title: 'Fermer'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'PecheurConnect', options)
  );
});

// Gestion des clics sur les notifications
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});
