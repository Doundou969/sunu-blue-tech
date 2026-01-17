import xarray as xr
import copernicusmarine
import numpy as np
import requests
import datetime
import os

# --- RÉCUPÉRATION ---
user = os.getenv("COPERNICUS_USERNAME")
pw = os.getenv("COPERNICUS_PASSWORD")
tg_token = os.getenv("TG_TOKEN")
tg_id = os.getenv("TG_ID")

def job():
    try:
        # Vérification immédiate
        if not user or not pw:
            print(f"❌ ERREUR : Les secrets GitHub sont vides !")
            print(f"Vérifiez que vous avez bien nommé COPERNICUS_USERNAME dans GitHub Settings.")
            return

        print(f"🚀 Connexion avec l'utilisateur : {user}")

        # Configurer la session une bonne fois pour toutes
        copernicusmarine.login(username=user, password=pw, force_persist=True)

        # Chargement des données
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT6H-i",
            minimum_longitude=-18.0, 
            maximum_longitude=-17.0,
            minimum_latitude=14.5, 
            maximum_latitude=15.5
        )

        # On prend le dernier point
        data = ds.isel(time=-1).sel(latitude=14.9, longitude=-17.5, method="nearest")
        
        u = float(data.uo.values)
        v = float(data.vo.values)
        vit = np.sqrt(u**2 + v**2) * 3.6
        
        # Envoi simple
        msg = f"✅ SUNU-BLUE-TECH : TEST RÉUSSI !\nVitesse mer : {vit:.1f} km/h"
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        requests.post(url, data={"chat_id": tg_id, "text": msg})
        print("✅ Message envoyé !")

    except Exception as e:
        print(f"❌ ERREUR : {str(e)}")

if __name__ == "__main__":
    job()
