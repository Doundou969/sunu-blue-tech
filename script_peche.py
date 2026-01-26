import copernicusmarine as cm
import json
import os
import requests
from datetime import datetime, timedelta

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
    try:
        requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})
    except: pass

results = []
print(f"🚀 Démarrage PecheurConnect IBI - {datetime.now()}")

# NOUVEL ID : Spécifique zone Atlantique (Pas de conflit Bathy)
DATASET_ID = "cmems_mod_ibi_phy_anfc_0.027deg-3D_static"

for name, b in ZONES.items():
    try:
        print(f"📡 Analyse Thermique IBI : {name}...")
        
        # On utilise une sélection directe par variable pour forcer Copernicus
        ds = cm.open_dataset(
            dataset_id=DATASET_ID,
            variables=["thetao"],
            username=USER,
            password=PASS
        )
        
        # Découpage précis
        subset = ds.sel(
            longitude=slice(b[1], b[3]), 
            latitude=slice(b[0], b[2]),
            depth=0,
            method="nearest"
        )
            
        raw_temp = float(subset['thetao'].mean())
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
            print(f"✅ Telegram envoyé pour {name}")

    except Exception as e:
        print(f"❌ Erreur sur {name}: {e}")

# Sauvegarde forcée
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print(f"🏁 Terminé : {len(results)} zones enregistrées.")
