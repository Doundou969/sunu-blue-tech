import copernicusmarine as cm
import json
import os
from datetime import datetime

# Authentification via les secrets GitHub
USER = os.getenv('COPERNICUS_USERNAME')
PASS = os.getenv('COPERNICUS_PASSWORD')

# Zones de surveillance Sénégal
ZONES = {
    "SAINT-LOUIS": [15.8, -17.2, 16.5, -16.3],
    "KAYAR": [14.7, -17.5, 15.2, -16.9],
    "DAKAR-YOFF": [14.6, -17.8, 14.9, -17.3],
    "MBOUR-JOAL": [14.0, -17.3, 14.5, -16.7],
    "CASAMANCE": [12.3, -17.5, 12.8, -16.5]
}

results = []
print("🔑 Connexion sécurisée à Copernicus...")
# Format de date pour le dataset physique
today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
today_end = datetime.now().strftime("%Y-%m-%d 23:59:59")

for name, b in ZONES.items():
    try:
        print(f"📡 Analyse de la zone : {name}...")
        
        # Changement d'ID vers GLOBAL_ANALYSISFORECAST_PHY_001_024 (Température)
        ds = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static", 
            variables=["thetao"], 
            minimum_longitude=b[1], 
            maximum_longitude=b[3],
            minimum_latitude=b[0], 
            maximum_latitude=b[2],
            start_datetime=today_start,
            end_datetime=today_end,
            username=USER,
            password=PASS
        )
        
        # On vérifie si thetao est présent, sinon on essaie 'tos' (Sea Surface Temp)
        temp_var = ds['thetao'] if 'thetao' in ds.variables else ds['tos']
        
        # Calcul Température (Moyenne sur la zone et la profondeur de surface)
        # On sélectionne la première couche de profondeur si thetao est 4D
        if 'depth' in temp_var.coords:
            raw_temp = float(temp_var.isel(depth=0).mean())
        else:
            raw_temp = float(temp_var.mean())

        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)

        lat_center = (b[0] + b[2]) / 2
        lon_center = (b[1] + b[3]) / 2

        results.append({
            "zone": name,
            "temp": sst,
            "vhm0": 1.2, 
            "lat": lat_center,
            "lon": lon_center,
            "is_fish_zone": sst <= 21.8, # Seuil d'Upwelling
            "trend": "📉" if sst < 21 else "📈",
            "alert": "🟢" if sst < 24 else "🟡",
            "wind_speed": 14,
            "wind_dir": "NNE",
            "next_vhm": 1.3
        })
    except Exception as e:
        print(f"⚠️ Erreur sur {name}: {e}")

# Sauvegarde pour le site web
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print(f"✅ Analyse terminée. {len(results)} zones traitées.")
