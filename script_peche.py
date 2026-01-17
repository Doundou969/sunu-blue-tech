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

ZONES = {
    "SAINT-LOUIS": {"lat": 16.0, "lon": -16.6},
    "LOMPOUL": {"lat": 15.4, "lon": -16.8},
    "DAKAR / KAYAR": {"lat": 14.9, "lon": -17.5},
    "MBOUR / JOAL": {"lat": 14.1, "lon": -17.0},
    "CASAMANCE": {"lat": 12.5, "lon": -16.8}
}

def send_tg_with_photo(caption, photo_path):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo})

def job():
    try:
        print("🚀 Récupération Température + Courants...")
        # On utilise le dataset physique global qui contient tout
        DATASET_ID = "cmems_mod_glo_phy_anfc_0.083deg_PT1H-m"
        
        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID, username=USER, password=PASS,
            minimum_longitude=-18.5, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0
        )

        rapport = f"🌡️ *SUNU-BLUE-TECH : BULLETIN COMPLET*\n"
        rapport += f"📅 `{datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}`\n"
        rapport += "━━━━━━━━━━━━━━━\n\n"
        
        plt.figure(figsize=(10, 8))
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, (nom, coord) in enumerate(ZONES.items()):
            data = ds.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest")
            if 'time' in data.dims: data = data.isel(time=-1)
            if 'depth' in data.dims: data = data.isel(depth=0)

            # Extraction Courants + Température
            u = float(np.array(data.uo.values).flatten()[0])
            v = float(np.array(data.vo.values).flatten()[0])
            temp = float(np.array(data.thetao.values).flatten()[0])
            vitesse = np.sqrt(u**2 + v**2) * 3.6 
            
            if abs(u) > abs(v):
                dir_txt = "Est ➡️" if u > 0 else "Ouest ⬅️"
            else:
                dir_txt = "Nord ⬆️" if v > 0 else "Sud ⬇️"

            # Construction du texte
            rapport += f"📍 *{nom}*\n"
            rapport += f"🌊 Courant : {dir_txt} ({vitesse:.1f} km/h)\n"
            rapport += f"🌡️ Temp. Eau : *{temp:.1f}°C*\n"
            rapport += "───────────────\n"

            # Graphique
            plt.quiver(0, -i, u, v, color=colors[i], scale=1.5, width=0.015)
            plt.text(0.3, -i, f"{nom} ({temp:.1f}°C)", va='center', fontsize=12, fontweight='bold', color=colors[i])

        plt.title("Courants et Températures de l'eau - Sénégal", fontsize=15)
        plt.xlim(-0.5, 2.0)
        plt.ylim(-len(ZONES), 1)
        plt.axis('off')
        
        image_path = "national_temp.png"
        plt.savefig(image_path, bbox_inches='tight', dpi=150)
        plt.close()

        rapport += "\n⚓ *Xam-Xam au service du Géej !*"
        send_tg_with_photo(rapport, image_path)
        print("✅ Bulletin envoyé !")

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_ID, "text": f"❌ Erreur : {e}"})

if __name__ == "__main__":
    job()
