# ============================================================
# PECHEUR CONNECT 🇸🇳
# Script Copernicus PRO – Génération data.json FRONT-COMPATIBLE
# ============================================================

import os
import json
import math
import datetime
import warnings
import requests
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
# 📍 ZONES CÔTIÈRES DU SÉNÉGAL
# lat_min, lon_min, lat_max, lon_max
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
# 🧭 Direction vent (rose des vents)
# ============================================================
def wind_direction(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[int((deg + 22.5) / 45) % 8]

# ============================================================
# 🚀 MAIN
# ============================================================
def main():
    print("🔑 Connexion Copernicus Marine...")
    copernicusmarine.login(username=COP_USER, password=COP_PASS)

    # Historique SST (pour calcul tendance 📉📈)
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
    telegram_report = f"🌊 <b>PECHEUR CONNECT 🇸🇳</b>\n📅 {now}\n\n"

    for zone, b in ZONES.items():
        print(f"📡 Analyse satellite : {zone}")

        try:
            # =========================
            # 🌡️ TEMPÉRATURE DE SURFACE
            # =========================
            ds_t = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
                minimum_latitude=b[0], maximum_latitude=b[2],
                minimum_longitude=b[1], maximum_longitude=b[3],
                variables=["thetao"]
            )
            raw = float(ds_t["thetao"].isel(time=-1, depth=0).mean())
            temp = round(raw - 273.15, 1) if raw > 100 else round(raw, 1)

            # =========================
            # 🌊 HOULE SIGNIFICATIVE
            # =========================
            ds_w = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                minimum_latitude=b[0], maximum_latitude=b[2],
                minimum_longitude=b[1], maximum_longitude=b[3],
                variables=["VHM0"]
            )
            vhm0 = round(float(ds_w["VHM0"].isel(time=-1).mean()), 1)
            next_vhm = round(float(ds_w["VHM0"].isel(time=-8).mean()), 1)

            # =========================
            # 🌬️ COURANTS (vent marin)
            # =========================
            ds_c = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                minimum_latitude=b[0], maximum_latitude=b[2],
                minimum_longitude=b[1], maximum_longitude=b[3],
                variables=["uo", "vo"]
            )
            u = float(ds_c["uo"].isel(time=-1, depth=0).mean())
            v = float(ds_c["vo"].isel(time=-1, depth=0).mean())
            wind_speed = round(math.sqrt(u*u + v*v) * 3.6, 1)
            wind_dir = wind_direction(u, v)

        except Exception as e:
            print(f"⚠️ Erreur {zone} → fallback")
            temp = 20.0
            vhm0 = 1.0
            next_vhm = 1.1
            wind_speed = 10.0
            wind_dir = "N"

        # =========================
        # 📉📈 TENDANCE (Upwelling)
        # =========================
        prev = old_temp.get(zone, temp)
        if temp < prev - 0.2:
            trend = "📉"
        elif temp > prev + 0.2:
            trend = "📈"
        else:
            trend = "➡️"

        # =========================
        # 🚨 ALERTE MER
        # =========================
        if vhm0 >= 2.3:
            alert = "🔴"
        elif vhm0 >= 1.5:
            alert = "🟡"
        else:
            alert = "🟢"

        # =========================
        # JSON FINAL (FRONT READY)
        # =========================
        results.append({
            "zone": zone,
            "temp": temp,
            "vhm0": vhm0,
            "trend": trend,
            "alert": alert,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir,
            "next_vhm": next_vhm
        })

        telegram_report += (
            f"📍 <b>{zone}</b> {alert}\n"
            f"🌡️ {temp}°C {trend}\n"
            f"🌊 {vhm0} m | 🌬️ {wind_speed} km/h {wind_dir}\n\n"
        )

    # ============================================================
    # 💾 SAUVEGARDE JSON (pour le site)
    # ============================================================
    with open("data.json", "w") as f:
        json.dump(results, f, indent=2)

    print("✅ data.json généré avec succès")

    # ============================================================
    # 📤 TELEGRAM (optionnel)
    # ============================================================
    if TG_TOKEN and TG_ID:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_ID, "text": telegram_report, "parse_mode": "HTML"}
        )

# ============================================================
if __name__ == "__main__":
    main()
