import os
import requests
import copernicusmarine
import datetime
import numpy as np

# --- RÉCUPÉRATION ---
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def send_tg(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_ID, "text": message, "parse_mode": "Markdown"})

def job():
    try:
        # 1. CONNEXION SÉCURISÉE (On force l'absence de fichier config pour éviter les erreurs d'écriture)
        print("🚀 Connexion au catalogue Copernicus...")
        
        # Le dataset le plus stable pour le courant à Dakar en 2026
        DATASET_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"

        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID,
            username=USER,
            password=PASS,
            # On restreint la zone pour que ce soit rapide
            minimum_longitude=-18.0, 
            maximum_longitude=-17.0,
            minimum_latitude=14.0, 
            maximum_latitude=15.0
        )

        # 2. EXTRACTION DES DONNÉES (Point Kayar/Dakar)
        # On récupère uo (Est) et vo (Nord)
        data = ds.isel(time=-1).sel(latitude=14.9, longitude=-17.5, method="nearest")
        
        u = float(data.uo.values)
        v = float(data.vo.values)
        vitesse = np.sqrt(u**2 + v**2) * 3.6 # Conversion m/s -> km/h
        
        # Détermination de la direction
        if abs(u) > abs(v):
            dir_c = "Est ➡️" if u > 0 else "Ouest ⬅️"
        else:
            dir_c = "Nord ⬆️" if v > 0 else "Sud ⬇️"

        # État de la mer (Sécurité)
        etat_mer = "✅ CALME" if vitesse < 15 else "⚠️ AGITÉE" if vitesse < 25 else "🛑 DANGER"

        # 3. MISE EN FORME DU RAPPORT
        now = datetime.datetime.now()
        date_str = now.strftime("%d/%m/%Y à %H:%M")
        
        rapport = (
            f"🌊 *SUNU-BLUE-TECH : RAPPORT PÊCHE*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 Date : `{date_str}`\n"
            f"📍 Zone : *Dakar / Kayar*\n\n"
            f"🚩 *INFOS COURANT :*\n"
            f"Direction : {dir_c}\n"
            f"Vitesse : {vitesse:.1f} km/h\n"
            f"État : {etat_mer}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔗 [Google Maps](http://www.google.com/maps/place/14.9,-17.5)\n"
            f"⚓ *Xam-Xam au service du Géej !*"
        )

        send_tg(rapport)
        print("✅ Rapport envoyé avec succès !")

    except Exception as e:
        # En cas d'erreur, on t'envoie le détail technique sur Telegram
        send_tg(f"❌ *Erreur Copernicus :* \n`{str(e)}` \nVérifiez vos identifiants sur le site Copernicus.")

if __name__ == "__main__":
    job()
