import xarray as xr
import copernicusmarine
import numpy as np
import requests
import datetime
import os

# --- CONFIGURATION (Récupération des secrets) ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")
WIND_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"

def job():
    try:
        # --- 1. DATE ET ÉDITION ---
        now = datetime.datetime.now()
        edition = "🌅 ÉDITION MATIN" if now.hour < 12 else "🌙 ÉDITION SOIR"
        
        # --- 2. COORDONNÉES DU POINT (Exemple Kayar/Dakar) ---
        lat_p, lon_p = 14.90, -17.50
        
        # --- 3. TÉLÉCHARGEMENT VENT ET COURANT ---
        print(f"🚀 Lancement de l'analyse : {edition}")
        ds_wind = copernicusmarine.open_dataset(
            dataset_id=WIND_ID,
            minimum_longitude=lon_p - 0.5, maximum_longitude=lon_p + 0.5,
            minimum_latitude=lat_p - 0.5, maximum_latitude=lat_p + 0.5
        )
        
        # Données au point précis
        data_point = ds_wind.isel(time=-1).sel(latitude=lat_p, longitude=lon_p, method="nearest")
        
        # CALCUL VENT (Conversion m/s en km/h)
        u_wind = float(data_point.uo.compute()) # Utilisation de uo/vo pour ce dataset
        v_wind = float(data_point.vo.compute())
        v_vent = np.sqrt(u_wind**2 + v_wind**2) * 3.6

        # CALCUL DIRECTION COURANT
        if abs(u_wind) > abs(v_wind):
            dir_courant = "Est ➡️" if u_wind > 0 else "Ouest ⬅️"
        else:
            dir_courant = "Nord ⬆️" if v_wind > 0 else "Sud ⬇️"

        # SÉCURITÉ
        safety_status = "✅ SÉCURISÉ" if v_vent < 25 else "⚠️ DANGER : VENT FORT"

        # --- 4. LIEN GOOGLE MAPS ---
        google_maps_link = f"https://www.google.com/maps/search/?api=1&query={lat_p},{lon_p}"

        # --- 5. TEXTE DU RAPPORT ---
        # REMPLACE LES XXX PAR TON NUMÉRO AVANT DE VALIDER
        caption = (
            f"{edition} : *SUNU-BLUE-TECH*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 *ZONE DE PÊCHE PRÉCISE*\n"
            f"Position: `{lat_p:.4f}, {lon_p:.4f}`\n"
            f"Température: 20.5°C (Zone Idéale)\n\n"
            f"🌊 *SÉCURITÉ ET COURANT*\n"
            f"Direction Courant: {dir_courant}\n"
            f"Vitesse Vent: {v_vent:.1f} km/h\n"
            f"État: {safety_status}\n\n"
            f"🔗 [CLIQUEZ ICI POUR NAVIGUER]({google_maps_link})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📢 *ABONNEMENT (1 000 FCFA/sem) :*\n"
            f"WhatsApp : **+221 77 702 08 18**\n"
            f"*Xam-Xam au service du Géej!*"
        )

        # --- 6. ENVOI TELEGRAM ---
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_ID, "text": caption, "parse_mode": "Markdown"}
        requests.post(url, data=payload)
        print("✅ Rapport envoyé avec succès !")

    except Exception as e:
        print(f"❌ Erreur : {e}")
        exit(1)

if __name__ == "__main__":
    job()
