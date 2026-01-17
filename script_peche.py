import os
import requests
import copernicusmarine
import datetime
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def send_tg_with_photo(caption, photo_path):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo})

def job():
    try:
        DATASET_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
        
        # --- MODIFIE CES DEUX LIGNES ICI ---
        lat, lon = 16.0, -16.6  # Coordonnées pour Saint-Louis
        nom_zone = "Saint-Louis"


        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID, username=USER, password=PASS,
            minimum_longitude=lon-0.5, maximum_longitude=lon+0.5,
            minimum_latitude=lat-0.5, maximum_latitude=lat+0.5
        )

        data = ds.sel(latitude=lat, longitude=lon, method="nearest")
        if 'time' in data.dims: data = data.isel(time=-1)
        if 'depth' in data.dims: data = data.isel(depth=0)

        u = float(np.array(data.uo.values).flatten()[0])
        v = float(np.array(data.vo.values).flatten()[0])
        vitesse = np.sqrt(u**2 + v**2) * 3.6 
        
        # --- CRÉATION DE L'IMAGE ---
        plt.figure(figsize=(5, 5))
        # Dessiner la flèche du courant
        plt.quiver(0, 0, u, v, color='red', scale=1)
        plt.text(0, -0.2, f"Vitesse: {vitesse:.1f} km/h", ha='center', fontsize=12, fontweight='bold')
        plt.title(f"Direction du Courant - Dakar/Kayar")
        plt.axis('off')
        plt.xlim(-1, 1)
        plt.ylim(-1, 1)
        
        image_path = "courant.png"
        plt.savefig(image_path, bbox_inches='tight')
        plt.close()

        # --- RAPPORT TEXTE ---
        now = datetime.datetime.now()
        google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        rapport = (
            f"🌊 *SUNU-BLUE-TECH : BULLETIN DU GÉEJ*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 `{now.strftime('%d/%m/%Y à %H:%M')}`\n"
            f"📍 *Dakar / Kayar*\n\n"
            f"🚩 *INFOS COURANT :*\n"
            f"Vitesse : {vitesse:.1f} km/h\n"
            f"État : {'✅ CALME' if vitesse < 15 else '⚠️ AGITÉE'}\n\n"
            f"👉 [VOIR SUR LA CARTE]({google_maps_link})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚓ *Xam-Xam au service du Géej !*"
        )

        send_tg_with_photo(rapport, image_path)
        print("✅ Rapport avec image envoyé !")

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_ID, "text": f"❌ Erreur : {e}"})

if __name__ == "__main__":
    job()
