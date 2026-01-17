import os
import requests
import copernicusmarine
import datetime
import numpy as np
import matplotlib.pyplot as plt
import json

# --- CONFIGURATION ---
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

ZONES = [
    {"nom": "Saint-Louis", "lat": 16.0, "lon": -16.6},
    {"nom": "Dakar / Kayar", "lat": 14.9, "lon": -17.5},
    {"nom": "Mbour / Joal", "lat": 14.1, "lon": -17.0}
]

def send_tg_album(media_list):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup"
    
    files = {}
    media_payload = []
    
    for i, item in enumerate(media_list):
        file_key = f"photo{i}"
        # On ouvre le fichier
        files[file_key] = open(item['path'], 'rb')
        # On prépare l'entrée pour l'album
        media_payload.append({
            "type": "photo",
            "media": f"attach://{file_key}",
            "caption": item['caption'],
            "parse_mode": "Markdown"
        })
    
    # Envoi avec formatage JSON correct
    response = requests.post(
        url, 
        data={"chat_id": TG_ID, "media": json.dumps(media_payload)}, 
        files=files
    )
    return response.json()

def job():
    try:
        print("🚀 Chargement des données nationales...")
        DATASET_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
        
        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID, username=USER, password=PASS,
            minimum_longitude=-18.0, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0
        )

        album = []
        for zone in ZONES:
            # Extraction des données
            data = ds.sel(latitude=zone['lat'], longitude=zone['lon'], method="nearest")
            if 'time' in data.dims: data = data.isel(time=-1)
            if 'depth' in data.dims: data = data.isel(depth=0)

            u = float(np.array(data.uo.values).flatten()[0])
            v = float(np.array(data.vo.values).flatten()[0])
            vitesse = np.sqrt(u**2 + v**2) * 3.6 
            
            # Création du graphique
            plt.figure(figsize=(4, 4))
            plt.quiver(0, 0, u, v, color='blue', scale=1, width=0.02)
            plt.text(0, -0.4, f"{vitesse:.1f} km/h", ha='center', fontsize=12, fontweight='bold')
            plt.title(f"{zone['nom']}")
            plt.axis('off')
            plt.xlim(-1, 1); plt.ylim(-1, 1)
            
            clean_name = zone['nom'].replace(' ', '_').replace('/', '_')
            img_path = f"img_{clean_name}.png"
            plt.savefig(img_path, bbox_inches='tight')
            plt.close()

            # Rapport
            maps_link = f"https://www.google.com/maps?q={zone['lat']},{zone['lon']}"
            caption = (
                f"🌊 *{zone['nom'].upper()}*\n"
                f"🚩 Courant : {vitesse:.1f} km/h\n"
                f"⚓ État : {'✅ CALME' if vitesse < 15 else '⚠️ AGITÉE'}\n"
                f"📍 [Carte]({maps_link})"
            )
            album.append({"path": img_path, "caption": caption})

        # Envoi
        res = send_tg_album(album)
        if not res.get("ok"):
            # Si l'album échoue, on envoie un message d'erreur
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": TG_ID, "text": f"❌ Erreur Telegram : {res.get('description')}"})
        else:
            print("✅ Album national envoyé !")

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_ID, "text": f"❌ Erreur Script : {e}"})

if __name__ == "__main__":
    job()
