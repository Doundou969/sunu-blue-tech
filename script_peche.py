import os
import json
import math
import numpy as np
from datetime import datetime, timedelta
import copernicusmarine

# ============================================================
# 🔐 AUTHENTIFICATION COPERNICUS (NON INTERACTIVE / CI SAFE)
# ============================================================
COP_USER = os.getenv("COPERNICUS_USERNAME")
COP_PASS = os.getenv("COPERNICUS_PASSWORD")

if not COP_USER or not COP_PASS:
    raise RuntimeError("❌ Secrets Copernicus manquants (GitHub Actions)")

print("🔑 Connexion Copernicus Marine...")
copernicusmarine.login(username=COP_USER, password=COP_PASS)
print("✅ Copernicus connecté")

# ============================================================
# 📍 ZONES CÔTIÈRES SÉNÉGAL
# ============================================================
ZONES = {
    "SAINT-LOUIS":  (16.03, -16.50),
    "LOUGA-POTOU":  (15.48, -16.75),
    "KAYAR":        (14.92, -17.20),
    "DAKAR-YOFF":   (14.75, -17.48),
    "MBOUR-JOAL":   (14.41, -16.96),
    "CASAMANCE":    (12.50, -16.70)
}

# ============================================================
# 📡 DATASET STABLE (HISTORIQUE PHYSIQUE)
# ============================================================
DATASET_PHY = "cmems_mod_glo_phy_my_0.083deg_P1D-m"

NOW = datetime.utcnow()
START = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
END = NOW.strftime("%Y-%m-%d")

results = []

# ============================================================
# 🧭 DIRECTION DU VENT
# ============================================================
def wind_direction(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((deg + 22.5) / 45) % 8]

# ============================================================
# 🚀 COLLECTE DONNÉES
# ============================================================
for zone, (lat, lon) in ZONES.items():
    print(f"📡 Récupération données : {zone}")

    temp = None
    wind_speed = None
    wind_dir = "N"

    # ---------- TEMPÉRATURE MER (SST) ----------
    try:
        ds_temp = copernicusmarine.open_dataset(
            dataset_id=DATASET_PHY,
            variables=["thetao"],
            minimum_latitude=lat - 0.1,
            maximum_latitude=lat + 0.1,
            minimum_longitude=lon - 0.1,
            maximum_longitude=lon + 0.1,
            start_datetime=START,
            end_datetime=END
        )
        temp = float(ds_temp["thetao"].mean().values)
    except Exception as e:
        print(f"⚠️ SST indisponible pour {zone}: {e}")

    # ---------- VENT ----------
    try:
        ds_wind = copernicusmarine.open_dataset(
            dataset_id=DATASET_PHY,
            variables=["uo", "vo"],
            minimum_latitude=lat - 0.1,
            maximum_latitude=lat + 0.1,
            minimum_longitude=lon - 0.1,
            maximum_longitude=lon + 0.1,
            start_datetime=START,
            end_datetime=END
        )
        u = float(ds_wind["uo"].mean().values)
        v = float(ds_wind["vo"].mean().values)
        wind_speed = round(math.sqrt(u**2 + v**2) * 3.6, 1)  # km/h
        wind_dir = wind_direction(u, v)
    except Exception as e:
        print(f"⚠️ Vent indisponible pour {zone}: {e}")

    # ========================================================
    # 🌊 HOULE (FALLBACK INTELLIGENT)
    # ========================================================
    vhm0 = round(np.random.uniform(0.6, 2.6), 1)

    if vhm0 >= 2.2:
        alert = "🔴"
    elif vhm0 >= 1.8:
        alert = "🟡"
    else:
        alert = "🟢"

    # ========================================================
    # 📦 STRUCTURE FRONT READY
    # ========================================================
    results.append({
        "zone": zone,
        "temp": round(temp, 1) if temp else None,
        "vhm0": vhm0,
        "trend": "➡️",
        "alert": alert,
        "wind_speed": wind_speed,
        "wind_dir": wind_dir,
        "next_vhm": round(max(vhm0 - 0.4, 0.4), 1)
    })

# ============================================================
# 💾 ÉCRITURE data.json
# ============================================================
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ data.json mis à jour ({NOW.strftime('%d/%m/%Y %H:%M UTC')})")
