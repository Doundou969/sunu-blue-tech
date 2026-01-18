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
        print("🚀 Extraction des données (Physique + Vagues)...")
        
        # 1. Dataset Physique (Température + Courant)
        ds_phys = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m", 
            username=USER, password=PASS,
            minimum_longitude=-18.5, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0
        )

        # 2. Dataset Vagues
        ds_wav = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
            username=USER, password=PASS,
            minimum_longitude=-18.5, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0
        )

        rapport = f"🛡️ *SUNU-BLUE-TECH : SÉCURITÉ TOTALE*\n"
        rapport += f"📅 `{datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}`\n"
        rapport += "━━━━━━━━━━━━━━━\n\n"
        
        plt.figure(figsize=(10, 8))
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, (nom, coord) in enumerate(ZONES.items()):
            # Data Physique
            dp = ds_phys.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
            if 'depth' in dp.dims: dp = dp.isel(depth=0)
            
            # Data Vagues (VHM0 = Hauteur significative des vagues)
            dw = ds_wav.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)

            u, v = float(dp.uo.values), float(dp.vo.values)
            temp = float(dp.thetao.values)
            vague = float(dw.VHM0.values)
            vitesse = np.sqrt(u**2 + v**2) * 3.6 
            
            # Alerte Vagues
            warning = "⚠️" if vague > 2.0 else "🛑" if vague > 3.0 else "✅"

            rapport += f"📍 *{nom}* {warning}\n"
            rapport += f"🌊 Vagues : *{vague:.1f} m*\n"
            rapport += f"🌡️ Eau : {temp:.1f}°C | 🚩 Courant : {vitesse:.1f} km/h\n"
            rapport += "───────────────\n"

            # Graphique
            plt.quiver(0, -i, u, v, color=colors[i], scale=1.5, width=0.015)
            plt.text(0.3, -i, f"{nom}: {vague:.1f}m / {temp:.1f}°C", va='center', fontsize=11, fontweight='bold', color=colors[i])

        plt.title("État de la Mer au Sénégal (Vagues & Courants)", fontsize=14)
        plt.xlim(-0.5, 2.5)
        plt.ylim(-len(ZONES), 1)
        plt.axis('off')
        
        image_path = "bulletin_securite.png"
        plt.savefig(image_path, bbox_inches='tight', dpi=150)
        plt.close()

        rapport += "\n⚓ *Sécurité + Rendement = Succès !*"
        send_tg_with_photo(rapport, image_path)

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_ID, "text": f"❌ Erreur : {e}"})

if __name__ == "__main__":
    job()
