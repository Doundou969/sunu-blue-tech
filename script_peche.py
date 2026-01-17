import xarray as xr
import copernicusmarine
import numpy as np
import requests
import datetime
import os

# --- CONFIGURATION ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")
CP_USER = os.getenv("COPERNICUS_USERNAME")
CP_PASS = os.getenv("COPERNICUS_PASSWORD")

# Utilisation du dataset courant/physique le plus stable
DATASET_ID = "cmems_mod_glo_phy_anfc_0.083deg_PT6H-i"

def job():
    try:
        now = datetime.datetime.now()
        edition = "🌅 ÉDITION MATIN" if now.hour < 12 else "🌙 ÉDITION SOIR"
        
        print(f"🚀 Connexion Copernicus...")
        
        # 1. Chargement des données
        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID,
            username=CP_USER,
            password=CP_PASS,
            minimum_longitude=-18.0, 
            maximum_longitude=-17.0,
            minimum_latitude=14.5, 
            maximum_latitude=15.5
        )
        
        # 2. Point GPS (Dakar/Kayar)
        lat_p, lon_p = 14.90, -17.50
        
        # 3. Extraction (On prend les courants uo et vo)
        # On utilise .last() ou isel(time=-1)
        data = ds.isel(time=-1).sel(latitude=lat_p, longitude=lon_p, method="nearest")
        
        # Correction des noms de variables selon le dataset physique
        u_curr = float(data.uo.values)
        v_curr = float(data.vo.values)
        
        # Calcul de la vitesse et direction
        vitesse = np.sqrt(u_curr**2 + v_curr**2) * 3.6
        
        if abs(u_curr) > abs(v_curr):
            dir_c = "Est ➡️" if u_curr > 0 else "Ouest ⬅️"
        else:
            dir_c = "Nord ⬆️" if v_curr > 0 else "Sud ⬇️"

        safety = "✅ SÉCURISÉ" if vitesse < 25 else "⚠️ PRUDENCE : VENT/COURANT FORT"

        # 4. Envoi Telegram
        google_maps = f"https://www.google.com/maps?q={lat_p},{lon_p}"
        
        caption = (
            f"{edition} : *SUNU-BLUE-TECH*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 *ZONE DE PÊCHE*\n"
            f"Position: `{lat_p}, {lon_p}`\n\n"
            f"🌊 *INFOS MER*\n"
            f"Direction Courant: {dir_c}\n"
            f"Vitesse estimée: {vitesse:.1f} km/h\n"
            f"État: {safety}\n\n"
            f"🔗 [OUVRIR GOOGLE MAPS]({google_maps})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📢 *ABONNEMENT : +221 77 702 08 18*\n"
            f"*Xam-Xam au service du Géej!*"
        )

        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": TG_ID, "text": caption, "parse_mode": "Markdown"})
        
        if r.status_code == 200:
            print("✅ Succès !")
        else:
            print(f"❌ Erreur Telegram: {r.text}")

    except Exception as e:
        print(f"❌ ERREUR FINALE : {str(e)}")
        raise e

if __name__ == "__main__":
    job()
