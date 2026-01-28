const CACHE_NAME = 'pecheurconnect-v2';
const URLS_TO_CACHE = [
  '/sunu-blue-tech/',
  '/sunu-blue-tech/index.html',
  '/sunu-blue-tech/data.json',
  '/sunu-blue-tech/icon-192.png',
  '/sunu-blue-tech/icon-512.png',
  '/sunu-blue-tech/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

// INSTALL
self.addEventListener('install', event => {
  console.log('[SW] Installé');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(URLS_TO_CACHE))
      .then(() => self.skipWaiting())
  );
});

// ACTIVATE
self.addEventListener('activate', event => {
  console.log('[SW] Activé');
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== CACHE_NAME)
            .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// FETCH
self.addEventListener('fetch', event => {
  if (event.request.url.includes('data.json')) {
    // Stratégie "network first" pour data.json (toujours à jour)
    event.respondWith(
      fetch(event.request)
        .then(response => {
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, response.clone());
            return response;
          });
        })
        .catch(() => caches.match(event.request)) // fallback si offline
    );
  } else {
    // Stratégie "cache first" pour les assets
    event.respondWith(
      caches.match(event.request)
        .then(response => response || fetch(event.request))
    );
  }
});

// OPTIONNEL : nettoyage périodique des caches anciens
