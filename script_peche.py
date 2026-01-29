# ============================================================
# 🌊 PECHEURCONNECT – COPERNICUS SAFE CI SCRIPT
# ============================================================

import copernicusmarine
import json
import os
from datetime import datetime, timedelta

# ============================================================
# 🔐 DÉTECTION CREDENTIALS (CI SAFE)
# ============================================================
COP_USER = os.getenv("COPERNICUS_MARINE_USERNAME")
COP_PASS = os.getenv("COPERNICUS_MARINE_PASSWORD")

COPERNICUS_OK = False

if COP_USER and COP_PASS:
    try:
        print("🔑 Connexion Copernicus Marine (ENV)...")
        copernicusmarine.login(
            username=COP_USER,
            password=COP_PASS
        )
        COPERNICUS_OK = True
        print("✅ Copernicus connecté")
    except Exception as e:
        print(f"⚠️ Login Copernicus échoué : {e}")
else:
    print("⚠️ Aucun credential Copernicus → mode fallback")

# ============================================================
# ⏳ DATES SÛRES (ANTI BUG 2026)
# ============================================================
NOW = datetime.utcnow()
SAFE_DATE = NOW - timedelta(days=30)

START_DATE = (SAFE_DATE - timedelta(days=1)).strftime("%Y-%m-%d")
END_DATE = SAFE_DATE.strftime("%Y-%m-%d")

# ============================================================
# 📡 DATASET
# ============================================================
DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1D-m"

# ============================================================
# 📍 ZONES PÊCHE SÉNÉGAL
# ============================================================
ZONES = {
    "SAINT-LOUIS": (-16.5, 16.0),
    "KAYAR": (-17.1, 14.9),
    "DAKAR-YOFF": (-17.5, 14.7),
    "MBOUR-JOAL": (-16.9, 14.4),
    "CASAMANCE": (-16.6, 12.6)
}

results = {}

# ============================================================
# 🧠 RÉCUPÉRATION DONNÉES
# ============================================================
for zone, (lon, lat) in ZONES.items():
    print(f"📡 Zone : {zone}")

    if COPERNICUS_OK:
        try:
            ds = copernicusmarine.open_dataset(
                dataset_id=DATASET_ID,
                minimum_longitude=lon - 0.2,
                maximum_longitude=lon + 0.2,
                minimum_latitude=lat - 0.2,
                maximum_latitude=lat + 0.2,
                start_datetime=START_DATE,
                end_datetime=END_DATE,
            )

            sst = float(ds["thetao"].isel(time=0, depth=0).mean().values)
            uo = float(ds["uo"].isel(time=0, depth=0).mean().values)
            vo = float(ds["vo"].isel(time=0, depth=0).mean().values)

            results[zone] = {
                "sst_celsius": round(sst, 2),
                "courant_u": round(uo, 2),
                "courant_v": round(vo, 2),
                "source": "Copernicus Marine"
            }

            continue

        except Exception as e:
            print(f"⚠️ Copernicus KO pour {zone} : {e}")

    # ========================================================
    # 🟡 FALLBACK OFFLINE (ANTI CRASH)
    # ========================================================
    results[zone] = {
        "sst_celsius": None,
        "courant_u": None,
        "courant_v": None,
        "source": "fallback"
    }

# ============================================================
# 💾 EXPORT JSON
# ============================================================
output = {
    "updated_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "start_date": START_DATE,
    "end_date": END_DATE,
    "zones": results
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"✅ data.json généré ({output['updated_utc']})")
