import copernicusmarine
import json
from datetime import datetime, timedelta
import numpy as np

# =========================
# CONFIG
# =========================
SST_DATASET = "cmems_obs-sst_glo_phy_l3s_gir_P1D-m"
WIND_DATASET = "cmems_obs-wind_glo_phy_nrt_l3-hy2b-hscat-asc-0.25deg_P1D-i"

OUTPUT_FILE = "data.json"

ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.50},
    "KAYAR": {"lat": 14.92, "lon": -17.12},
    "DAKAR-YOFF": {"lat": 14.73, "lon": -17.49},
    "MBOUR-JOAL": {"lat": 14.15, "lon": -16.85},
    "CASAMANCE": {"lat": 12.55, "lon": -16.75}
}

TODAY = datetime.utcnow().date()
YESTERDAY = TODAY - timedelta(days=1)

# =========================
# UTILS
# =========================
def safe_mean(data):
    try:
        return float(np.nanmean(data))
    except:
        return None

def classify_zone(sst, wind):
    if sst is None or wind is None:
        return "NO_DATA", "⚠️ Données indisponibles"

    if sst < 24 and wind > 8:
        return "UPWELLING", "📉 Ndox mu nànd (zone poissonneuse)"
    if wind > 12:
        return "DANGER", "🔴 Buleen dugg (mer dangereuse)"
    return "GOOD", "🟢 Jàmm (conditions favorables)"

# =========================
# MAIN
# =========================
def main():
    print("🔑 Connexion Copernicus Marine...")

    result = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "Copernicus Marine Service",
        "zones": []
    }

    for zone, coord in ZONES.items():
        lat = coord["lat"]
        lon = coord["lon"]

        print(f"📡 Récupération données : {zone}")

        sst_value = None
        wind_value = None

        # ---- SST ----
        try:
            sst = copernicusmarine.open_dataset(
                dataset_id=SST_DATASET,
                variables=["analysed_sst"],
                minimum_longitude=lon - 0.25,
                maximum_longitude=lon + 0.25,
                minimum_latitude=lat - 0.25,
                maximum_latitude=lat + 0.25,
                start_datetime=str(YESTERDAY),
                end_datetime=str(TODAY)
            )
            sst_value = safe_mean(sst["analysed_sst"].values) - 273.15
        except Exception as e:
            print(f"⚠️ SST indisponible pour {zone}: {e}")

        # ---- WIND ----
        try:
            wind = copernicusmarine.open_dataset(
                dataset_id=WIND_DATASET,
                variables=["wind_speed"],
                minimum_longitude=lon - 0.25,
                maximum_longitude=lon + 0.25,
                minimum_latitude=lat - 0.25,
                maximum_latitude=lat + 0.25,
                start_datetime=str(YESTERDAY),
                end_datetime=str(TODAY)
            )
            wind_value = safe_mean(wind["wind_speed"].values)
        except Exception as e:
            print(f"⚠️ Vent indisponible pour {zone}: {e}")

        status, message = classify_zone(sst_value, wind_value)

        result["zones"].append({
            "name": zone,
            "lat": lat,
            "lon": lon,
            "sst_c": round(sst_value, 2) if sst_value else None,
            "wind_ms": round(wind_value, 2) if wind_value else None,
            "status": status,
            "message": message
        })

    # ---- SAVE JSON ----
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ {OUTPUT_FILE} mis à jour ({datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')})")

if __name__ == "__main__":
    main()
