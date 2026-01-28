# ============================================================
# PECHEUR CONNECT 🇸🇳 - Script Copernicus PRO
# Génération data.json FRONT-COMPATIBLE (SST, Houle, Vent)
# ============================================================

import os
import json
import math
import datetime
import warnings
import copernicusmarine
import numpy as np

warnings.filterwarnings("ignore")

# ============================================================
# 🔐 SECRETS (GitHub Actions / ENV)
# ============================================================
TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_ID = os.getenv("TG_ID", "")
COP_USER = os.getenv("COPERNICUS_USERNAME", "")
COP_PASS = os.getenv("COPERNICUS_PASSWORD", "")

# ============================================================
# 📍 ZONES CÔTIÈRES DU SÉNÉGAL (lat_min, lon_min, lat_max, lon_max)
# ============================================================
ZONES = {
    "SAINT-LOUIS":  [15.8, -16.7, 16.2, -16.3],
    "LOUGA-POTOU":  [15.3, -16.9, 15.6, -16.6],
    "KAYAR":        [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF":   [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL":   [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE":    [12.2, -16.9, 12.7, -16.5]
}

# ============================================================
# 🧭 Rose des vents
# ============================================================
def wind_direction(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[int((deg + 22.5) / 45) % 8]

# ============================================================
# 🔹 MAIN
# ============================================================
def main():
    print("🔑 Connexion Copernicus Marine...")
    copernicusmarine.login(username=COP_USER, password=COP_PASS)

    # Historique SST pour tendance
    old_temp = {}
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r") as f:
                old_data = json.load(f)
                for item in old_data:
                    old_temp[item["zone"]] = item["temp"]
        except:
            pass

    results = []
    now = datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
    day = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    for zone, coords in ZONES.items():
        lat_min, lon_min, lat_max, lon_max = coords

        # ------------------------------
        # SST + Courants (thetao, uo, vo)
        # ------------------------------
        try:
            sst_data = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_phy-anfc_0.083deg_P1D-m",
                variables=["thetao","uo","vo"],
                minimum_longitude=lon_min,
                maximum_longitude=lon_max,
                minimum_latitude=lat_min,
                maximum_latitude=lat_max,
                start_datetime=f"{day}T00:00:00Z",
                end_datetime=f"{day}T23:59:59Z"
            )
            temp = float(np.mean(sst_data["thetao"]))
            wind_u = float(np.mean(sst_data["uo"]))
            wind_v = float(np.mean(sst_data["vo"]))
            wind_speed = round(math.sqrt(wind_u**2 + wind_v**2),1)
            wind_dir = wind_direction(wind_u, wind_v)
        except Exception as e:
            print(f"⚠️ Erreur SST/Vent pour {zone} : {e}")
            temp = 0.0
            wind_speed = 0.0
            wind_dir = "N"

        # ------------------------------
        # Houle / VHM0
        # ------------------------------
        try:
            wave_data = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                variables=["VHM0"],
                minimum_longitude=lon_min,
                maximum_longitude=lon_max,
                minimum_latitude=lat_min,
                maximum_latitude=lat_max,
                start_datetime=f"{day}T00:00:00Z",
                end_datetime=f"{day}T23:59:59Z"
            )
            vhm0 = round(float(np.mean(wave_data["VHM0"])),1)
        except Exception as e:
            print(f"⚠️ Erreur Houle pour {zone} : {e}")
            vhm0 = 0.0

        # ------------------------------
        # Tendance SST
        # ------------------------------
        trend = "➡️"
        if zone in old_temp:
            if temp > old_temp[zone] + 0.2:
                trend = "📈"
            elif temp < old_temp[zone] - 0.2:
                trend = "📉"

        # ------------------------------
        # Alertes houle
        # ------------------------------
        if vhm0 >= 2.2:
            alert = "🔴"
        elif vhm0 >= 1.5:
            alert = "🟠"
        else:
            alert = "🟢"

        # ------------------------------
        # Prévision simple (demain) – estimation locale
        # ------------------------------
        next_vhm = round(vhm0 * 0.8,1)  # simple facteur correctif

        # ------------------------------
        # Résultat final pour la zone
        # ------------------------------
        results.append({
            "zone": zone,
            "temp": round(temp,1),
            "vhm0": vhm0,
            "trend": trend,
            "alert": alert,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir,
            "next_vhm": next_vhm
        })

    # ------------------------------
    # Écriture data.json
    # ------------------------------
    with open("data.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ data.json mis à jour ({now})")

# ============================================================
# 🔹 EXECUTION
# ============================================================
if __name__ == "__main__":
    main()
