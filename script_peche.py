# ============================================================
# 🌊 SUNU BLUE TECH – COPERNICUS MARINE PIPELINE (CORRIGÉ)
# ============================================================

import copernicusmarine
import xarray as xr
import json
from datetime import datetime, timedelta
import os

# ============================================================
# 🔑 LOGIN COPERNICUS (SANS overwrite ❌)
# ============================================================
print("🔑 Connexion Copernicus Marine...")
copernicusmarine.login()
print("✅ Copernicus connecté")

# ============================================================
# ⏳ GESTION DES DATES (ANTI-ERREUR 2026)
# Les datasets MY ont du retard → on recule volontairement
# ============================================================
NOW = datetime.utcnow()
SAFE_DATE = NOW - timedelta(days=30)

START_DATE = (SAFE_DATE - timedelta(days=1)).strftime("%Y-%m-%d")
END_DATE = SAFE_DATE.strftime("%Y-%m-%d")

# ============================================================
# 📡 DATASET VALIDE (MULTI-YEAR PHYSIQUE)
# ============================================================
DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1D-m"

# ============================================================
# 📍 ZONES DE PÊCHE (SÉNÉGAL)
# ============================================================
ZONES = {
    "SAINT-LOUIS": (-16.5, 16.0),
    "KAYAR": (-17.1, 14.9),
    "DAKAR-YOFF": (-17.5, 14.7),
    "MBOUR-JOAL": (-16.9, 14.4),
    "CASAMANCE": (-16.6, 12.6)
}

# ============================================================
# 🧠 RÉCUPÉRATION DONNÉES
# ============================================================
results = {}

for zone, (lon, lat) in ZONES.items():
    print(f"📡 Récupération données : {zone}")
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

        # Variables standards
        sst = float(ds["thetao"].isel(time=0, depth=0).mean().values)
        uo = float(ds["uo"].isel(time=0, depth=0).mean().values)
        vo = float(ds["vo"].isel(time=0, depth=0).mean().values)

        results[zone] = {
            "sst_celsius": round(sst, 2),
            "courant_u": round(uo, 2),
            "courant_v": round(vo, 2),
            "source": "Copernicus Marine"
        }

    except Exception as e:
        print(f"⚠️ Erreur pour {zone} : {e}")
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

print(f"✅ data.json mis à jour ({output['updated_utc']})")
