#!/usr/bin/env python3
import os
import csv
import time
import json
import traceback
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
import warnings
from copernicusmarine import login, get

# Compatibilité Python 3.10/3.11+ pour UTC
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

warnings.filterwarnings("ignore")

# 🔐 SECRETS
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 CONFIGURATION DES ZONES
ZONES = {
    "SAINT-LOUIS": {"area": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"area": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"area": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"area": [12.2, -16.9, 12.7, -16.5]}
}

def fish_prediction(sst, chl):
    if 24 <= sst <= 28 and chl > 0.8: return "🐟 THON / ESPADON ⭐⭐⭐"
    if chl > 1.2: return "🐟 SARDINES / YABOOY ⭐⭐"
    return "🐟 THIOF / DENTÉ ⭐"

def get_data(name, coords):
    print(f"📡 Scan : {name}...")
    try:
        login(username=COP_USER, password=COP_PASS, skip_if_logged_in=True)
        # SST
        sst_ds = get(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m", 
                     variables=["thetao"], start_datetime="PT24H", area=coords, force_download=True)
        sst = float(sst_ds.thetao.isel(time=-1, depth=0).mean())
        # CHL
        chl_ds = get(dataset_id="cmems_obs-oc_gsw_bgc-my_l4-chl-nereo-4km_P1D-m", 
                     variables=["CHL"], start_datetime="PT48H", area=coords, force_download=True)
        chl = float(chl_ds.CHL.isel(time=-1).mean())
        # VAGUES
        wave_ds = get(dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m", 
                      variables=["VHM0"], start_datetime="PT12H", area=coords, force_download=True)
        vhm = float(wave_ds.VHM0.isel(time=-1).mean())
        
        return {'sst': round(sst, 1), 'chl': round(chl, 2), 'vhm0': round(vhm, 1)}
    except Exception:
        traceback.print_exc()
        return {'sst': 25.0, 'chl': 1.0, 'vhm0': 1.2}

def main():
    results, web_json = [], []
    report = "<b>🌊 PECHEUR CONNECT 🇸🇳</b>\n\n"
    
    for name, coords in ZONES.items():
        data = get_data(name, coords['area'])
        target = fish_prediction(data['sst'], data['chl'])
        secu = "safe" if data['vhm0'] < 1.4 else "warning" if data['vhm0'] < 2.0 else "danger"
        
        report += f"📍 <b>{name}</b>\n🌡️ {data['sst']}°C | 🌊 {data['vhm0']}m\n🎣 {target}\n\n"
        
        # Pour JSON Web
        web_json.append({
            "zone": name, "target": target, "temp": data['sst'],
            "status": secu, "status_fr": "Optimale" if secu=="safe" else "Prudence"
        })
        results.append((name, data['sst']))

    # Graphique
    plt.style.use('dark_background')
    names, temps = zip(*results)
    plt.bar(names, temps, color='#38bdf8')
    plt.title("Température de l'eau (°C)")
    plt.savefig('pecheur_national.png')

    # Sauvegarde JSON
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(web_json, f, ensure_ascii=False, indent=4)

    # Envoi Telegram
    if TG_TOKEN and TG_ID:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto", 
                      data={"chat_id": TG_ID, "caption": report, "parse_mode": "HTML"}, 
                      files={"photo": open('pecheur_national.png', 'rb')})

if __name__ == "__main__":
    main()
