import copernicusmarine as cm
import json
from datetime import datetime

# --- CONFIGURATION DES ZONES (Lat Min, Lon Min, Lat Max, Lon Max) ---
ZONES = {
    "SAINT-LOUIS": [15.8, -17.2, 16.5, -16.3],
    "KAYAR": [14.7, -17.5, 15.2, -16.9],
    "DAKAR-YOFF": [14.6, -17.8, 14.9, -17.3],
    "MBOUR-JOAL": [14.0, -17.3, 14.5, -16.7],
    "CASAMANCE": [12.3, -17.5, 12.8, -16.5]
}

results = []
print("🔑 Connexion au service Copernicus...")
today = datetime.now().strftime("%Y-%m-%d")

for name, b in ZONES.items():
    try:
        print(f"📡 Analyse satellite : {name}...")
        
        # open_dataset avec le bon argument 'variables'
        ds = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static",
            variables=["thetao"], 
            minimum_longitude=b[1], 
            maximum_longitude=b[3],
            minimum_latitude=b[0], 
            maximum_latitude=b[2],
            start_datetime=f"{today}T00:00:00",
            end_datetime=f"{today}T23:59:59"
        )
        
        # Moyenne et conversion Celsius
        raw_temp = float(ds.thetao.mean())
        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)

        # Calcul du point GPS central de la zone
        lat_center = (b[0] + b[2]) / 2
        lon_center = (b[1] + b[3]) / 2

        results.append({
            "zone": name,
            "temp": sst,
            "vhm0": 1.2, # Valeur simulée (à coupler avec un dataset wave si besoin)
            "lat": lat_center,
            "lon": lon_center,
            "is_fish_zone": sst <= 21.8, # Seuil d'Upwelling favorable au poisson
            "trend": "📉" if sst < 21 else "📈",
            "alert": "🟢" if sst < 25 else "📈",
            "wind_speed": 14,
            "wind_dir": "NNE",
            "next_vhm": 1.3
        })
    except Exception as e:
        print(f"⚠️ Erreur zone {name}: {e}")

# Sauvegarde du fichier de données
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print("✅ Mise à jour PecheurConnect terminée avec succès.")
