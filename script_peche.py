import copernicusmarine as cm
import json
import os
import requests
from datetime import datetime

# Secrets GitHub
USER = os.getenv('COPERNICUS_USERNAME')
PASS = os.getenv('COPERNICUS_PASSWORD')
TEL_TOKEN = os.getenv('TELEGRAM_TOKEN')
TEL_ID = os.getenv('TELEGRAM_CHAT_ID')

# Zones Sénégal
ZONES = {
    "SAINT-LOUIS": [15.8, -17.2, 16.5, -16.3],
    "KAYAR": [14.7, -17.5, 15.2, -16.9],
    "DAKAR-YOFF": [14.6, -17.8, 14.9, -17.3],
    "MBOUR-JOAL": [14.0, -17.3, 14.5, -16.7],
    "CASAMANCE": [12.3, -17.5, 12.8, -16.5]
}

def send_telegram(message):
    if not TEL_TOKEN or not TEL_ID: return
    url = f"https://api.telegram.org/bot{TEL_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})
    except: pass

results = []
print(f"🚀 Démarrage PecheurConnect - {datetime.now()}")

# ID CORRECT : Analyse Physique Globale (Mise à jour quotidienne)
DATASET_ID = "cmems_mod_glo_phy_anfc_0.083deg_static"

for name, b in ZONES.items():
    try:
        print(f"📡 Analyse Satellite : {name}...")
        
        # On force la sélection des coordonnées avant de charger les variables
        ds = cm.open_dataset(
            dataset_id=DATASET_ID,
            username=USER,
            password=PASS
        )
        
        # On découpe la zone et on cherche spécifiquement la Température Potentielle
        # On essaie d'abord 'thetao' (3D) puis 'tos' (2D Surface)
        subset = ds.sel(longitude=slice(b[1], b[3]), latitude=slice(b[0], b[2]))
        
        if 'thetao' in subset.variables:
            # On prend la surface (profondeur la plus proche de 0)
            temp_val = subset['thetao'].isel(depth=0).mean().values
        elif 'tos' in subset.variables:
            temp_val = subset['tos'].mean().values
        else:
            raise ValueError(f"Variables disponibles: {list(subset.variables)}")

        raw_temp = float(temp_val)
        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)
        
        lat_c = (b[0] + b[2]) / 2
        lon_c = (b[1] + b[3]) / 2
        is_fish = sst <= 21.8

        results.append({
            "zone": name, "temp": sst, "lat": lat_c, "lon": lon_c,
            "is_fish_zone": is_fish, "alert": "🟢"
        })

        if is_fish:
            msg = f"🐟 <b>POISSON DÉTECTÉ à {name} !</b>\n🌡️ Temp: {sst}°C\n📍 GPS: {lat_c:.3f}, {lon_c:.3f}"
            send_telegram(msg)

    except Exception as e:
        print(f"❌ Erreur {name}: {e}")

# Sauvegarde pour le site
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print(f"🏁 Terminé : {len(results)} zones enregistrées.")
