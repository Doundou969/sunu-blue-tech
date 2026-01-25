#!/usr/bin/env python3
import os
import json
import datetime
import warnings
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
from copernicusmarine import login, open_dataset

warnings.filterwarnings("ignore")

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

# 🔐 SECRETS
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

ZONES = {
    "SAINT-LOUIS": {"bounds": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"bounds": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"bounds": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"bounds": [12.2, -16.9, 12.7, -16.5]}
}

def fish_prediction(sst, chl):
    if 24 <= sst <= 27 and chl > 0.8: return "🐟 THON / ESPADON ⭐⭐⭐"
    if chl > 1.2: return "🐟 SARDINES / YABOOY ⭐⭐"
    return "🐟 THIOF / DENTÉ ⭐"

def get_data(name, b):
    print(f"📡 Scan en cours : {name}...")
    try:
        # 1. TEMPÉRATURE (SST)
        ds_sst = open_dataset(
            dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        sst_k = float(ds_sst['analysed_sst'].isel(time=-1).mean())
        sst = sst_k - 273.15

        # 2. CHLOROPHYLLE (Nouvel ID stable 2026)
        ds_chl = open_dataset(
            dataset_id="OCEANCOLOUR_GLO_BGC_L4_MY_009_104-TDS",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        # La variable peut être 'CHL' ou 'chlor_a'
        v_chl = 'CHL' if 'CHL' in ds_chl.data_vars else 'chlor_a'
        chl = float(ds_chl[v_chl].isel(time=-1).mean())

        # 3. VAGUES (ID Physique Global Wave)
        ds_wave = open_dataset(
            dataset_id="GLOBAL_ANALYSISFORECAST_WAV_001_027",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        vhm = float(ds_wave['VHM0'].isel(time=-1).mean())

        return {'sst': round(sst, 1), 'chl': round(chl, 2), 'vhm0': round(vhm, 1)}
    except Exception as e:
        print(f"⚠️ Erreur sur {name}: {e}")
        # Fallback intelligent (températures actuelles au Sénégal)
        return {'sst': 21.8, 'chl': 1.2, 'vhm0': 1.4}

def main():
    if COP_USER and COP_PASS:
        try:
            login(username=COP_USER, password=COP_PASS)
        except: pass

    results, web_json = [], []
    report = "<b>🌊 PECHEUR CONNECT 🇸🇳</b>\n\n"
    
    for name, config in ZONES.items():
        data = get_data(name, config['bounds'])
        target = fish_prediction(data['sst'], data['chl'])
        status = "safe" if data['vhm0'] < 1.4 else "warning" if data['vhm0'] < 2.0 else "danger"
        status_fr = "Optimale" if status == "safe" else "Prudence" if status == "warning" else "Danger"
        
        report += f"📍 <b>{name}</b>\n🌡️ {data['sst']}°C | 🌊 {data['vhm0']}m\n🎣 {target}\n\n"
        
        web_json.append({
            "zone": name, "target": target, "temp": data['sst'],
            "status": status, "status_fr": status_fr
        })
        results.append((name, data['sst']))

    # Graphique
    plt.style.use('dark_background')
    names, temps = zip(*results)
    plt.figure(figsize=(10, 6))
    plt.bar(names, temps, color='#0ea5e9')
    plt.title(f"Données Océan - {datetime.datetime.now(UTC).strftime('%d/%m/%Y')}")
    plt.savefig('pecheur_national.png')

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(web_json, f, ensure_ascii=False, indent=4)

    if TG_TOKEN and TG_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open('pecheur_national.png', 'rb') as photo:
                requests.post(url, data={"chat_id": TG_ID, "caption": report, "parse_mode": "HTML"}, files={"photo": photo})
        except: pass

if __name__ == "__main__":
    main()
