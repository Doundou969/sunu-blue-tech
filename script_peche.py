import os
import requests
import copernicusmarine
import datetime
import numpy as np

# --- RÉCUPÉRATION DES SECRETS ---
user = os.getenv("COPERNICUS_USERNAME")
pw = os.getenv("COPERNICUS_PASSWORD")
tg_token = os.getenv("TG_TOKEN")
tg_id = os.getenv("TG_ID")

def send_tg(message):
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    requests.post(url, data={"chat_id": tg_id, "text": message, "parse_mode": "Markdown"})

def job():
    try:
        print(f"🚀 Connexion Copernicus pour {user}...")
        
        # 1. CONNEXION SIMPLIFIÉE
        # On passe les identifiants directement dans open_dataset
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT6H-i",
            username=user,
            password=pw,
            minimum_longitude=-18.0, 
            maximum_longitude=-17.0,
            minimum_latitude=14.5, 
            maximum_latitude=15.5
        )

        # 2. EXTRACTION DES DONNÉES (Dakar/Kayar)
        # On récupère le dernier temps disponible
        data = ds.isel(time=-1).sel(latitude=14.9, longitude=-17.5, method="nearest")
        
        # Courants (uo = Est/Ouest, vo = Nord/Sud)
        u = float(data.uo.values)
        v = float(data.vo.values)
        
        # Calcul de la vitesse en km/h
        vitesse = np.sqrt(u**2 + v**2) * 3.6
        
        # Direction du courant
        if abs(u) > abs(v):
            dir_c = "Est ➡️" if u > 0 else "Ouest ⬅️"
        else:
            dir_c = "Nord ⬆️" if v > 0 else "Sud ⬇️"

        # 3. PRÉPARATION DU MESSAGE
        now = datetime.datetime.now()
        edition = "🌅 MATIN" if now.hour < 12 else "🌙 SOIR"
        
        rapport = (
            f"🚀 *SUNU-BLUE-TECH : {edition}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 *ZONE : DAKAR / KAYAR*\n"
            f"🌊 Courant : {dir_c}\n"
            f"💨 Vitesse : {vitesse:.1f} km/h\n"
            f"🛰️ État : Opérationnel\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚓ *Bonne pêche aux Capitaines !*"
        )

        # 4. ENVOI
        send_tg(rapport)
        print("✅ Rapport envoyé avec succès !")

    except Exception as e:
        error_msg = f"❌ Erreur technique : {str(e)}"
        print(error_msg)
        send_tg(error_msg)

if __name__ == "__main__":
    job()
