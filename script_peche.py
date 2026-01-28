"""
PecheurConnect 🇸🇳
Script Copernicus Marine – SST (Sea Surface Temperature)

- Télécharge les données SST Copernicus
- Calcule la moyenne locale par zone de pêche
- Génère data.json pour GitHub Pages
"""

import json
from datetime import datetime, timedelta
from statistics import mean

from copernicusmarine import subset
import numpy as np

# =========================
# ZONES DE PÊCHE (SÉNÉGAL)
# =========================
ZONES = [
    {"name": "SAINT-LOUIS", "lat": 16.04, "lon": -16.49},
    {"name": "KAYAR", "lat": 14.92, "lon": -17.12},
    {"name": "DAKAR-YOFF", "lat": 14.74, "lon": -17.49},
    {"name": "MBOUR-JOAL", "lat": 14.15, "lon": -16.83},
    {"name": "CASAMANCE", "lat": 12.56, "lon": -16.27},
]

# =========================
# PARAMÈTRES COPERNICUS
# =========================
DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
VARIABLE = "thetao"  # Sea Surface Temperature
BOX = 0.25           # Rayon spatial (°)
DAYS_BACK = 1        # Données J-1 (stables)

# =========================
# DATE
# =========================
end_date = datetime.utcnow().date()
start_date = end_date - timedelta(days=DAYS_BACK)

stations = []

# =========================
# EXTRACTION DES DONNÉES
# =========================
for zone in ZONES:
    name = zone["name"]
    lat = zone["lat"]
    lon = zone["lon"]

    print(f"📡 Traitement {name}")

    try:
        ds = subset(
            dataset_id=DATASET_ID,
            variables=[VARIABLE],
            minimum_latitude=lat - BOX,
            maximum_latitude=lat + BOX,
            minimum_longitude=lon - BOX,
            maximum_longitude=lon + BOX,
            start_datetime=f"{start_date}T00:00:00",
            end_datetime=f"{end_date}T00:00:00"
        )

        values = ds[VARIABLE].values.flatten()
        values = values[~np.isnan(values)]

        if len(values) == 0:
            raise ValueError("Pas de données valides")

        sst = round(mean(values), 1)

    except Exception as e:
        print(f"⚠️ Erreur {name} : {e}")
        sst = None

    # =========================
    # RÈGLES MÉTIER SIMPLES
    # =========================
    # (houle & vent seront branchés plus tard à Copernicus Waves / Wind)
    wave = round(0.4 + (abs(lat) % 1.2), 1)
    wind = round(7 + (abs(lon) % 10))

    stations.append({
        "name": name,
        "lat": lat,
        "lon": lon,
        "temperature": sst,
        "wave": wave,
        "wind": wind
    })

# =========================
# EXPORT data.json
# =========================
output = {
    "updated_at": datetime.utcnow().isoformat() + "Z",
    "source": "Copernicus Marine Service",
    "stations": stations
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("✅ data.json généré avec succès")
