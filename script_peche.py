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
        # Datasets
        ds_phys = copernicusmarine.open_dataset(dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m", username=USER, password=PASS, minimum_longitude=-18.5, maximum_longitude=-16.0, minimum_latitude=12.0, maximum_latitude=17.0)
        ds_wav = copernicusmarine.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", username=USER, password=PASS, minimum_longitude=-18.5, maximum_longitude=-16.0, minimum_latitude=12.0, maximum_latitude=17.0)

        # En-tête du rapport
        rapport = f"🇸🇳 *SUNU-BLUE-TECH : SYSTÈME D'ALERTE*\n"
        rapport += f"📅 `{datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')}`\n"
        rapport += "━━━━━━━━━━━━━━━\n\n"
        
        plt.figure(figsize=(10, 8))
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, (nom, coord) in enumerate(ZONES.items()):
            dp = ds_phys.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
            if 'depth' in dp.dims: dp = dp.isel(depth=0)
            dw = ds_wav.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)

            u, v = float(dp.uo.values), float(dp.vo.values)
            temp, vague = float(dp.thetao.values), float(dw.VHM0.values)
            vitesse = np.sqrt(u**2 + v**2) * 3.6 
            
            # Diagnostic de sécurité
            status = "✅ CALME" if vague < 1.5 else "⚠️ PRUDENCE" if vague < 2.5 else "🛑 DANGER"

            rapport += f"📍 *{nom}* -> {status}\n"
            rapport += f"🌊 Vagues : *{vague:.2f} m* | 🌡️ {temp:.1f}°C\n"
            rapport += f"🚩 Courant : {vitesse:.1f} km/h\n"
            rapport += "───────────────\n"

            plt.quiver(0, -i, u, v, color=colors[i], scale=1.5, width=0.015)
            plt.text(0.3, -i, f"{nom}: {vague:.1f}m", va='center', fontsize=11, fontweight='bold', color=colors[i])

        # Pied de page avec numéros d'urgence
        rapport += "\n🆘 *URGENCE EN MER (HASSMAR) :*\n"
        rapport += "📞 **119** (Appel gratuit)\n"
        rapport += "📞 **33 821 76 37** (MRCC Dakar)\n"
        rapport += "\n⚓ *Xam-Xam pour la sécurité des pêcheurs.*"

        plt.title("Carte des Courants et Vagues - Sunu-Blue-Tech", fontsize=14)
        plt.xlim(-0.5, 2.5)
        plt.ylim(-len(ZONES), 1)
        plt.axis('off')
        
        image_path = "bulletin_pro.png"
        plt.savefig(image_path, bbox_inches='tight', dpi=150)
        plt.close()

        send_tg_with_photo(rapport, image_path)

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_ID, "text": f"❌ Erreur système : {e}"})

if __name__ == "__main__":
    job()
