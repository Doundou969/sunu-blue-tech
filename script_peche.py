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
    if TEL_TOKEN and TEL_ID:
        url = f"https://api.telegram.org/bot{TEL_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})

results = []
print("🌊 Connexion au catalogue Copernicus...")

try:
    # On ouvre le dataset global physique (SST)
    # L'ID 'cmems_mod_glo_phy_anfc_0.083deg_static' est parfois capricieux, 
    # on utilise le moteur par défaut sans forcer d'options inutiles.
    ds = cm.open_dataset(
        dataset_id="cmems_mod_glo_phy_anfc_0.083deg_static",
        username=USER,
        password=PASS
    )

    print(f"✅ Dataset ouvert. Variables trouvées : {list(ds.variables)}")

    for name, b in ZONES.items():
        try:
            # Extraction propre
            subset = ds.sel(longitude=slice(b[1], b[3]), latitude=slice(b[0], b[2]))
            
            # DETERMINATION DE LA VARIABLE (sécurité totale)
            # On cherche 'thetao' (température eau) ou 'tos' (température surface)
            var_name = None
            if 'thetao' in subset.variables: var_name = 'thetao'
            elif 'tos' in subset.variables: var_name = 'tos'
            elif 'deptho' in subset.variables: var_name = 'deptho' # Bathymétrie en dernier recours

            if not var_name:
                print(f"⚠️ Aucune donnée exploitable pour {name}")
                continue

            # Calcul de la valeur
            data_slice = subset[var_name]
            if 'depth' in data_slice.coords:
                data_slice = data_slice.isel(depth=0)
            
            val = float(data_slice.mean())
            
            # Si c'est de la température (Kelvin -> Celsius)
            if var_name in ['thetao', 'tos']:
                final_val = round(val - 273.15, 1) if val > 100 else round(val, 1)
                unit = "°C"
            else:
                final_val = round(val, 1)
                unit = "m (fond)"

            lat_c, lon_c = (b[0]+b[2])/2, (b[1]+b[3])/2
            is_fish = (unit == "°C" and final_val <= 21.8)

            results.append({
                "zone": name, "temp": final_val, "lat": lat_c, "lon": lon_c,
                "is_fish_zone": is_fish, "alert": "🟢"
            })

            if is_fish:
                send_telegram(f"🐟 <b>POISSON DÉTECTÉ !</b>\n📍 {name}\n🌡️ {final_val}°C\n⚓ {lat_c:.3f}, {lon_c:.3f}")
                print(f"📩 Alerte envoyée pour {name}")

        except Exception as zone_err:
            print(f"❌ Erreur sur la zone {name}: {zone_err}")

except Exception as global_err:
    print(f"💥 Erreur critique de connexion : {global_err}")

# Sauvegarde du JSON
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)

print(f"🏁 Terminé. {len(results)} zones traitées.")
