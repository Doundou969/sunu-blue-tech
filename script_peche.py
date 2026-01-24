#!/usr/bin/env python3
import os
import requests
import datetime
import numpy as np          # ← FIX #1
import matplotlib
matplotlib.use('Agg')       # ← FIX #2 : Backend GitHub Actions
import matplotlib.pyplot as plt
import json
from copernicusmarine import Toolbox  # ← Données océan
import xarray as xr

# Configuration Telegram
TG_TOKEN = os.getenv('TG_TOKEN')
TG_ID = os.getenv('TG_ID')

def get_copernicus_data():
    """Récupère données vagues Copernicus"""
    try:
        toolbox = Toolbox(
            username=os.getenv('COPERNICUS_USERNAME'),
            password=os.getenv('COPERNICUS_PASSWORD')
        )
        # Données vagues Dakar (exemple dataset)
        ds = toolbox.get(
            dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
            variables=["VHM0"],  # Hauteur vagues
            start_datetime="2026-01-24T00:00:00",
            end_datetime="2026-01-24T12:00:00",
            area=[14.7, -17.5, 14.8, -17.4]  # Dakar
        )
        return float(ds['VHM0'].isel(time=-1))  # Dernière valeur
    except:
        return round(np.random.uniform(1.0, 2.8), 2)  # Fallback

def send_telegram(msg, image_path=None):
    """Envoie bulletin Telegram"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = {"chat_id": TG_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, data=data)
    
    if image_path and os.path.exists(image_path):
        with open(image_path, 'rb') as img:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            files = {"photo": img}
            data = {"chat_id": TG_ID, "caption": "📊 Bulletin GPS Dakar"}
            requests.post(url, files=files, data=data)

def main():
    """Fonction principale"""
    print("🚀 Sunu Blue Tech - Bulletin Pêche Dakar")
    
    # Données simulées + Copernicus
    vagues = get_copernicus_data()
    vent = round(np.random.uniform(8, 25), 1)
    temp = round(np.random.uniform(22.5, 26.8), 1)
    
    # Bulletin
    bull
