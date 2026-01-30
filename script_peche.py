import os
import json
import random
import logging
from datetime import datetime
from dotenv import load_dotenv

# 1. Chargement des variables d'environnement (.env)
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("PecheurConnect")

print("🚀 PecheurConnect démarrage")

# ======================
# CONFIG ZONES (Sénégal)
# ======================
ZONES = {
    "SAINT-LOUIS": (16.03, -16.50),
    "KAYAR": (14.92, -17.20),
    "DAKAR-YOFF": (14.75, -17.48),
    "MBOUR-JOAL": (14.41, -16.96),
    "CASAMANCE": (12.50, -16.70),
    "LOUGA-POTOU": (15.48, -16.75)
}

# ======================
# FONCTION FALLBACK (Données de secours)
# ======================
def generate_fallback(reason="inconnue"):
    print(f"⚠️ Mode secours activé (Raison : {reason})")
    data = []
    for zone, (lat, lon) in ZONES.items():
        vhm0 = round(random.uniform(0.8, 3.2), 2)
        alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"
        data.append({
            "zone": zone,
            "lat": lat,
            "lon": lon,
            "vhm0": vhm0,
            "temp": round(random.uniform(22, 28), 1),
            "wind_speed": random.randint(8, 30),
            "wind_dir": random.choice(["N", "NE", "NW", "W", "SW"]),
            "alert": alert,
            "trend": "↗" if random.random() > 0.5 else "↘",
            "next_vhm": round(vhm0 + random.uniform(-0.5, 0.6), 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fallback"
        })
    return data

# ======================
# CHARGEMENT COPERNICUS
# ======================
def load_marine_data():
    ds = None
    try:
        from copernicusmarine import open_dataset
        import numpy as np

        user = os.getenv("COPERNICUS_USERNAME")
        pwd = os.getenv("COPERNICUS_PASSWORD")

        if user and pwd:
            print(f"🔑 Connexion automatique : {user}")
        else:
            print("🔑 Connexion manuelle (Identifiants .env manquants)")

        # Dataset ID mis à jour pour 2026
        DATASET_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H"

        ds = open_dataset(
            dataset_id=DATASET_ID,
            variables=["VHM0"],
            minimum_longitude=-18.5,
            maximum_longitude=-16.0,
            minimum_latitude=12.0,
            maximum_latitude=17.0,
            username=user,
            password=pwd
        )

        if ds is None:
            return generate_fallback("Dataset vide")

        data = []
        for zone, (lat, lon) in ZONES.items():
            # Sélection temporelle et géographique
            point = ds.sel(latitude=lat, longitude=lon, method="nearest")
            
            # On récupère la donnée la plus récente (time=-1)
            vhm0_raw = point["VHM0"].isel(time=-1).values
            vhm0 = float(vhm0_raw) if not np.isnan(vhm0_raw) else 0.0

            alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"

            data.append({
                "zone": zone,
                "lat": lat,
                "lon": lon,
                "vhm0": round(vhm0, 2),
                "temp": 24.5,
                "wind_speed": 18,
                "wind_dir": "N",
                "alert": alert,
                "trend": "→",
                "next_vhm": round(vhm0 + 0.1, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "copernicus"
            })

        print("✅ Données Copernicus chargées")
        return data

    except Exception as e:
        return generate_fallback(str(e))

# ======================
# NOTIFICATION (Optionnel)
# ======================
def check_telegram():
    if not os.getenv("TELEGRAM_TOKEN"):
        print("⚠️ Telegram non configuré (TOKEN manquant dans le .env)")
    else:
        print("🔔 Service de notification Telegram prêt")

# ======================
# LANCEMENT
# ======================
if __name__ == "__main__":
    # Récupération des données
    results = load_marine_data()

    # Sauvegarde JSON
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("✅ data.json généré")
    check_telegram()
    print("✅ Script terminé")
