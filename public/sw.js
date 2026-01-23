self.addEventListener("install",e=>e.waitUntil(caches.open("sunu-v1").then(c=>c.addAll(["/","/index.html","/public/data.json"]))))
