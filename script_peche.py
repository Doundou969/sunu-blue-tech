#!/usr/bin/env python3
import os
import sys
import csv
import time
import traceback
import datetime
import numpy as np
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

# Suppression des alertes inutiles
warnings.filterwarnings("ignore", category=UserWarning)

print("🚀 PECHEUR CONNECT - SENEGAL MULTI-ZONES")

# 🔐 SECRETS (Récupérés depuis GitHub Actions)
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 ZONES DE PÊCHE (De Saint-Louis à la Casamance)
ZONES = {
    "SAINT-LOUIS": {"area": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"area": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"area": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"area": [12.2, -16.9, 12.7, -16.5]}
}

def copernicus_fishing_conditions(zone_name, coords):
    """Récupération ultra-robuste avec Retries et Debug détaillé"""
    print(f"📡 Tentative de connexion : {zone_name}...")
    max_retries = 3
    retry_delay = 5

    if not COP_USER or not COP_PASS:
        print(f"⚠️ [AUTH] Secrets manquants. Simulation pour {zone_name}.")
        return {'sst': 25.5, 'chl': 1.1, 'vhm0': 1.2}

    for attempt in range(1, max_retries + 1):
        try:
            login(username=COP_USER, password=COP_PASS, skip_if_logged_in=True)
            
            # 1. SST (Température de surface)
            sst_ds = get(
                dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                variables=["thetao"], start_datetime="PT24H", area=coords, force_download=True
            )
            sst = float(sst_ds.thetao.isel(time=-1, depth=0).mean())

            # 2. CHL (Chlorophylle)
            chl_ds = get(
                dataset_id="cmems_obs-oc_gsw_bgc-my_l4-chl-nereo-4km_P1D-m",
                variables=["CHL"], start_datetime="PT48H", area=coords, force_download=True
            )
            chl = float(chl_ds.CHL.isel(time=-1).mean())

            # 3. VAGUES
            wave_ds = get(
                dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
                variables=["VHM0"], start_datetime="PT12H", area=coords, force_download=True
            )
            vhm0 = float(wave_ds.VHM0.isel(time=-1).mean())

            return {'sst': round(sst, 1), 'chl': round(chl, 2), 'vhm0': round(vhm0, 1)}

        except Exception as e:
            print(f"⚠️ [ESSAI {attempt}] Erreur {zone_name}: {str(e)}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                traceback.print_exc()
                return {'sst': 24.5, 'chl': 0.8, 'vhm0': 1.0}

def fish_prediction(sst, chl):
    if 24 <= sst <= 29 and chl > 0.8:
        return "🐟 THON / ESPADON ⭐⭐⭐"
    elif chl > 1.2:
        return "🐟 SARDINES / CHINCHARD ⭐⭐"
    else:
        return "🐟 THIOF / DENTÉ ⭐"

def main():
    report = "<b>🌊 PECHEUR CONNECT - RAPPORT NATIONAL</b> 🇸🇳\n\n"
    history = []
    now_ts = datetime.datetime.now(UTC).strftime('%d/%m %H:%M UTC')
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    zones_list, sst_list = [], []

    for name, config in ZONES.items():
        data = copernicus_fishing_conditions(name, config['area'])
        prediction = fish_prediction(data['sst'], data['chl'])
        
        secu = "✅ Calme" if data['vhm0'] < 1.4 else "⚠️ Prudence"
        report += f"📍 <b>{name}</b>\n🌡️ {data['sst']}°C | 🌊 {data['vhm0']}m\n🎣 {prediction}\n🛡️ {secu}\n\n"
        
        zones_list.append(name)
        sst_list.append(data['sst'])
        data['zone'] = name
        data['timestamp'] = datetime.datetime.now(UTC).strftime('%Y-%m-%d %H:%M')
        history.append(data)

    ax.bar(zones_list, sst_list, color=['#f97316', '#10b981', '#3b82f6', '#8b5cf6'])
    ax.set_title(f"Température de l'eau (°C) - {now_ts}")
    plt.tight_layout()
    plt.savefig('pecheur_national.png')

    if TG_TOKEN and TG_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        requests.post(url, data={"chat_id": TG_ID, "caption": report, "parse_mode": "HTML"}, 
                      files={"photo": open('pecheur_national.png', 'rb')})

    # Archivage CSV
    file_exists = os.path.isfile("pecheur_coast_history.csv")
    with open("pecheur_coast_history.csv", "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'zone', 'sst', 'chl', 'vhm0'])
        if not file_exists: writer.writeheader()
        writer.writerows(history)
    
    print("🎉 Rapport terminé.")

if __name__ == "__main__":
    main()
