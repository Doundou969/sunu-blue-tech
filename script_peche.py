import os
import json
import random
import logging
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# 1. Chargement des accès (Copernicus & GitHub)
load_dotenv()

# Config Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
print("🚀 PecheurConnect démarrage...")

# ======================
# CONFIG ZONES
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
# MODE SECOURS
# ======================
def generate_fallback(reason="inconnue"):
    print(f"⚠️ Utilisation du fallback (Raison : {reason})")
    data = []
    for zone, (lat, lon) in ZONES.items():
        vhm0 = round(random.uniform(0.8, 3.2), 2)
        data.append({
            "zone": zone, "lat": lat, "lon": lon, "vhm0": vhm0,
            "temp": round(random.uniform(22, 28), 1),
            "wind_speed": random.randint(8, 30), "wind_dir": random.choice(["N", "NE", "NW"]),
            "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
            "trend": "↗", "next_vhm": round(vhm0 + 0.1, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z", "source": "fallback"
        })
    return data

# ======================
# RÉCUPÉRATION COPERNICUS
# ======================
def load_marine_data():
    try:
        from copernicusmarine import open_dataset
        import numpy as np

        user = os.getenv("COPERNICUS_USERNAME")
        pwd = os.getenv("COPERNICUS_PASSWORD")
        DATASET_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H"

        ds = open_dataset(
            dataset_id=DATASET_ID,
            variables=["VHM0"],
            minimum_longitude=-18.5, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0,
            username=user, password=pwd
        )

        if ds is None: return generate_fallback("Dataset vide")

        data = []
        for zone, (lat, lon) in ZONES.items():
            point = ds.sel(latitude=lat, longitude=lon, method="nearest")
            vhm0_raw = point["VHM0"].isel(time=-1).values
            vhm0 = float(vhm0_raw) if not np.isnan(vhm0_raw) else 0.0

            data.append({
                "zone": zone, "lat": lat, "lon": lon, "vhm0": round(vhm0, 2),
                "temp": 24.5, "wind_speed": 15, "wind_dir": "N",
                "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                "trend": "→", "next_vhm": round(vhm0 + 0.2, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z", "source": "copernicus"
            })
        print("✅ Données Copernicus récupérées")
        return data

    except Exception as e:
        return generate_fallback(str(e))

# ======================
# AUTOMATISATION GITHUB
# ======================
def push_to_github():
    try:
        print("📤 Envoi vers GitHub Pages...")
        subprocess.run(["git", "add", "data.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update marine data"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("🚀 Site web mis à jour !")
    except Exception as e:
        print(f"❌ Erreur Git : {e} (Assurez-vous que Git est installé et configuré)")

# ======================
# EXECUTION
# ======================
if __name__ == "__main__":
    # 1. Obtenir les données
    final_data = load_marine_data()

    # 2. Sauvegarder le JSON localement
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    print("✅ data.json généré")

    # 3. Mettre en ligne (Optionnel, décommentez si Git est prêt)
    # push_to_github()

    print("✅ Script terminé")
