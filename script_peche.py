import json
import os
import requests
import xarray as xr
from datetime import datetime

TEL_TOKEN = os.getenv('TELEGRAM_TOKEN')
TEL_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if not TEL_TOKEN or not TEL_ID: return
    url = f"https://api.telegram.org/bot{TEL_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TEL_ID, "text": message, "parse_mode": "HTML"})

results = []
if not os.path.exists("data.nc"):
    print("❌ Fichier data.nc introuvable.")
    exit(1)

try:
    ds = xr.open_dataset("data.nc")
    ZONES = {
        "SAINT-LOUIS": [15.8, -17.2, 16.5, -16.3],
        "KAYAR": [14.7, -17.5, 15.2, -16.9],
        "DAKAR-YOFF": [14.6, -17.8, 14.9, -17.3],
        "MBOUR-JOAL": [14.0, -17.3, 14.5, -16.7],
        "CASAMANCE": [12.3, -17.5, 12.8, -16.5]
    }

    for name, b in ZONES.items():
        subset = ds.sel(longitude=slice(b[1], b[3]), latitude=slice(b[0], b[2]))
        temp_var = "thetao" if "thetao" in ds.variables else "tos"
        
        data_slice = subset[temp_var]
        if 'depth' in data_slice.coords: data_slice = data_slice.isel(depth=0)
            
        raw_temp = float(data_slice.mean())
        sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)
        
        lat_c, lon_c = (b[0]+b[2])/2, (b[1]+b[3])/2
        is_fish = sst <= 21.8

        results.append({"zone": name, "temp": sst, "lat": lat_c, "lon": lon_c, "is_fish_zone": is_fish, "alert": "🟢"})
        if is_fish:
            send_telegram(f"🐟 <b>ZONE DE POISSON !</b>\n📍 {name}\n🌡️ {sst}°C\n⚓ {lat_c:.3f}, {lon_c:.3f}")

except Exception as e:
    print(f"❌ Erreur : {e}")

with open('data.json', 'w') as f:
    json.dump(results, f, indent=4)
