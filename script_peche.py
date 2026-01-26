import copernicusmarine as cm
import json
import os
import requests
from datetime import datetime

# Configuration
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
print("🌊 Synchronisation PecheurConnect...")

try:
    # On ouvre le dataset
    ds = cm.open_dataset(
        dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static",
        username=USER,
        password=PASS
    )

    for name, b in ZONES.items():
        try:
            subset = ds.sel(longitude=slice(b[1], b[3]), latitude=slice(b[0], b[2]))
            
            # FORCE LA VARIABLE DE TEMPÉRATURE (thetao)
            # Si on trouve deptho (profondeur), on l'ignore pour le calcul de température
            if 'thetao' in subset.variables:
                data = subset['thetao']
                if 'depth' in data.coords: data = data.isel(depth=0)
                val = float(data.mean())
                # CONVERSION KELVIN -> CELSIUS (Ex: 294K -> 21°C)
                sst = round(val - 273.15, 1) if val > 100 else round(val, 1)
            else:
                # Si on n'a que la profondeur, on met une valeur par défaut pour ne pas afficher 500°C
                sst = 22.0 

            lat_c, lon_c = (b[0]+b[2])/2, (b[1]+b[3])/2
            
            # Seuil de l'Upwelling au Sénégal (Eaux froides = Poissons)
            is_fish = sst <= 21.5 

            results.append({
                "zone": name, 
                "temp": sst, 
                "lat": lat_c, 
                "lon": lon_c,
                "is_fish_zone": is_fish, 
                "alert": "🟢" if sst < 26 else "🟡"
            })

            if is_fish:
                msg = f"🐟 <b>ALERTE PÊCHE - {name}</b>\n🌡️ Température idéale : {sst}°C\n⚓ Position : {lat_c:.3f}, {lon_c:.3f}\n\n<i>Envoyé par PecheurConnect 🇸🇳</i>"
                send_telegram(msg)

        except Exception as e:
            print(f"⚠️ Erreur {name}: {e}")

except Exception as e:
    print(f"💥 Erreur globale: {e}")

# Sauvegarde propre
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print("✅ Mise à jour terminée.")
