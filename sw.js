const CACHE_NAME = "pecheurconnect-v1";
const urlsToCache = [
  "/sunu-blue-tech/index.html",
  "/sunu-blue-tech/data.json",
  "/sunu-blue-tech/manifest.json",
  "/sunu-blue-tech/icon-192.png",
  "/sunu-blue-tech/icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)));
});

self.addEventListener("fetch", event => {
  event.respondWith(caches.match(event.request).then(resp => resp || fetch(event.request)));
});
