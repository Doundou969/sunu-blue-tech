import os
import json
import xarray as xr
import numpy as np
from datetime import datetime
import copernicusmarine
import sys

# -------------------------
# CONFIG
# -------------------------
ZONE = "Grande Côte – Sénégal"
OUT_FILE = "chl.nc"

DATASET_CHL = "cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1D"

# -------------------------
def abort(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def normalize(value, vmin, vmax):
    return max(0, min(1, (value - vmin) / (vmax - vmin)))

def etat_zone(score):
    if score >= 0.7:
        return "🟢 Favorable"
    elif score >= 0.4:
        return "🟠 Moyen"
    else:
        return "🔴 Faible"

# -------------------------
def main():
    print("🔑 Connexion Copernicus Marine (CI-safe mode)")

    username = os.getenv("COPERNICUS_USERNAME")
    password = os.getenv("COPERNICUS_PASSWORD")

    if not username or not password:
        abort("Secrets Copernicus absents")

    # 🔒 Empêche TOUT prompt
    os.environ["COPERNICUSMARINE_DISABLE_INTERACTIVE"] = "true"
    os.environ["COPERNICUSMARINE_USERNAME"] = username
    os.environ["COPERNICUSMARINE_PASSWORD"] = password

    # -------------------------
    # DOWNLOAD CHL VIA SUBSET
    # -------------------------
    print("⬇️ Téléchargement chlorophylle…")

    copernicusmarine.subset(
        dataset_id=DATASET_CHL,
        variables=["CHL"],
        minimum_longitude=-20,
        maximum_longitude=-10,
        minimum_latitude=10,
        maximum_latitude=17,
        start_datetime="2026-01-01",
        end_datetime="2026-01-10",
        output_filename=OUT_FILE,
        output_directory="."
    )

    if not os.path.exists(OUT_FILE):
        abort("Fichier NetCDF non généré")

    # -------------------------
    # LECTURE NETCDF
    # -------------------------
    ds = xr.open_dataset(OUT_FILE)

    if "CHL" not in ds:
        abort("Variable CHL absente")

    chl = float(ds["CHL"].mean().values)

    # -------------------------
    # SCORE SIMPLE (CHL ONLY – STABLE)
    # -------------------------
    chl_n = normalize(chl, 0.1, 2.0)
    score = round(chl_n, 2)

    result = {
        "zone": ZONE,
        "date": datetime.utcnow().isoformat() + "Z",
        "chlorophylle_mg_m3": round(chl, 3),
        "score_peche": score,
        "etat": etat_zone(score)
    }

    # -------------------------
    # SAVE JSON
    # -------------------------
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("✅ data.json généré")
    print(result)

# -------------------------
if __name__ == "__main__":
    main()
