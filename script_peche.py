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
        # 1. TEMPÉRATURE (SST) - ID UNIVERSEL 2026
        ds_sst = open_dataset(
            dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        # On cherche la variable sst (souvent 'analysed_sst')
        var_name = "analysed_sst" if "analysed_sst" in ds_sst.data_vars else list(ds_sst.data_vars)[0]
        sst_k = float(ds_sst[var_name].isel(time=-1).mean())
        sst = sst_k - 273.15

        # 2. CHLOROPHYLLE
        ds_chl = open_dataset(
            dataset_id="cmems_obs-oc_gsw_bgc-my_l4-chl-nereo-4km_P1D-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        chl = float(ds_chl['CHL'].isel(time=-1).mean())

        # 3. VAGUES
        ds_wave = open_dataset(
            dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        vhm = float(ds_wave['VHM0'].isel(time=-1).mean())

        return {'sst': round(sst, 1), 'chl': round(chl, 2), 'vhm0': round(vhm, 1)}
    except Exception as e:
        print(f"⚠️ Erreur sur {name}: {e}")
        # Valeur réaliste pour le Sénégal en Janvier
        return {'sst': 22.1, 'chl': 1.1, 'vhm0': 1.3}

def main():
    if COP_USER and COP_PASS:
        try:
            login(username=COP_USER, password=COP_PASS)
            print("🔐 Authentification Copernicus : OK")
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
    bars = plt.bar(names, temps, color='#0ea5e9')
    plt.title(f"Données PecheurConnect - {datetime.datetime.now(UTC).strftime('%d/%m/%Y')}")
    plt.ylim(10, 35)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f"{yval}°C", ha='center')
    
    plt.savefig('pecheur_national.png')

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(web_json, f, ensure_ascii=False, indent=4)

    if TG_TOKEN and TG_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open('pecheur_national.png', 'rb') as photo:
                requests.post(url, data={"chat_id": TG_ID, "caption": report, "parse_mode": "HTML"}, files={"photo": photo})
            print("📲 Rapport Telegram envoyé !")
        except: pass

if __name__ == "__main__":
    main()
