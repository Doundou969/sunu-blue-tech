<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <title>PêcheurConnect 🇸🇳</title>
  <meta name="description" content="Radar satellite Copernicus pour pêcheurs artisanaux sénégalais">

  <!-- PWA -->
  <link rel="manifest" href="./manifest.json">
  <meta name="theme-color" content="#0ea5e9">

  <!-- Icons -->
  <link rel="icon" href="./icon-192.png">

  <!-- Tailwind (OK pour MVP) -->
  <script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-sky-50 text-gray-800">

  <header class="bg-sky-600 text-white p-4 text-center">
    <h1 class="text-2xl font-bold">🌊 PÊCHEURCONNECT</h1>
    <p class="text-sm">Ta sécurité. Ta réussite.</p>
  </header>

  <main class="p-4 space-y-4">

    <div class="bg-white rounded-xl shadow p-4">
      <h2 class="font-semibold text-lg">📡 Radar Poisson</h2>
      <p id="score" class="text-3xl font-bold text-sky-600">--</p>
      <p class="text-sm text-gray-500">Indice satellite Copernicus</p>
    </div>

    <div class="bg-white rounded-xl shadow p-4">
      <h2 class="font-semibold text-lg">🧭 Position GPS</h2>
      <p id="gps">En attente...</p>
    </div>

  </main>

  <footer class="text-center text-xs text-gray-500 p-2">
    © PêcheurConnect Sénégal
  </footer>

<script>
/* =========================
   DATA.JSON
========================= */
fetch('./data.json')
  .then(r => r.json())
  .then(data => {
    document.getElementById("score").textContent = data.score_peche;
  })
  .catch(() => {
    document.getElementById("score").textContent = "N/A";
  });

/* =========================
   GPS
========================= */
if ("geolocation" in navigator) {
  navigator.geolocation.getCurrentPosition(pos => {
    document.getElementById("gps").textContent =
      pos.coords.latitude.toFixed(4) + ", " + pos.coords.longitude.toFixed(4);
  });
}

/* =========================
   SERVICE WORKER
========================= */
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js')
    .then(() => console.log("✅ Service Worker OK"))
    .catch(err => console.error("❌ SW erreur", err));
}
</script>

</body>
</html>
