import copernicusmarine
import numpy as np
import matplotlib.pyplot as plt
import requests
import os
from datetime import datetime

# --- 1. CONFIGURATION ---
USER = os.getenv('USER_COP')
PWD = os.getenv('PWD_COP')
TOKEN = os.getenv('TG_TOKEN')
ID = os.getenv('TG_ID')

WIND_ID = "cmems_mod_glo_phy_anfc_merged-uv_PT1H-i" # ID pour le Vent

try:
    print("🔑 Connexion...")
    copernicusmarine.login(username=USER, password=PWD)

    # --- 2. TÉLÉCHARGEMENT SST (TEMPÉRATURE) ---
    ds_sst = copernicusmarine.open_dataset(dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2", 
        minimum_longitude=-18.5, maximum_longitude=-16.5, 
        minimum_latitude=14.0, maximum_latitude=15.5)
    sst = (ds_sst.analysed_sst.isel(time=-1) - 273.15).compute()

    # --- 3. TÉLÉCHARGEMENT VENT ---
    print("🌬️ Analyse du vent...")
    ds_wind = copernicusmarine.open_dataset(dataset_id=WIND_ID,
        minimum_longitude=-18.5, maximum_longitude=-16.5,
        minimum_latitude=14.0, maximum_latitude=15.5)
    # On calcule la vitesse (Magnitude) à partir des composantes U et V
    wind_data = ds_wind.isel(time=-1)
    wind_speed = np.sqrt(wind_data.utotal**2 + wind_data.vtotal**2).compute()
    # Conversion m/s en km/h
    wind_kmh = wind_speed * 3.6

    # --- 4. CALCUL DU POINT GPS ---
    abs_diff = np.abs(sst - 20.5)
    idx = np.unravel_index(abs_diff.argmin(), abs_diff.shape)
    lat_p = float(sst.latitude[idx[0]])
    lon_p = float(sst.longitude[idx[1]])
    
    # Vitesse du vent au point précis
    v_vent = float(wind_kmh.sel(latitude=lat_p, longitude=lon_p, method="nearest"))

    # --- 5. ANALYSE SÉCURITÉ (Ajustée pour les pirogues du Sénégal) ---
    # 0-15 km/h : Mer d'huile / 15-25 : Petite brise / +30 : Risque de chavirement
    if v_vent < 15:
        safety_status = "✅ MER CALME (Conditions Idéales)"
        emoji = "🌊"
    elif v_vent < 27:
        safety_status = "⚠️ VENT MODÉRÉ (Prudence en mer)"
        emoji = "⛵"
    else:
        safety_status = "🚫 DANGER : VENT FORT (Sortie Déconseillée)"
        emoji = "🚩"

    # --- 6. CARTE ---
    plt.figure(figsize=(10, 8))
    sst.plot(cmap='RdYlBu_r')
    plt.scatter(lon_p, lat_p, color='yellow', s=200, marker='*', edgecolor='black')
    plt.title(f"Sunu-Blue-Tech - {datetime.now().strftime('%d/%m/%Y')}")
    plt.savefig('carte.jpg')
    plt.close()

    # --- 7. ENVOI TELEGRAM ---
    google_maps_link = f"http://maps.google.com/maps?q={lat_p},{lon_p}"
    
    caption = (
        f"🚀 *SUNU-BLUE-TECH : RAPPORT DU JOUR*\n\n"
        f"📍 *ZONE DE PÊCHE*\n"
        f"Position: `{lat_p:.4f}, {lon_p:.4f}`\n"
        f"Température: 20.5°C\n\n"
        f"🌬️ *MÉTÉO & SÉCURITÉ*\n"
        f"Vitesse Vent: {v_vent:.1f} km/h\n"
        f"État: {safety_status}\n\n"
        f"🔗 [OUVRIR DANS GOOGLE MAPS]({google_maps_link})"
    )
    
    with open('carte.jpg', 'rb') as photo:
        requests.post(url=f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                      data={'chat_id': ID, 'caption': caption, 'parse_mode': 'Markdown'}, 
                      files={'photo': photo})

    print(f"✅ Rapport complet envoyé (Vent: {v_vent:.1f} km/h)")

except Exception as e:
    print(f"❌ Erreur : {e}")
