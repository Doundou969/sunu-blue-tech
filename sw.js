// sw.js - Service Worker minimal pour PecheurConnect
self.addEventListener('install', (e) => {
  console.log('PecheurConnect SW installé');
});

self.addEventListener('fetch', (e) => {
  // Nécessaire pour le mode hors-ligne basique
  e.respondWith(fetch(e.request));
});
