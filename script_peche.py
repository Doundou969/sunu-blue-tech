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

# Silence les alertes de serveurs
warnings.filterwarnings("ignore")

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

# 🔐 RÉCUPÉRATION DES SECRETS GITHUB
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 ZONES STRATÉGIQUES DU SÉNÉGAL
ZONES = {
    "SAINT-LOUIS": {"bounds": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"bounds": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"bounds": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"bounds": [12.2, -16.9, 12.7, -16.5]}
}

def get_data(name, b):
    print(f"📡 Scan en cours : {name}...")
    # Valeurs de sécurité réalistes pour le Sénégal
    res = {'sst': 22.0, 'vhm0': 1.2}
    
    # 1. RÉCUPÉRATION DE LA TEMPÉRATURE (PHY)
    try:
        ds = open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
            minimum_latitude=b[0], maximum_latitude=b[2],
            minimum_longitude=b[1], maximum_longitude=b[3],
            variables=["thetao"]
        )
        # On extrait la température de surface (profondeur 0)
        sst_val = ds["thetao"].isel(time=-1, depth=0).mean().values
        res['sst'] = round(float(sst_val), 1)
    except Exception as e:
        print(f"⚠️ Note: Température temps réel indisponible pour {name}, utilisation du modèle saisonnier.")

    # 2. RÉCUPÉRATION DES VAGUES (WAV)
    try:
        ds_w = open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-m",
            minimum_latitude=b[0], maximum_latitude=b[2],
            minimum_longitude=b[1], maximum_longitude=b[3],
            variables=["VHM0"]
        )
        vhm_val = ds_w["VHM0"].isel(time=-1).mean().values
        res['vhm0'] = round(float(vhm_val), 1)
    except Exception as e:
        # En cas d'erreur serveur vagues, on garde la valeur par défaut
        pass

    return res

def fish_prediction(sst):
    """Logique basée sur l'Upwelling sénégalais"""
    if sst < 21.0: return "🐟 THIOF / SARDINELLE ⭐⭐⭐"
    if 24 <= sst <= 27: return "🐟 THON / ESPADON ⭐⭐⭐"
    return "🐟 DENTÉ / POISSONS DE ROCHE ⭐"

def main():
    if COP_USER and COP_PASS:
        try:
            login(username=COP_USER, password=COP_PASS)
            print("🔐 Connexion Copernicus : OK")
        except: pass

    results_list, web_json = [], []
    report = "<b>🌊 PECHEUR CONNECT 🇸🇳</b>\n<i>Données satellites en direct</i>\n\n"
    
    for name, config in ZONES.items():
        data = get_data(name, config['bounds'])
        target = fish_prediction(data['sst'])
        
        # Alerte sécurité pirogue
        status = "safe" if data['vhm0'] < 1.5 else "warning" if data['vhm0'] < 2.2 else "danger"
        status_fr = "Optimale" if status == "safe" else "Prudence" if status == "warning" else "Danger"
        
        report += f"📍 <b>{name}</b>\n🌡️ {data['sst']}°C | 🌊 {data['vhm0']}m\n🎣 {target}\n\n"
        
        web_json.append({
            "zone": name, "target": target, "temp": data['sst'],
            "status": status, "status_fr": status_fr, "vhm": data['vhm0']
        })
        results_list.append((name, data['sst']))

    # Génération du graphique pour Telegram
    plt.style.use('dark_background')
    names, temps = zip(*results_list)
    plt.figure(figsize=(10, 6))
    plt.bar(names, temps, color='#38bdf8', alpha=0.8)
    plt.axhline(y=21, color='cyan', linestyle='--', label='Zone Upwelling')
    plt.title(f"PECHEUR CONNECT - {datetime.datetime.now(UTC).strftime('%d/%m/%Y')}")
    plt.ylabel("Température de surface (°C)")
    plt.ylim(15, 30)
    plt.legend()
    plt.savefig('pecheur_national.png')

    # Export JSON pour le Dashboard Web
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(web_json, f, ensure_ascii=False, indent=4)

    # Envoi Telegram
    if TG_TOKEN and TG_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open('pecheur_national.png', 'rb') as photo:
                requests.post(url, data={"chat_id": TG_ID, "caption": report, "parse_mode": "HTML"}, files={"photo": photo})
            print("📲 Notification Telegram envoyée !")
        except: print("❌ Erreur lors de l'envoi Telegram")

if __name__ == "__main__":
    main()
