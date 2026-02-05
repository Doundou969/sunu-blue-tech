<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    const map = L.map('map').setView([14.45, -17.2], 7);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap | PecheurConnect'
    }).addTo(map);

    fetch('./data.json?v=' + Date.now())
        .then(response => response.json())
        .then(data => {
            data.forEach(item => {
                // PROTECTION : On donne des valeurs par défaut si une clé manque
                const vagues   = item.v_now || "0";
                const temp     = item.t_now || "0";
                const courant  = item.c_now || "0";
                const indexP   = item.index || "MOYEN";
                const securite = item.safety || "SÛR"; // Évite l'erreur .includes()
                const zoneName = item.zone   || "Zone inconnue";

                // On vérifie si c'est dangereux sans risquer de plantage
                const isDanger = securite.toString().includes("DANGER");
                const color = isDanger ? "#e74c3c" : "#2ecc71";

                const popupContent = `
                    <div style="min-width:200px; font-family: sans-serif;">
                        <h3 style="text-align:center; margin:0 0 10px 0;">${zoneName}</h3>
                        <div style="background:#f8f9fa; border-left:4px solid #3498db; padding:8px; margin:5px 0;">
                            🌊 <b>MER :</b> ${vagues}m | 🧭 <b>Courant :</b> ${courant}m/s
                        </div>
                        <div style="background:#f8f9fa; border-left:4px solid #27ae60; padding:8px; margin:5px 0;">
                            🐟 <b>PÊCHE :</b> ${indexP}<br>
                            🌡️ <b>Temp :</b> ${temp}°C
                        </div>
                        <div style="background:${color}; color:white; text-align:center; padding:5px; border-radius:4px; font-weight:bold; margin-top:8px;">
                            ${securite}
                        </div>
                    </div>`;

                L.marker([item.lat, item.lon], {
                    icon: L.divIcon({
                        className: 'custom-icon',
                        html: `<div style="background:${color}; color:white; padding:3px 6px; border-radius:4px; font-weight:bold; font-size:11px; white-space:nowrap; border:1px solid rgba(0,0,0,0.2);">${vagues}m | ${temp}°C</div>`,
                        iconSize: [95, 25]
                    })
                })
                .addTo(map)
                .bindPopup(popupContent);
            });
        })
        .catch(err => {
            console.error("Erreur de lecture détaillée :", err);
        });
</script>
