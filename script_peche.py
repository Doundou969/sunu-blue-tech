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
        print("🚀 Récupération des données maritimes...")
        
        DATASET_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"

        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_ID,
            username=USER,
            password=PASS,
            minimum_longitude=-17.6, 
            maximum_longitude=-17.4,
            minimum_latitude=14.8, 
            maximum_latitude=15.0
        )

        # Extraction point Dakar/Kayar (14.9N, -17.5W)
        # On force la sélection sur un seul point, un seul temps, une seule profondeur
        data = ds.sel(latitude=14.9, longitude=-17.5, method="nearest")
        
        if 'time' in data.dims:
            data = data.isel(time=-1)
        if 'depth' in data.dims:
            data = data.isel(depth=0)

        # On utilise .values.flatten()[0] pour être SÛR de n'avoir qu'un seul chiffre
        u = float(np.array(data.uo.values).flatten()[0])
        v = float(np.array(data.vo.values).flatten()[0])
        
        vitesse = np.sqrt(u**2 + v**2) * 3.6 # km/h
        
        if abs(u) > abs(v):
            dir_c = "Vers l'Est ➡️" if u > 0 else "Vers l'Ouest ⬅️"
        else:
            dir_c = "Vers le Nord ⬆️" if v > 0 else "Vers le Sud ⬇️"

        etat_mer = "✅ CALME" if vitesse < 15 else "⚠️ AGITÉE" if vitesse < 25 else "🛑 DANGER"

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
            f"⚓ *Xam-Xam au service du Géej !*"
        )

        send_tg(rapport)
        print("✅ Rapport envoyé avec succès !")

    except Exception as e:
        send_tg(f"❌ *Erreur technique :* \n`{str(e)}`")

if __name__ == "__main__":
    job()
