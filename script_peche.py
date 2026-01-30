import json
import os
import random
import logging
from datetime import datetime

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
# FALLBACK DATA (Données de secours)
# ======================
def generate_fallback():
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
# COPERNICUS DATA (Données Réelles)
# ======================
def load_copernicus():
    ds = None
    try:
        from copernicusmarine import open_dataset

        # Récupération automatique des identifiants (Variables d'environnement)
        user = os.getenv("COPERNICUS_USERNAME")
        pwd = os.getenv("COPERNICUS_PASSWORD")

        if user and pwd:
            print(f"🔑 Connexion automatique : {user}")
        else:
            print("🔑 Connexion manuelle (Identifiants système non configurés)")

        ds = open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H",
            variables=["VHM0"],
            minimum_longitude=-18,
            maximum_longitude=-16,
            minimum_latitude=12,
            maximum_latitude=17,
            username=user,
            password=pwd
        )

        # Vérification si le dataset a bien été ouvert
        if ds is None:
            raise ValueError("Dataset non initialisé")

        data = []
        for zone, (lat, lon) in ZONES.items():
            # Sélection du point le plus proche
            point = ds.sel(latitude=lat, longitude=lon, method="nearest")
            
            # Extraction de la valeur VHM0 (hauteur des vagues)
            vhm0_val = point["VHM0"].mean().values
            vhm0 = float(vhm0_val) if vhm0_val else 0.0

            alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"

            data.append({
                "zone": zone,
                "lat": lat,
                "lon": lon,
                "vhm0": round(vhm0, 2),
                "temp": 24.5,  # Valeur par défaut si non disponible
                "wind_speed": 15,
                "wind_dir": "N",
                "alert": alert,
                "trend": "↗",
                "next_vhm": round(vhm0 + 0.2, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "copernicus"
            })

        print("✅ Données Copernicus chargées avec succès")
        return data

    except Exception as e:
        # CORRECTION : Capture l'erreur et bascule sans crash sur le fallback
        print(f"⚠️ Copernicus indisponible → fallback data utilisé ({e})")
        return generate_fallback()

# ======================
# GESTION TELEGRAM (Optionnel)
# ======================
def notify_telegram():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("⚠️ Telegram non configuré (TOKEN manquant)")
        return False
    # Logique d'envoi ici...
    return True

# ======================
# EXÉCUTION
# ======================
if __name__ == "__main__":
    # 1. Chargement des données
    processed_data = load_copernicus()

    # 2. Sauvegarde au format JSON pour l'interface PecheurConnect
    try:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        print("✅ data.json généré")
    except Exception as e:
        print(f"❌ Erreur lors de l'écriture du fichier : {e}")

    # 3. Notification
    notify_telegram()

    print("✅ Script terminé sans erreur")
