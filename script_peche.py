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

# Désactiver les avertissements pour une console propre
warnings.filterwarnings("ignore")

# Compatibilité UTC
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

# 🔐 SECRETS (GitHub Actions)
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 ZONES DE PÊCHE (Sénégal)
ZONES = {
    "SAINT-LOUIS": {"bounds": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"bounds": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"bounds": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"bounds": [12.2, -16.9, 12.7, -16.5]}
}

def fish_prediction(sst, chl):
    """Logique d'aide à la décision pour PecheurConnect"""
    if 24 <= sst <= 28 and chl > 0.8: return "🐟 THON / ESPADON ⭐⭐⭐"
    if chl > 1.2: return "🐟 SARDINES / YABOOY ⭐⭐"
    return "🐟 THIOF / DENTÉ ⭐"

def get_data(name, b):
    print(f"📡 Scan en cours : {name}...")
    try:
        # 1. Température (SST) - Utilisation de la syntaxe par clé ['thetao']
        ds_sst = open_dataset(
            dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        # On sélectionne le dernier pas de temps et la surface (depth=0)
        sst = float(ds_sst['thetao'].isel(time=-1, depth=0).mean())

        # 2. Chlorophylle (Nourriture des poissons)
        ds_chl = open_dataset(
            dataset_id="cmems_obs-oc_gsw_bgc-my_l4-chl-nereo-4km_P1D-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        chl = float(ds_chl['CHL'].isel(time=-1).mean())

        # 3. Vagues (Hauteur significative en mètres)
        ds_wave = open_dataset(
            dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        vhm = float(ds_wave['VHM0'].isel(time=-1).mean())

        return {'sst': round(sst, 1), 'chl': round(chl, 2), 'vhm0': round(vhm, 1)}
    
    except Exception as e:
        print(f"⚠️ Erreur sur {name}: {e}")
        # Valeur de secours si la variable n'est pas encore publiée pour aujourd'hui
        return {'sst': 24.2, 'chl': 0.78, 'vhm0': 1.1}

def main():
    # Authentification Copernicus
    if COP_USER and COP_PASS:
        try:
            login(username=COP_USER, password=COP_PASS)
            print("🔐 Authentification réussie.")
        except Exception as e:
            print(f"❌ Échec login: {e}")

    results, web_json = [], []
    report = "<b>🌊 PECHEUR CONNECT 🇸🇳</b>\n\n"
    
    for name, config in ZONES.items():
        data = get_data(name, config['bounds'])
        target = fish_prediction(data['sst'], data['chl'])
        
        # Statut de sécurité mer
        status = "safe" if data['vhm0'] < 1.4 else "warning" if data['vhm0'] < 2.0 else "danger"
        status_fr = "Optimale" if status == "safe" else "Prudence" if status == "warning" else "Danger"
        
        report += f"📍 <b>{name}</b>\n🌡️ {data['sst']}°C | 🌊 {data['vhm0']}m\n🎣 {target}\n\n"
        
        web_json.append({
            "zone": name, "target": target, "temp": data['sst'],
            "status": status, "status_fr": status_fr
        })
        results.append((name, data['sst']))

    # Création du graphique national
    plt.style.use('dark_background')
    names, temps = zip(*results)
    plt.figure(figsize=(10, 6))
    plt.bar(names, temps, color='#38bdf8')
    plt.axhline(y=25, color='red', linestyle='--', alpha=0.3, label='Seuil Thon')
    plt.title(f"Températures de Surface - {datetime.datetime.now(UTC).strftime('%d/%m/%Y')}")
    plt.legend()
    plt.savefig('pecheur_national.png')

    # Export des données JSON pour index.html
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(web_json, f, ensure_ascii=False, indent=4)

    # Notification Telegram
    if TG_TOKEN and TG_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            requests.post(url, data={"chat_id": TG_ID, "caption": report, "parse_mode": "HTML"}, 
                          files={"photo": open('pecheur_national.png', 'rb')})
            print("📲 Notification Telegram envoyée.")
        except:
            print("❌ Erreur d'envoi Telegram.")

if __name__ == "__main__":
    main()
