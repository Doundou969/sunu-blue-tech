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

WIND_ID = "cmems_mod_glo_phy_anfc_merged-uv_PT1H-i"

try:
    print("🔑 Connexion...")
    copernicusmarine.login(username=USER, password=PWD)

    # --- 2. TÉLÉCHARGEMENT TEMPÉRATURE (SST) ---
    ds_sst = copernicusmarine.open_dataset(dataset_id="METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2", 
        minimum_longitude=-18.5, maximum_longitude=-16.5, 
        minimum_latitude=14.0, maximum_latitude=15.5)
    sst = (ds_sst.analysed_sst.isel(time=-1) - 273.15).compute()

    # --- 3. CALCUL DU POINT GPS ---
    abs_diff = np.abs(sst - 20.5)
    idx = np.unravel_index(abs_diff.argmin(), abs_diff.shape)
    lat_p = float(sst.latitude[idx[0]])
    lon_p = float(sst.longitude[idx[1]])

    # --- 4. TÉLÉCHARGEMENT VENT ET COURANT ---
    print("🌬️ Analyse du vent et 🌊 courant...")
    ds_wind = copernicusmarine.open_dataset(dataset_id=WIND_ID,
        minimum_longitude=-18.5, maximum_longitude=-16.5,
        minimum_latitude=14.0, maximum_latitude=15.5)
    
    data_point = ds_wind.isel(time=-1).sel(latitude=lat_p, longitude=lon_p, method="nearest")
    
    # CALCUL VENT
    u_wind = float(data_point.utotal.compute())
    v_wind = float(data_point.vtotal.compute())
    v_vent = float(np.sqrt(u_wind**2 + v_wind**2) * 3.6)

    # CALCUL COURANT (Direction)
    if abs(u_wind) > abs(v_wind):
        dir_courant = "Est ➡️" if u_wind > 0 else "Ouest ⬅️"
    else:
        dir_courant = "Nord ⬆️" if v_wind > 0 else "Sud ⬇️"

    # --- 5. ANALYSE SÉCURITÉ ---
    if v_vent < 15:
        safety_status = "✅ MER CALME"
    elif v_vent < 27:
        safety_status = "⚠️ VENT MODÉRÉ"
    else:
        safety_status = "🚫 DANGER : VENT FORT"

    # --- 6. GÉNÉRATION DE LA CARTE ---
    plt.figure(figsize=(10, 8))
    sst.plot(cmap='RdYlBu_r')
    plt.scatter(lon_p, lat_p, color='yellow', s=200, marker='*', edgecolor='black')
    plt.title(f"Sunu-Blue-Tech - {datetime.now().strftime('%d/%m/%Y')}")
    plt.savefig('carte.jpg')
    plt.close()

    # --- 7. ENVOI TELEGRAM ---
    google_maps_link = f"http://www.google.com/maps/place/{lat_p},{lon_p}"
    
    import datetime
    now = datetime.datetime.now()
    # Si il est avant midi, c'est l'édition matin, sinon soir
    edition = "🌅 ÉDITION MATIN" if now.hour < 12 else "🌙 ÉDITION SOIR"

    caption = (
        f"🚀 *{edition}*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📍 *ZONE DE PÊCHE*\n"
        f"Position: `{lat_p:.4f}, {lon_p:.4f}`\n"
        f"Température: 20.5°C\n\n"
        f"🌊 *COURANT & VENT*\n"
        f"Direction Courant: {dir_courant}\n"
        f"Vitesse Vent: {v_vent:.1f} km/h\n"
        f"État: {safety_status}\n\n"
        f"🔗 [OUVRIR DANS GOOGLE MAPS]({google_maps_link})"
    )
    
    with open('carte.jpg', 'rb') as photo:
        requests.post(url=f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                      data={'chat_id': ID, 'caption': caption, 'parse_mode': 'Markdown'}, 
                      files={'photo': photo})

    print("✅ Tout est envoyé avec succès !")

except Exception as e:
    print(f"❌ Erreur : {e}")
