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
    if TEL_TOKEN and TEL_ID:
        url = f"https://api.telegram.org/bot{TEL_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})

results = []
print("🔑 Connexion Copernicus...")
today = datetime.now().strftime("%Y-%m-%d")

for name, b in ZONES.items():
    try:
        print(f"📡 Analyse : {name}...")
        # Utilisation de l'ID statique pour éviter les erreurs de variables manquantes
        ds = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static",
            variables=["thetao"],
            minimum_longitude=b[1], maximum_longitude=b[3],
            minimum_latitude=b[0], maximum_latitude=b[2],
            username=USER, password=PASS
        )
        
        raw_temp = float(ds.thetao.mean())
        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)
        
        lat_c = (b[0] + b[2]) / 2
        lon_c = (b[1] + b[3]) / 2
        is_fish = sst <= 21.8

        results.append({
            "zone": name, "temp": sst, "lat": lat_c, "lon": lon_center,
            "is_fish_zone": is_fish, "alert": "🟢"
        })

        if is_fish:
            msg = f"🐟 <b>ZONE DE POISSON DÉTECTÉE !</b>\n📍 Secteur: {name}\n🌡️ Temp: {sst}°C\n⚓ Coordonnées: {lat_c:.3f}, {lon_c:.3f}\n\n<i>Logiciel PecheurConnect 🇸🇳</i>"
            send_telegram(msg)

    except Exception as e:
        print(f"❌ Erreur {name}: {e}")

with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)
