/* PecheurConnect Service Worker
   Offline-safe • GitHub Pages compatible
*/

const CACHE_NAME = "pecheurconnect-v1";

// Fichiers essentiels à garder hors ligne
const ASSETS = [
  "./",
  "./index.html",
  "./about.html",
  "./services.html",
  "./data.json",
  "./manifest.json"
];

// Installation : mise en cache
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// Activation : nettoyage des anciens caches
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      )
    )
  );
  self.clients.claim();
});

// Fetch : cache first, network fallback
self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return (
        response ||
        fetch(event.request)
          .then(networkResponse => {
            // Mise à jour silencieuse du cache
            if (event.request.url.startsWith(self.location.origin)) {
              const clone = networkResponse.clone();
              caches.open(CACHE_NAME).then(cache =>
                cache.put(event.request, clone)
              );
            }
            return networkResponse;
          })
          .catch(() => {
            // Si offline total
            if (event.request.destination === "document") {
              return caches.match("./index.html");
