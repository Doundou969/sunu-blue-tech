import copernicusmarine
import numpy as np
import matplotlib.pyplot as plt
import requests
import os
from datetime import datetime

# --- 1. CONNEXION SÉCURISÉE ---
# On récupère les accès cachés dans le coffre-fort de GitHub
USER = os.getenv('USER_COP')
PWD = os.getenv('PWD_COP')
TOKEN = os.getenv('TG_TOKEN')
ID = os.getenv('TG_ID')

try:
    # Connexion automatique
    copernicusmarine.login(username=USER, password=PWD, skip_if_logged_in=True)

    # --- 2. TÉLÉCHARGEMENT ---
    print("📡 Récupération des données satellite...")
    ds = copernicusmarine.open_dataset(dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2", 
        minimum_longitude=-18.5, maximum_longitude=-16.5, 
        minimum_latitude=14.0, maximum_latitude=15.5)
    sst = (ds.analysed_sst.isel(time=-1) - 273.15).compute()

    # --- 3. CALCUL DU POINT GPS ---
    abs_diff = np.abs(sst - 20.5)
    idx = np.unravel_index(abs_diff.argmin(), abs_diff.shape)
    lat_p = float(sst.latitude[idx[0]])
    lon_p = float(sst.longitude[idx[1]])

    # --- 4. CRÉATION DE LA CARTE ---
    plt.figure(figsize=(10, 8))
    sst.plot(cmap='RdYlBu_r')
    plt.scatter(lon_p, lat_p, color='yellow', s=200, marker='*', edgecolor='black')
    date_str = datetime.now().strftime('%d/%m/%Y')
    plt.title(f"Sunu-Blue-Tech - {date_str}")
    plt.savefig('carte.jpg')

    # --- 5. ENVOI TELEGRAM ---
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    caption = f"🚀 Point trouvé !\n📍 GPS: {lat_p:.4f}, {lon_p:.4f}\n🌡️ Temp: 20.5°C"
    with open('carte.jpg', 'rb') as photo:
        requests.post(url, data={'chat_id': ID, 'caption': caption}, files={'photo': photo})
    
    print("✅ Fiche envoyée avec succès !")

except Exception as e:
    print(f"❌ Erreur : {e}")
