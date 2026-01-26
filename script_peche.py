import json
import os
import requests
import xarray as xr
from datetime import datetime

TEL_TOKEN = os.getenv('TELEGRAM_TOKEN')
TEL_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if not TEL_TOKEN or not TEL_ID: 
        print("⚠️ Telegram non configuré")
        return
    url = f"https://api.telegram.org/bot{TEL_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})

results = []

if not os.path.exists("data.nc"):
    print("❌ Erreur : Le fichier data.nc n'a pas été téléchargé.")
    exit(1)

try:
    # Lecture du fichier NetCDF
    ds = xr.open_dataset("data.nc")
    
    ZONES = {
        "SAINT-LOUIS": [15.8, -17.2, 16.5, -16.3],
        "KAYAR": [14.7, -17.5, 15.2, -16.9],
        "DAKAR-YOFF": [14.6, -17.8, 14.9, -17.3],
        "MBOUR-JOAL": [14.0, -17.3, 14.5, -16.7],
        "CASAMANCE": [12.3, -17.5, 12.8, -16.5]
    }

    for name, b in ZONES.items():
        # Sélection de la zone géographique
        subset = ds.sel(longitude=slice(b[1], b[3]), latitude=slice(b[0], b[2]))
        
        # Sélection de la variable de température
        temp_var = "thetao" if "thetao" in ds.variables else "tos"
        
        # Calcul de la moyenne sur la zone (et sur la surface si depth existe)
        data_slice = subset[temp_var]
        if 'depth' in data_slice.coords:
            data_slice = data_slice.isel(depth=0)
            
        raw_temp = float(data_slice.mean())
        # Conversion Kelvin vers Celsius si nécessaire
        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)
        
        lat_c = (b[0] + b[2]) / 2
        lon_c = (b[1] + b[3]) / 2
        is_fish = sst <= 21.8

        results.append({
            "zone": name, 
            "temp": sst, 
            "lat": lat_c, 
            "lon": lon_c,
            "is_fish_zone": is_fish, 
            "alert": "🟢"
        })

        if is_fish:
            msg = f"🐟 <b>ZONE DE POISSON DÉTECTÉE !</b>\n📍 Secteur: {name}\n🌡️ Temp: {sst}°C\n⚓ GPS: {lat_c:.3f}, {lon_c:.3f}"
            send_telegram(msg)
            print(f"✅ Alerte envoyée pour {name}")

except Exception as e:
    print(f"❌ Erreur lors du traitement : {e}")

# Sauvegarde du JSON pour le site web
with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)
print(f"🏁 Terminé : {len(results)} zones enregistrées dans data.json.")
