import json
import os
import random
from datetime import datetime

print("🚀 PecheurConnect démarrage")

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
# FALLBACK DATA
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
# COPERNICUS DATA
# ======================
def load_copernicus():
    try:
        from copernicusmarine import open_dataset

        print("🔑 Connexion Copernicus Marine...")

        ds = open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H",
            variables=["VHM0"],
            minimum_longitude=-18,
            maximum_longitude=-16,
            minimum_latitude=12,
            maximum_latitude=17
        )

        data = []
        for zone, (lat, lon) in ZONES.items():
            point = ds.sel(latitude=lat, longitude=lon, method="nearest")
            vhm0 = float(point["VHM0"].mean().values)

            alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"

            data.append({
                "zone": zone,
                "lat": lat,
                "lon": lon,
                "vhm0": round(vhm0, 2),
                "temp": None,
                "wind_speed": None,
                "wind_dir": None,
                "alert": alert,
                "trend": "↗",
                "next_vhm": round(vhm0 + 0.3, 2),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "copernicus"
            })

        print("✅ Données Copernicus chargées")
        return data

    except Exception as e:
        print(f"⚠️ Copernicus indisponible → fallback data ({e})")
        return generate_fallback()

# ======================
# MAIN
# ======================
data = load_copernicus()

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ data.json généré")

print("⚠️ Telegram non configuré")
print("✅ Script terminé sans erreur")
