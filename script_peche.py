import xarray as xr
import copernicusmarine
import numpy as np
import requests
import datetime
import os

# --- CONFIGURATION (Récupération des secrets) ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")
CP_USER = os.getenv("COPERNICUS_USERNAME")
CP_PASS = os.getenv("COPERNICUS_PASSWORD")
WIND_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"

def job():
    try:
        # --- 1. DATE ET ÉDITION ---
        now = datetime.datetime.now()
        edition = "🌅 ÉDITION MATIN" if now.hour < 12 else "🌙 ÉDITION SOIR"
        
        # --- 2. CONNEXION ET TÉLÉCHARGEMENT ---
        print(f"🚀 Connexion Copernicus pour : {edition}")
        
        # On force la connexion avec les secrets
        ds = copernicusmarine.open_dataset(
            dataset_id=WIND_ID,
            username=CP_USER,
            password=CP_PASS,
            minimum_longitude=-18.0, maximum_longitude=-17.0,
            minimum_latitude=14.5, maximum_latitude=15.5
        )
        
        # Coordonnées du point (Dakar/Kayar)
        lat_p, lon_p = 14.90, -17.50
        
        # Extraction des données
        data_point = ds.isel(time=-1).sel(latitude=lat_p, longitude=lon_p, method="nearest")
        
        # CALCUL VENT ET COURANT (uo et vo sont les vecteurs courants/vent dans ce dataset)
        u = float(data_point.uo.compute())
        v = float(data_point.vo.compute())
        v_vitesse = np.sqrt(u**2 + v**2) * 3.6

        # CALCUL DIRECTION
        if abs(u) > abs(v):
            dir_c = "Est ➡️" if u > 0 else "Ouest ⬅️"
        else:
            dir_c = "Nord ⬆️" if v > 0 else "Sud ⬇️"

        safety = "✅ SÉCURISÉ" if v_vitesse < 25 else "⚠️ PRUDENCE : VENT FORT"

        # --- 3. TEXTE DU RAPPORT ---
        google_maps = f"https://www.google.com/maps?q={lat_p},{lon_p}"
        
        caption = (
            f"{edition} : *SUNU-BLUE-TECH*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 *ZONE DE PÊCHE PRÉCISE*\n"
            f"Position: `{lat_p:.4f}, {lon_p:.4f}`\n\n"
            f"🌊 *SÉCURITÉ ET COURANT*\n"
            f"Direction Courant: {dir_c}\n"
            f"Vitesse Vent: {v_vitesse:.1f} km/h\n"
            f"État: {safety}\n\n"
            f"🔗 [OUVRIR GOOGLE MAPS]({google_maps})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📢 *ABONNEMENT (1 000 FCFA/sem) :*\n"
            f"WhatsApp : **+221 77702 08 18**\n"
            f"*Xam-Xam au service du Géej!*"
        )

        # --- 4. ENVOI TELEGRAM ---
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_ID, "text": caption, "parse_mode": "Markdown"})
        print("✅ Rapport envoyé avec succès !")

    except Exception as e:
        print(f"❌ Erreur détectée : {e}")
        exit(1)

if __name__ == "__main__":
    job()
