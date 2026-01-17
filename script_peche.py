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

DATASET_ID = "cmems_mod_glo_phy_anfc_0.083deg_PT6H-i"

def job():
    try:
        now = datetime.datetime.now()
        edition = "🌅 ÉDITION MATIN" if now.hour < 12 else "🌙 ÉDITION SOIR"
        
        print(f"🚀 Tentative de connexion pour {CP_USER}...")

        # FORCE L'AUTHENTIFICATION
        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID,
            username=CP_USER,
            password=CP_PASS,
            minimum_longitude=-18.0, 
            maximum_longitude=-17.0,
            minimum_latitude=14.5, 
            maximum_latitude=15.5,
            force_download=True  # Force le rafraîchissement
        )

        if ds is None:
            raise Exception("Le dataset n'a pas pu être chargé (ds est None). Vérifiez vos identifiants Copernicus.")

        # 2. Point GPS (Dakar/Kayar)
        lat_p, lon_p = 14.90, -17.50
        
        # 3. Extraction
        # Note : On utilise 'time' ou 'step' selon le dataset, ici on essaie le dernier index
        data = ds.isel(time=-1).sel(latitude=lat_p, longitude=lon_p, method="nearest")
        
        # Récupération des courants uo et vo
        u_curr = float(data.uo.values)
        v_curr = float(data.vo.values)
        
        vitesse = np.sqrt(u_curr**2 + v_curr**2) * 3.6
        dir_c = "Est ➡️" if u_curr > 0 else "Ouest ⬅️" if abs(u_curr) > abs(v_curr) else "Nord ⬆️" if v_curr > 0 else "Sud ⬇️"

        # 4. Envoi Telegram
        google_maps = f"https://www.google.com/maps?q={lat_p},{lon_p}"
        
        caption = (
            f"{edition} : *SUNU-BLUE-TECH*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 *ZONE DE PÊCHE*\n"
            f"Position: `{lat_p}, {lon_p}`\n\n"
            f"🌊 *INFOS MER*\n"
            f"Direction Courant: {dir_c}\n"
            f"Vitesse: {vitesse:.1f} km/h\n\n"
            f"🔗 [OUVRIR GOOGLE MAPS]({google_maps})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📢 *ABONNEMENT : +221 77 702 08 18*"
        )

        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_ID, "text": caption, "parse_mode": "Markdown"})
        print("✅ Rapport envoyé avec succès !")

    except Exception as e:
        print(f"❌ ERREUR FINALE : {str(e)}")
        # On affiche aussi les secrets pour vérifier s'ils sont vides (sans afficher le mot de passe entier)
        print(f"DEBUG: User={CP_USER}, Pass OK={'OUI' if CP_PASS else 'NON'}")
        raise e

if __name__ == "__main__":
    job()
