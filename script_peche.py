import copernicusmarine
import numpy as np
import matplotlib.pyplot as plt
import requests
import os
from datetime import datetime

# --- 1. CONNEXION SÉCURISÉE ---
USER = os.getenv('USER_COP')
PWD = os.getenv('PWD_COP')
TOKEN = os.getenv('TG_TOKEN')
ID = os.getenv('TG_ID')

try:
    # Connexion simplifiée (Correction de l'erreur)
    print("🔑 Connexion à Copernicus...")
    copernicusmarine.login(username=USER, password=PWD)

    # --- 2. TÉLÉCHARGEMENT ---
    print("📡 Récupération des données satellite...")
    ds = copernicusmarine.open_dataset(dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2", 
        minimum_longitude=-18.5, maximum_longitude=-16.5, 
        minimum_latitude=14.0, maximum_latitude=15.5)
    sst = (ds.analysed_sst.isel(time=-1) - 273.15).compute()

    # --- 3. CALCUL DU POINT GPS ---
    abs_diff = np.abs(sst - 20.5)
    dim_lat, dim_lon = sst.dims[0], sst.dims[1]
    idx = np.unravel_index(abs_diff.argmin(), abs_diff.shape)
    lat_p = float(sst[dim_lat][idx[0]])
    lon_p = float(sst[dim_lon][idx[1]])

    # --- 4. CRÉATION DE LA CARTE ---
    print("🎨 Création de la carte...")
    plt.figure(figsize=(10, 8))
    sst.plot(cmap='RdYlBu_r')
    plt.scatter(lon_p, lat_p, color='yellow', s=200, marker='*', edgecolor='black')
    date_str = datetime.now().strftime('%d/%m/%Y')
    plt.title(f"Sunu-Blue-Tech - {date_str}")
    plt.savefig('carte.jpg')
    plt.close()

    # --- 5. ENVOI TELEGRAM ---
    print("📲 Envoi à Telegram...")
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    
    # Création du lien Google Maps
    google_maps_link = f"https://www.google.com/maps/search/?api=1&query={lat_p},{lon_p}"
    
    caption = (
        f"🚀 *POINT DE PÊCHE TROUVÉ !*\n\n"
        f"🌡️ *Température :* 20.5°C\n"
        f"📍 *Position :* `{lat_p:.4f}, {lon_p:.4f}`\n"
        f"📅 *Date :* {date_str}\n\n"
        f"🔗 [CLIQUEZ ICI POUR NAVIGUER]({google_maps_link})"
    )
    
    with open('carte.jpg', 'rb') as photo:
        response = requests.post(url, data={
            'chat_id': ID, 
            'caption': caption, 
            'parse_mode': 'Markdown' # Très important pour le lien cliquable
        }, files={'photo': photo})

except Exception as e:
    print(f"❌ Erreur critique : {e}")
