#!/usr/bin/env python3
import os
import sys
import csv
import datetime
from datetime import UTC
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests

# 🔐 CONFIGURATION
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 DÉFINITION DES ZONES GÉOGRAPHIQUES (Bounding Boxes)
ZONES = {
    "SAINT-LOUIS": {"area": [15.9, -16.6, 16.1, -16.4], "gps": "16.0°N, 16.5°W"},
    "DAKAR / YOFF": {"area": [14.6, -17.6, 14.8, -17.4], "gps": "14.7°N, 17.5°W"},
    "MBOUR / JOAL": {"area": [14.1, -17.0, 14.3, -16.8], "gps": "14.2°N, 16.9°W"},
    "CASAMANCE":   {"area": [12.3, -16.8, 12.6, -16.6], "gps": "12.5°N, 16.7°W"}
}

def get_zone_data(zone_name, coords):
    """Interroge Copernicus pour une zone spécifique"""
    if not COP_USER or not COP_PASS:
        return {'sst': 25.0, 'chl': 1.0, 'vhm0': 1.2} # Simulation si secrets absents
    
    from copernicusmarine import get
    try:
        # SST
        sst_ds = get(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                     variables="thetao", start_datetime="PT24H", area=coords)
        sst = float(sst_ds.thetao.isel(time=-1, depth=0).mean())
        
        # CHLOROPHYLLE
        chl_ds = get(dataset_id="cmems_obs-oc_gsw_bgc-my_l4-chl-nereo-4km_P1D-m",
                     variables="CHL", start_datetime="PT48H", area=coords)
        chl = float(chl_ds.CHL.isel(time=-1).mean())
        
        # VAGUES
        wave_ds = get(dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
                      variables="VHM0", start_datetime="PT12H", area=coords)
        vhm0 = float(wave_ds.VHM0.isel(time=-1).mean())
        
        return {'sst': round(sst, 1), 'chl': round(chl, 2), 'vhm0': round(vhm0, 1)}
    except:
        return None

def main():
    print("🌍 Analyse de la côte Sénégalaise...")
    report_text = "<b>🌊 PECHEUR CONNECT - CÔTE SÉNÉGAL</b> 🇸🇳\n\n"
    history_data = []
    
    # Préparation du graphique
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    zone_labels = []
    sst_vals = []
    vhm_vals = []

    for name, config in ZONES.items():
        print(f"📡 Scan zone: {name}...")
        res = get_zone_data(name, config['area'])
        
        if res:
            # Texte du bulletin
            secu = "✅ Calme" if res['vhm0'] < 1.4 else "⚠️ Prudence"
            report_text += f"📍 <b>{name}</b>\n🌡️ {res['sst']}°C | 🌿 {res['chl']}mg | 🌊 {res['vhm0']}m\n🛡️ {secu}\n\n"
            
            # Données pour le graphique
            zone_labels.append(name)
            sst_vals.append(res['sst'])
            vhm_vals.append(res['vhm0'])
            
            # Pour l'historique CSV
            res['zone'] = name
            res['timestamp'] = datetime.datetime.now(UTC).strftime('%Y-%m-%d %H:%M')
            history_data.append(res)

    # Création du graphique comparatif
    ax1.bar(zone_labels, sst_vals, color='#f97316')
    ax1.set_title("🌡️ Température par Zone (°C)")
    ax2.bar(zone_labels, vhm_vals, color='#1e40af')
    ax2.set_title("🌊 Hauteur des Vagues (m)")
    
    plt.tight_layout()
    plt.savefig('coast_report.png')

    # Envoi Telegram
    report_text += "⛺ <i>Données valables 12h</i>\n@PecheurConnect"
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    with open('coast_report.png', 'rb') as f:
        requests.post(url, data={"chat_id": TG_ID, "caption": report_text, "parse_mode": "HTML"}, files={"photo": f})

    # Archivage CSV
    file_exists = os.path.isfile("pecheur_coast_history.csv")
    with open("pecheur_coast_history.csv", "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'zone', 'sst', 'chl', 'vhm0'])
        if not file_exists: writer.writeheader()
        writer.writerows(history_data)

    print("✅ Rapport multi-zones envoyé !")

if __name__ == "__main__":
    main()
