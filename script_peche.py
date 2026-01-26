import copernicusmarine as cm
import json
import os
import requests
from datetime import datetime

# Configuration Telegram & Copernicus
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
    if not TEL_TOKEN or not TEL_ID:
        print("⚠️ Telegram non configuré dans les Secrets.")
        return
    url = f"https://api.telegram.org/bot{TEL_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})
        print(f"📡 Statut Telegram: {r.status_code}")
    except Exception as e:
        print(f"❌ Erreur envoi Telegram: {e}")

results = []
print(f"🚀 Démarrage PecheurConnect - {datetime.now()}")

for name, b in ZONES.items():
    try:
        print(f"📡 Tentative sur {name}...")
        # On utilise le dataset 'tos' (Sea Surface Temp) qui est plus léger et stable
        ds = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static",
            username=USER,
            password=PASS
        ).sel(longitude=slice(b[1], b[3]), latitude=slice(b[0], b[2]))
        
        # On cherche la température (soit thetao, soit tos)
        temp_var = ds['thetao'] if 'thetao' in ds.variables else ds['tos']
        raw_temp = float(temp_var.mean())
        
        # Conversion Kelvin -> Celsius
        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)
        
        lat_c = (b[0] + b[2]) / 2
        lon_c = (b[1] + b[3]) / 2
        is_fish = sst <= 21.8

        results.append({
            "zone": name, "temp": sst, "lat": lat_c, "lon": lon_c,
            "is_fish_zone": is_fish, "alert": "🟢"
        })

        if is_fish:
            print(f"🐟 Poisson trouvé à {name}!")
            msg = f"🐟 <b>ZONE DE POISSON !</b>\n📍 Secteur: {name}\n🌡️ Temp: {sst}°C\n⚓ GPS: {lat_c:.3f}, {lon_c:.3f}"
            send_telegram(msg)

    except Exception as e:
        print(f"❌ Erreur zone {name}: {e}")

# Sauvegarde forcée du fichier
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)
print(f"✅ data.json mis à jour avec {len(results)} zones.")
