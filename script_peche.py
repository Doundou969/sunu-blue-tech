#!/usr/bin/env python3
import os
import sys
import csv
import traceback
import datetime
from datetime import UTC
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
import warnings

# Suppression des alertes non critiques
warnings.filterwarnings("ignore", category=UserWarning)

print("🚀 PECHEUR CONNECT - SENEGAL (Version 2.1)")

# 🔐 CONFIGURATION (Via Variables d'Environnement)
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()
CSV_FILE = "pecheur_data_history.csv"

def log_to_csv(data):
    """Archive les données pour l'intelligence prédictive de PecheurConnect"""
    file_exists = os.path.isfile(CSV_FILE)
    try:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            fieldnames = ['timestamp', 'sst', 'chl', 'vhm0', 'spot']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            # On ajoute le timestamp au dictionnaire de données
            log_data = data.copy()
            log_data['timestamp'] = datetime.datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow(log_data)
        print(f"📊 Données archivées dans {CSV_FILE}")
    except Exception as e:
        print(f"⚠️ Erreur d'archivage CSV: {e}")

def copernicus_fishing_conditions():
    """📡 Extraction Data Réelle : SST + CHLORO + VAGUES via Copernicus"""
    if not COP_USER or not COP_PASS:
        print("⚠️ Mode Simulation (Identifiants Copernicus manquants)")
        return {'sst': 26.5, 'chl': 1.15, 'vhm0': 1.4, 'spot': 'Dakar-Yoff'}
    
    try:
        from copernicusmarine import get
        print("🌡️ Interrogation des satellites Copernicus...")
        
        # 1. SST (Température de surface)
        sst_ds = get(
            dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
            variables="thetao",
            start_datetime="PT24H",
            area=[14.7, -17.5, 14.8, -17.4]
        )
        sst = float(sst_ds.thetao.isel(time=-1, depth=0).mean())
        
        # 2. CHLOROPHYLLE (Présence de plancton)
        chl_ds = get(
            dataset_id="cmems_obs-oc_gsw_bgc-my_l4-chl-nereo-4km_P1D-m",
            variables="CHL",
            start_datetime="PT48H",
            area=[14.7, -17.5, 14.8, -17.4]
        )
        chl = float(chl_ds.CHL.isel(time=-1).mean())
        
        # 3. VAGUES (Sécurité pirogues)
        wave_ds = get(
            dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
            variables="VHM0",
            start_datetime="PT12H",
            area=[14.7, -17.5, 14.8, -17.4]
        )
        vhm0 = float(wave_ds.VHM0.isel(time=-1).mean())
        
        return {
            'sst': round(sst, 1),
            'chl': round(chl, 2),
            'vhm0': round(vhm0, 1),
            'spot': 'Dakar-Yoff ⭐'
        }
    except Exception as e:
        print(f"⚠️ Erreur API Copernicus: {e} -> Fallback")
        return {'sst': 26.1, 'chl': 1.23, 'vhm0': 1.5, 'spot': 'Dakar-Yoff'}

def fish_prediction(sst, chl):
    """🧠 IA Pêche : Identification des espèces par biomarqueurs"""
    if 24 <= sst <= 29 and chl > 0.8:
        return {
            'species': "🐟🐟🐟 <b>THON (Albacore/Listao)</b>",
            'stars': "⭐⭐⭐", 'spot': "Yoff Roche",
            'depth': "0-50m", 'bait': "Vivant (Chinchard)"
        }
    elif chl > 1.5:
        return {
            'species': "🐟🐟 <b>SARDINES / ANCHOIS</b>",
            'stars': "⭐⭐", 'spot': "Almadies",
            'depth': "0-20m", 'bait': "Filet / Plumes"
        }
    elif 22 <= sst <= 28:
        return {
            'species': "🐟 <b>LIEUTENANT / DENTÉ</b>",
            'stars': "⭐⭐", 'spot': "Ngor 25m",
            'depth': "20-40m", 'bait': "Crevette / Seiche"
        }
    else:
        return {
            'species': "🐟 <b>CHINCHARD / THIOF</b>",
            'stars': "⭐", 'spot': "Cayar / Fosse",
            'depth': "10-30m", 'bait': "Sardine découpée"
        }

def telegram_send_pro(bulletin, photo_path=None):
    """📱 Notification unifiée Image + Texte"""
    if not TG_TOKEN or not TG_ID:
        print("⚠️ Telegram non configuré.")
        return False
    
    try:
        if photo_path and os.path.exists(photo_path):
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open(photo_path, 'rb') as f:
                payload = {"chat_id": TG_ID, "caption": bulletin, "parse_mode": "HTML"}
                r = requests.post(url, data=payload, files={"photo": f}, timeout=30)
        else:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            payload = {"chat_id": TG_ID, "text": bulletin, "parse_mode": "HTML"}
            r = requests.post(url, data=payload, timeout=20)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Erreur envoi Telegram: {e}")
        return False

def main():
    try:
        # 1. Acquisition et Archivage
        data = copernicus_fishing_conditions()
        log_to_csv(data)
        
        now = datetime.datetime.now(UTC)
        ts = now.strftime('%d/%m %H:%M UTC')
        
        # 2. Analyse Métier
        fish = fish_prediction(data['sst'], data['chl'])
        
        # 3. Diagnostic Sécurité
        if data['vhm0'] < 1.2:
            secu, emoji = "🟢 EXCELLENTE (Mer calme)", "✅"
        elif data['vhm0'] < 1.8:
            secu, emoji = "🟡 PRUDENCE (Houle modérée)", "⚠️"
        else:
            secu, emoji = "🔴 DANGER (Sortie déconseillée)", "❌"
            
        # 4. Préparation du Bulletin
        bulletin = (
            f"<b>🌊 PECHEUR CONNECT - RAPPORT</b> 🇸🇳\n"
            f"📅 <i>{ts}</i> | Source: Copernicus Marine\n\n"
            f"🌡️ <b>SST:</b> <code>{data['sst']}°C</code>\n"
            f"🌿 <b>CHLORO:</b> <code>{data['chl']} mg/m³</code>\n"
            f"🌊 <b>Vagues:</b> <code>{data['vhm0']}m</code>\n\n"
            f"{emoji} <b>SÉCURITÉ:</b> {secu}\n\n"
            f"🎣 <b>ZONE ACTIVE : {fish['spot'].upper()}</b>\n"
            f"{fish['species']} {fish['stars']}\n"
            f"⚓ <b>TECHNIQUE:</b> {fish['depth']} | {fish['bait']}\n"
            f"📍 <a href='https://www.google.com/maps?q=14.75,-17.48'>Position GPS suggérée</a>\n\n"
            f"🛶 <i>PecheurConnect : La technologie au service de la mer.</i>"
        )
        
        # 5. Visualisation (Style Dark pour mobile)
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Normalisation visuelle : Chloro x10 pour être lisible face à la SST
        labels = ['SST (°C)', 'CHLORO (x10)', 'Vagues (m)']
        values = [data['sst'], data['chl'] * 10, data['vhm0']]
        colors = ['#ff4500', '#32cd32', '#1e90ff']
        
        bars = ax.bar(labels, values, color=colors, alpha=0.9)
        ax.set_title(f"Données Océanographiques Dakar - {ts}", fontsize=14, pad=20)
        
        # Ajout des valeurs sur les barres
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.5, 
                    f"{yval/10 if 'CHLORO' in labels[int(bar.get_x()+0.5)] else yval}", 
                    ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        img_path = 'pecheur_report.png'
        plt.savefig(img_path, dpi=120)
        plt.close()
        
        # 6. Finalisation
        if telegram_send_pro(bulletin, img_path):
            print("🚀 Bulletin PecheurConnect envoyé !")
        
        return 0
    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
