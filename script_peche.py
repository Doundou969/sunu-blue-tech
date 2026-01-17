import os
import requests
import copernicusmarine
import datetime
import numpy as np

# --- CONFIGURATION ---
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def send_tg(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_ID, "text": message, "parse_mode": "Markdown"})

def job():
    try:
        print("🔍 Recherche automatique du catalogue...")
        # 1. Lister les datasets disponibles pour éviter l'erreur de nom inexistant
        catalogue = copernicusmarine.list_datasets()
        
        # On cherche le dataset de physique globale (courants) le plus récent
        # Généralement il contient 'cmems_mod_glo_phy_anfc_0.083deg_PT1H-m' ou similaire
        targets = [d for d in catalogue if "glo_phy_anfc" in d and "static" not in d]
        
        if not targets:
            # Si on ne trouve pas avec le mot clé, on prend l'ID historique par défaut
            target_id = "cmems_mod_glo_phy_anfc_0.083deg_PT6H-i"
        else:
            # On prend le premier de la liste (le plus récent)
            target_id = targets[0]
            
        print(f"✅ Utilisation de : {target_id}")

        # 2. Chargement des données
        ds = copernicusmarine.open_dataset(
            dataset_id=target_id,
            username=USER,
            password=PASS,
            minimum_longitude=-18.0, 
            maximum_longitude=-17.0,
            minimum_latitude=14.5, 
            maximum_latitude=15.5
        )

        # 3. Extraction (Dakar/Kayar : 14.9, -17.5)
        # On sélectionne la surface (depth=0) si disponible et le dernier temps
        data = ds.sel(latitude=14.9, longitude=-17.5, method="nearest")
        if 'time' in data.dims:
            data = data.isel(time=-1)
        if 'depth' in data.dims:
            data = data.isel(depth=0)

        # Récupération des courants
        u = float(data.uo.values)
        v = float(data.vo.values)
        vitesse = np.sqrt(u**2 + v**2) * 3.6 # km/h
        
        # Direction
        if abs(u) > abs(v):
            dir_c = "Est ➡️" if u > 0 else "Ouest ⬅️"
        else:
            dir_c = "Nord ⬆️" if v > 0 else "Sud ⬇️"

        # 4. Rapport final
        now = datetime.datetime.now()
        edition = "🌅 MATIN" if now.hour < 12 else "🌙 SOIR"
        
        rapport = (
            f"🚀 *SUNU-BLUE-TECH : {edition}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 *ZONE : DAKAR / KAYAR*\n"
            f"🌊 Courant : {dir_c}\n"
            f"💨 Vitesse : {vitesse:.1f} km/h\n"
            f"📡 Source : {target_id[:15]}...\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚓ *Bonne pêche, Capitaine !*"
        )

        send_tg(rapport)
        print("✅ Terminé avec succès !")

    except Exception as e:
        err = f"❌ Erreur : {str(e)}"
        print(err)
        send_tg(err)

if __name__ == "__main__":
    job()
