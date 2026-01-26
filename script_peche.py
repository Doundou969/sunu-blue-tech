import copernicusmarine as cm
import json
import os
import requests
from datetime import datetime

# Identifiants
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
        print("⚠️ Telegram non configuré dans les Secrets GitHub.")
        return
    url = f"https://api.telegram.org/bot{TEL_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})
        if r.status_code == 200:
            print("✅ Notification Telegram envoyée !")
        else:
            print(f"❌ Erreur Telegram {r.status_code}: {r.text}")
    except Exception as e:
        print(f"💥 Erreur réseau Telegram: {e}")

results = []
print("🌊 Connexion au Radar Copernicus...")

try:
    # On force l'ouverture du dataset physique
    ds = cm.open_dataset(
        dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static",
        username=USER,
        password=PASS
    )

    for name, b in ZONES.items():
        try:
            subset = ds.sel(longitude=slice(b[1], b[3]), latitude=slice(b[0], b[2]))
            
            # Détection de la meilleure variable
            var_name = 'thetao' if 'thetao' in subset.variables else 'tos'
            
            data_slice = subset[var_name]
            if 'depth' in data_slice.coords:
                data_slice = data_slice.isel(depth=0)
            
            # Calcul et conversion Kelvin vers Celsius
            val_kelvin = float(data_slice.mean())
            if val_kelvin > 100:
                sst = round(val_kelvin - 273.15, 1)
            else:
                sst = round(val_kelvin, 1)

            lat_c, lon_c = (b[0]+b[2])/2, (b[1]+b[3])/2
            
            # CONDITION DE PÊCHE (Upwelling : eau froide = poisson)
            is_fish = sst <= 21.8 

            results.append({
                "zone": name, "temp": sst, "lat": lat_c, "lon": lon_c,
                "is_fish_zone": is_fish, "alert": "🟢" if sst < 25 else "🟡"
            })

            if is_fish:
                msg = f"🐟 <b>ZONE DE POISSON DÉTECTÉE !</b>\n📍 Secteur: {name}\n🌡️ Température: {sst}°C\n⚓ GPS: {lat_c:.2f}, {lon_c:.2f}\n\n🇸🇳 PecheurConnect"
                send_telegram(msg)

        except Exception as e:
            print(f"⚠️ Erreur zone {name}: {e}")

except Exception as e:
    print(f"💥 Erreur globale: {e}")

with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print(f"🏁 Terminé. {len(results)} zones dans data.json.")
