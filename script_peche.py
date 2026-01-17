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

# --- LISTE DES ZONES ---
ZONES = [
    {"nom": "Saint-Louis", "lat": 16.0, "lon": -16.6},
    {"nom": "Dakar / Kayar", "lat": 14.9, "lon": -17.5},
    {"nom": "Mbour / Joal", "lat": 14.1, "lon": -17.0}
]

def send_tg_with_photo(caption, photo_path):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo})

def job():
    try:
        print("🚀 Connexion Copernicus pour Multi-Zones...")
        DATASET_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
        
        # On ouvre le dataset une seule fois pour gagner du temps
        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID, username=USER, password=PASS,
            minimum_longitude=-18.0, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0
        )

        for zone in ZONES:
            print(f"📊 Analyse de la zone : {zone['nom']}")
            
            # Extraction des données
            data = ds.sel(latitude=zone['lat'], longitude=zone['lon'], method="nearest")
            if 'time' in data.dims: data = data.isel(time=-1)
            if 'depth' in data.dims: data = data.isel(depth=0)

            u = float(np.array(data.uo.values).flatten()[0])
            v = float(np.array(data.vo.values).flatten()[0])
            vitesse = np.sqrt(u**2 + v**2) * 3.6 
            
            # Création de l'image de la flèche
            plt.figure(figsize=(4, 4))
            plt.quiver(0, 0, u, v, color='blue', scale=1, width=0.02)
            plt.text(0, -0.3, f"{vitesse:.1f} km/h", ha='center', fontsize=12, fontweight='bold')
            plt.title(f"Courant : {zone['nom']}")
            plt.axis('off')
            plt.xlim(-1, 1)
            plt.ylim(-1, 1)
            
            img_name = f"courant_{zone['nom'].replace(' ', '')}.png"
            plt.savefig(img_name, bbox_inches='tight')
            plt.close()

            # Rapport texte
            now = datetime.datetime.now()
            google_maps_link = f"https://www.google.com/maps?q={zone['lat']},{zone['lon']}"
            
            rapport = (
                f"🌊 *SUNU-BLUE-TECH : {zone['nom'].upper()}*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📅 `{now.strftime('%d/%m/%Y à %H:%M')}`\n"
                f"🚩 *INFOS COURANT :*\n"
                f"Vitesse : {vitesse:.1f} km/h\n"
                f"État : {'✅ CALME' if vitesse < 15 else '⚠️ AGITÉE'}\n\n"
                f"👉 [VOIR SUR LA CARTE]({google_maps_link})\n"
                f"━━━━━━━━━━━━━━━"
            )

            send_tg_with_photo(rapport, img_name)

        print("✅ Tous les rapports ont été envoyés !")

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_ID, "text": f"❌ Erreur Multi-Zone : {e}"})

if __name__ == "__main__":
    job()
