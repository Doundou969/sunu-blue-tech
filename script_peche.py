# ============================================================
# PECHEUR CONNECT 🇸🇳
# Script Copernicus PRO – data.json FRONT-COMPATIBLE
# ============================================================

import os, json, math, datetime, warnings
import copernicusmarine
import numpy as np

warnings.filterwarnings("ignore")

# ============================================================
# 🔐 SECRETS
# ============================================================
COP_USER = os.getenv("COPERNICUS_USERNAME", "")
COP_PASS = os.getenv("COPERNICUS_PASSWORD", "")

# ============================================================
# 📍 ZONES CÔTIÈRES DU SÉNÉGAL
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
# 🧭 Direction du vent
# ============================================================
def wind_direction(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[int((deg + 22.5) / 45) % 8]

# ============================================================
# 🌊 Évaluation risque mer
# ============================================================
def sea_risk(wind_speed):
    if wind_speed < 6:
        return "VERT"
    elif wind_speed < 10:
        return "ORANGE"
    else:
        return "ROUGE"

# ============================================================
# 🐟 Potentiel pêche (proxy plancton)
# ============================================================
def fishing_potential(temp, wind_speed):
    if 22 <= temp <= 27 and wind_speed < 8:
        return "EXCELLENT"
    elif 20 <= temp <= 29:
        return "BON"
    else:
        return "FAIBLE"

# ============================================================
# 🚀 MAIN
# ============================================================
def main():
    print("🔑 Connexion Copernicus Marine...")
    copernicusmarine.login(username=COP_USER, password=COP_PASS)

    now = datetime.datetime.utcnow()
    date_str = now.strftime("%d/%m/%Y %H:%M UTC")
    day = now.strftime("%Y-%m-%d")

    # Historique température
    old_temp = {}
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r") as f:
                for z in json.load(f):
                    old_temp[z["zone"]] = z["sst"]
        except:
            pass

    results = []

    for zone, box in ZONES.items():
        lat_min, lon_min, lat_max, lon_max = box

        data = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy_my_0.083_P1D-m",
            variables=["thetao", "uo", "vo"],
            minimum_longitude=lon_min,
            maximum_longitude=lon_max,
            minimum_latitude=lat_min,
            maximum_latitude=lat_max,
            start_datetime=f"{day}T00:00:00",
            end_datetime=f"{day}T23:59:59"
        )

        temp = float(np.nanmean(data["thetao"].values))
        u = float(np.nanmean(data["uo"].values))
        v = float(np.nanmean(data["vo"].values))

        wind_speed = round(math.sqrt(u**2 + v**2) * 3.6, 1)  # m/s → km/h
        direction = wind_direction(u, v)

        trend = "STABLE"
        if zone in old_temp:
            if temp > old_temp[zone] + 0.3:
                trend = "📈 CHAUD"
            elif temp < old_temp[zone] - 0.3:
                trend = "📉 FROID"

        results.append({
            "zone": zone,
            "date": date_str,
            "sst": round(temp, 1),
            "tendance": trend,
            "vent_kmh": wind_speed,
            "vent_direction": direction,
            "risque_mer": sea_risk(wind_speed),
            "potentiel_peche": fishing_potential(temp, wind_speed)
        })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("✅ data.json généré avec succès")

# ============================================================
if __name__ == "__main__":
    main()
