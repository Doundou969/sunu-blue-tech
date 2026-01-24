const CACHE_NAME = 'sunu-blue-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/public/data.json',
  '/public/manifest.json'
];

// Installation : Mise en cache des fichiers de base
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// Stratégie : "Network First" (Réseau d'abord, sinon Cache)
// Idéal pour les données météo qui changent souvent
self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Si le réseau répond, on clone la réponse dans le cache
        return caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, response.clone());
          return response;
        });
      })
      .catch(() => {
        // Si le réseau échoue (plein mer), on cherche dans le cache
        return caches.match(event.request);
      })
  );
});
