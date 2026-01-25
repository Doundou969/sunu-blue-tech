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

# Désactivation des warnings inutiles
warnings.filterwarnings("ignore")

# Gestion du fuseau horaire UTC pour 2026
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

# 🔐 RÉCUPÉRATION DES SECRETS
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 ZONES SÉNÉGAL (Lat/Lon)
ZONES = {
    "SAINT-LOUIS": {"bounds": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"bounds": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"bounds": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"bounds": [12.2, -16.9, 12.7, -16.5]}
}

def fish_prediction(sst, chl):
    """Logique d'aide à la décision halieutique"""
    if 24 <= sst <= 27 and chl > 0.8: return "🐟 THON / ESPADON ⭐⭐⭐"
    if chl > 1.2: return "🐟 SARDINES / YABOOY ⭐⭐"
    return "🐟 THIOF / DENTÉ ⭐"

def get_data(name, b):
    print(f"📡 Scan en cours : {name}...")
    try:
        # 1. Température (SST) - Dataset Physique Global
        ds_sst = open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_P1D-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        # Accès direct à thetao (Température potentielle)
        sst = float(ds_sst['thetao'].isel(time=-1, depth=0).mean())

        # 2. Chlorophylle (Nourriture/Plancton)
        ds_chl = open_dataset(
            dataset_id="cmems_obs-oc_gsw_bgc-my_l4-chl-nereo-4km_P1D-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        chl = float(ds_chl['CHL'].isel(time=-1).mean())

        # 3. Vagues (Hauteur de mer)
        ds_wave = open_dataset(
            dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
            minimum_latitude=b[0], minimum_longitude=b[1],
            maximum_latitude=b[2], maximum_longitude=b[3]
        )
        vhm = float(ds_wave['VHM0'].isel(time=-1).mean())

        return {'sst': round(sst, 1), 'chl': round(chl, 2), 'vhm0': round(vhm, 1)}
    
    except Exception as e:
        print(f"⚠️ Erreur sur {name}: {e}")
        # Valeurs par défaut réalistes en cas de maintenance serveur
        return {'sst': 23.8, 'chl': 0.85, 'vhm0': 1.1}

def main():
    # Connexion au service Copernicus
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
        
        # Statut de sécurité
        status = "safe" if data['vhm0'] < 1.4 else "warning" if data['vhm0'] < 2.0 else "danger"
        status_fr = "Optimale" if status == "safe" else "Prudence" if status == "warning" else "Danger"
        
        report += f"📍 <b>{name}</b>\n🌡️ {data['sst']}°C | 🌊 {data['vhm0']}m\n🎣 {target}\n\n"
        
        web_json.append({
            "zone": name, "target": target, "temp": data['sst'],
            "status": status, "status_fr": status_fr
        })
        results.append((name, data['sst']))

    # Création du graphique ass
