import copernicusmarine as cm
import pandas as pd
import json
import datetime

# --- CONFIGURATION ---
ZONES = {
    "SAINT-LOUIS": [15.8, -17.2, 16.5, -16.3],
    "KAYAR": [14.7, -17.5, 15.2, -16.9],
    "DAKAR-YOFF": [14.6, -17.8, 14.9, -17.3],
    "MBOUR-JOAL": [14.0, -17.3, 14.5, -16.7],
    "CASAMANCE": [12.3, -17.5, 12.8, -16.5]
}

def get_trend(current, zone_name):
    # Logique simplifiée pour l'exemple (à coupler avec tes anciennes données)
    return "📉" if current < 21 else "📈"

results = []
print("🔑 Connexion Copernicus...")

for name, b in ZONES.items():
    print(f"📡 Analyse de la zone : {name}...")
    
    # 1. Récupération Température (SST)
    ds_temp = cm.open_dataset(
        dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static",
        variable=["thetao"],
        minimum_longitude=b[1], maximum_longitude=b[3],
        minimum_latitude=b[0], maximum_latitude=b[2],
        start_datetime=datetime.datetime.now().strftime("%Y-%m-%d"),
        end_datetime=datetime.datetime.now().strftime("%Y-%m-%d")
    )
    
    # Extraction et conversion Kelvin -> Celsius
    raw_temp = float(ds_temp.thetao.mean())
    sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)

    # 2. Récupération Houle (VHM0)
    # (Ici on simule la récupération vhm0 pour l'exemple de structure)
    vhm0 = 1.2 
    
    # CALCUL DES COORDONNÉES DU "POINT POISSON"
    # On cible le centre de la zone d'étude
    lat_fish = (b[0] + b[2]) / 2
    lon_fish = (b[1] + b[3]) / 2

    results.append({
        "zone": name,
        "temp": sst,
        "vhm0": vhm0,
        "lat": lat_fish,
        "lon": lon_fish,
        "is_fish_zone": sst <= 21.5, # Seuil d'Upwelling riche
        "trend": get_trend(sst, name),
        "alert": "🔴" if vhm0 > 2.2 else "🟢",
        "wind_speed": 15,
        "wind_dir": "NNE",
        "next_vhm": 1.4
    })

# Sauvegarde
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print("✅ Données mises à jour avec coordonnées de pêche.")
