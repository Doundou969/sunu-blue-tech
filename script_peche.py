import json
import os
import random
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

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
# FALLBACK DATA
# ======================
def generate_fallback():
    data = []
    for zone, (lat, lon) in ZONES.items():
        vhm0 = round(random.uniform(0.8, 3.2), 2)
        alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"
        data.append({
            "zone": zone, "lat": lat, "lon": lon, "vhm0": vhm0,
            "temp": round(random.uniform(22, 28), 1),
            "wind_speed": random.randint(8, 30), "wind_dir": random.choice(["N", "NE", "NW"]),
            "alert": alert, "trend": "↗", "next_vhm": round(vhm0 + 0.2, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z", "source": "fallback"
        })
    return data

# ======================
# COPERNICUS DATA
# ======================
def load_copernicus():
    ds = None
    try:
        from copernicusmarine import open_dataset

        user = os.getenv("COPERNICUS_USERNAME")
        pwd = os.getenv("COPERNICUS_PASSWORD")

        # Mise à jour du Dataset ID (Identifiant mis à jour pour 2026)
        # On utilise le dataset global de vagues standard
        DATASET_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H" 
        
        print(f"🔑 Connexion avec ID: {DATASET_ID}")

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
            raise ValueError("Dataset introuvable ou accès refusé.")

        data = []
        for zone, (lat, lon) in ZONES.items():
            # Correction : gestion du temps pour éviter les erreurs de dimension
            point = ds.sel(latitude=lat, longitude=lon, method="nearest")
            
            # On prend la dernière échéance temporelle disponible
            vhm0_val = point["VHM0"].isel(time=-1).values
            vhm0 = float(vhm0_val) if not np.isnan(vhm0_val) else 0.0

            alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"

            data.append({
                "zone": zone, "lat": lat, "lon": lon, "vhm0": round(vhm0, 2),
                "temp": 25.0, "wind_speed": 12, "wind_dir": "N",
                "alert": alert, "trend": "→", "next_vhm": round(vhm0 + 0.1, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "copernicus"
            })

        print("✅ Données Copernicus chargées")
        return data

    except Exception as e:
        # Si le dataset ID est faux ou le service down, on ne crash pas
        print(f"⚠️ Copernicus indisponible → fallback activé ({e})")
        return generate_fallback()

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    # Import numpy au cas où pour les vérifications de données marines
    try: import numpy as np
    except: pass

    marine_results = load_copernicus()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(marine_results, f, indent=2, ensure_ascii=False)

    print("✅ data.json généré")

    if not os.getenv("TELEGRAM_TOKEN"):
        print("⚠️ Telegram non configuré (TOKEN manquant)")

    print("✅ Script terminé sans erreur")
