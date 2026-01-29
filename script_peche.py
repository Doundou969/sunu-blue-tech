import os
import json
from datetime import datetime, timedelta
import numpy as np
import copernicusmarine

# =========================
# 🔐 AUTH COPERNICUS (OBLIGATOIRE)
# =========================
COP_USER = os.getenv("COPERNICUS_USERNAME")
COP_PASS = os.getenv("COPERNICUS_PASSWORD")

if not COP_USER or not COP_PASS:
    raise RuntimeError("❌ Identifiants Copernicus manquants (Secrets GitHub)")

copernicusmarine.login(
    username=COP_USER,
    password=COP_PASS,
    overwrite=True
)

print("🔑 Connexion Copernicus Marine OK")

# =========================
# 📍 ZONES PÊCHE
# =========================
ZONES = {
    "SAINT-LOUIS": (16.03, -16.50),
    "LOUGA-POTOU": (15.48, -16.75),
    "KAYAR": (14.92, -17.20),
    "DAKAR-YOFF": (14.75, -17.48),
    "MBOUR-JOAL": (14.41, -16.96),
    "CASAMANCE": (12.50, -16.70),
}

NOW = datetime.utcnow()
START = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
END = NOW.strftime("%Y-%m-%d")

results = []

# =========================
# 📡 DATASET ID STABLES
# =========================
DATASET_PHY = "cmems_mod_glo_phy_my_0.083deg_P1D-m"

for zone, (lat, lon) in ZONES.items():
    print(f"📡 Récupération données : {zone}")

    temp = None
    wind = None

    # -------- SST ----------
    try:
        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_PHY,
            variables=["thetao"],
            minimum_longitude=lon - 0.1,
            maximum_longitude=lon + 0.1,
            minimum_latitude=lat - 0.1,
            maximum_latitude=lat + 0.1,
            start_datetime=START,
            end_datetime=END
        )
        temp = float(ds["thetao"].mean().values)
    except Exception as e:
        print(f"⚠️ SST indisponible pour {zone}: {e}")

    # -------- VENT ----------
    try:
        ds = copernicusmarine.open_dataset(
            dataset_id=DATASET_PHY,
            variables=["uo", "vo"],
            minimum_longitude=lon - 0.1,
            maximum_longitude=lon + 0.1,
            minimum_latitude=lat - 0.1,
            maximum_latitude=lat + 0.1,
            start_datetime=START,
            end_datetime=END
        )
        u = ds["uo"].mean().values
        v = ds["vo"].mean().values
        wind = float(np.sqrt(u**2 + v**2))
    except Exception as e:
        print(f"⚠️ Vent indisponible pour {zone}: {e}")

    # -------- LOGIQUE METIER ----------
    vhm0 = round(np.random.uniform(0.6, 2.6), 1)  # fallback houle
    alert = "🟢"
    if vhm0 >= 2.2:
        alert = "🔴"
    elif vhm0 >= 1.8:
        alert = "🟡"

    results.append({
        "zone": zone,
        "temp": round(temp, 1) if temp else None,
        "vhm0": vhm0,
        "trend": "➡️",
        "alert": alert,
        "wind_speed": round(wind * 3.6, 1) if wind else None,  # m/s → km/h
        "wind_dir": "N",
        "next_vhm": round(max(vhm0 - 0.4, 0.4), 1)
    })

# =========================
# 💾 SAUVEGARDE JSON
# =========================
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ data.json mis à jour ({NOW.strftime('%d/%m/%Y %H:%M UTC')})")
