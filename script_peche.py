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

# 📍 ZONES SÉNÉGAL
ZONES = {
    "SAINT-LOUIS": {"bounds": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"bounds": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"bounds": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"bounds": [12.2, -16.9, 12.7, -16.5]}
}

def get_data(name, b):
    print(f"📡 Scan en cours : {name}...")
    try:
        # 1. PHYSIQUE (Utilisation de l'ID de produit stable v2026)
        ds = open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
            minimum_latitude=b[0],
            maximum_latitude=b[2],
            minimum_longitude=b[1],
            maximum_longitude=b[3],
            variables=["thetao"]
        )
        
        # Extraction de la température (SST)
        # On s'assure de prendre le dernier index temporel disponible
        sst_val = ds["thetao"].isel(time=-1, depth=0).mean().values
        sst = float(sst_val)

        # 2. VAGUES (ID de produit simplifié)
        ds_w = open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-m",
            minimum_latitude=b[0],
            maximum_latitude=b[2],
            minimum_longitude=b[1],
            maximum_longitude=b[3],
            variables=["VHM0"]
        )
        vhm_val = ds_w["VHM0"].isel(time=-1).mean().values
        vhm = float(vhm_val)

        return {'sst': round(sst, 1), 'vhm0': round(vhm, 1)}
    
    except Exception as e:
        print(f"❌ Erreur réelle sur {name}: {e}")
        # On change les valeurs de secours pour vérifier si ça bouge
        return {'sst': 22.2, 'vhm0': 1.3}

def fish_prediction(sst):
    if sst < 21.5: return "🐟 THIOF / SARDINELLE (FROID) ⭐⭐⭐"
    if 24 <= sst <= 27: return "🐟 THON / ESPADON (CHAUD) ⭐⭐⭐"
    return "🐟 DENTÉ / POISSONS DE ROCHE ⭐"

def main():
    if COP_USER and COP_PASS:
        try:
            login(username=COP_USER, password=COP_PASS)
            print("🔐 Connexion Copernicus établie.")
        except: print("⚠️ Problème de credentials.")

    results, web_json = [], []
    report = "<b>🌊 PECHEUR CONNECT 🇸🇳</b>\n\n"
    
    for name, config in ZONES.items():
        data = get_data(name, config['bounds'])
        target = fish_prediction(data['sst'])
        status = "safe" if data['vhm0'] < 1.4 else "warning" if data['vhm0'] < 2.0 else "danger"
        
        report += f"📍 <b>{name}</b>\n🌡️ {data['sst']}°C | 🌊 {data['vhm0']}m\n🎣 {target}\n\n"
        
        web_json.append({
            "zone": name, "target": target, "temp": data['sst'],
            "status": status, "status_fr": "Optimale" if status == "safe" else "Prudence"
        })
        results.append((name, data['sst']))

    # Graphique
    plt.style.use('dark_background')
    names, temps = zip(*results)
    plt.figure(figsize=(10, 6))
    plt.bar(names, temps, color='#38bdf8')
    plt.title(f"PECHEUR CONNECT - {datetime.datetime.now(UTC).strftime('%d/%m/%Y')}")
    plt.ylabel("Température (°C)")
    plt.savefig('pecheur_national.png')

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(web_json, f, ensure_ascii=False, indent=4)

    if TG_TOKEN and TG_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open('pecheur_national.png', 'rb') as photo:
                requests.post(url, data={"chat_id": TG_ID, "caption": report, "parse_mode": "HTML"}, files={"photo": photo})
            print("📲 Notification Telegram envoyée !")
        except: pass

if __name__ == "__main__":
    main()
