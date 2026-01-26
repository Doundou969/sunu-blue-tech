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
    requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})

results = []
print(f"🚀 Lancement du Radar - {datetime.now()}")

# ID de l'Analyse Physique Globale (Contient thetao/température)
# On force le chargement du dataset physique
DATASET_ID = "cmems_mod_glo_phy_anfc_0.083deg_static"

for name, b in ZONES.items():
    try:
        print(f"📡 Analyse Thermique : {name}...")
        
        # On utilise open_dataset en spécifiant bien la variable attendue
        ds = cm.open_dataset(
            dataset_id=DATASET_ID,
            variables=["thetao"], # On demande explicitement la température
            minimum_longitude=b[1],
            maximum_longitude=b[3],
            minimum_latitude=b[0],
            maximum_latitude=b[2],
            username=USER,
            password=PASS
        )
        
        # Sélection de la couche de surface (depth=0)
        temp_data = ds['thetao']
        if 'depth' in temp_data.coords:
            temp_data = temp_data.isel(depth=0)
            
        raw_temp = float(temp_data.mean())
        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)
        
        lat_c = (b[0] + b[2]) / 2
        lon_c = (b[1] + b[3]) / 2
        is_fish = sst <= 21.8

        results.append({
            "zone": name, "temp": sst, "lat": lat_c, "lon": lon_c,
            "is_fish_zone": is_fish, "alert": "🟢"
        })

        if is_fish:
            msg = f"🐟 <b>POISSON DÉTECTÉ à {name} !</b>\n🌡️ Temp: {sst}°C\n📍 GPS: {lat_c:.3f}, {lon_c:.3f}\n\nAppli: https://doundou969.github.io/sunu-blue-tech/"
            send_telegram(msg)
            print(f"✅ Alerte Telegram envoyée pour {name}")

    except Exception as e:
        print(f"❌ Erreur sur {name}: {e}")

with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print(f"🏁 Terminé : {len(results)} zones enregistrées.")
