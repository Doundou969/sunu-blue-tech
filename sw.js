const CACHE_NAME = 'pecheurconnect-v2';
self.addEventListener('install', e => {
  console.log('SW installé');
  self.skipWaiting();
});

self.addEventListener('fetch', e => {
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
