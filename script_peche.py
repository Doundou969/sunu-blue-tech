import os
import json
from datetime import datetime
import copernicusmarine
import numpy as np

# -------------------------
# CONFIG
# -------------------------
ZONE = "Grande Côte – Sénégal"
DATASET_CHL = "cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1D"
DATASET_PHY = "cmems_mod_glo_phy_anfc_0.083deg_P1D-m"

# -------------------------
# UTILS
# -------------------------
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
# MAIN
# -------------------------
def main():
    print("🔑 Connexion Copernicus Marine...")

    os.environ["COPERNICUSMARINE_USERNAME"] = os.getenv("COPERNICUS_USERNAME", "")
    os.environ["COPERNICUSMARINE_PASSWORD"] = os.getenv("COPERNICUS_PASSWORD", "")
    os.environ["COPERNICUSMARINE_DISABLE_CREDENTIALS_CACHE"] = "true"

    # --- Chlorophylle
    chl_ds = copernicusmarine.open_dataset(
        dataset_id=DATASET_CHL,
        minimum_longitude=-20,
        maximum_longitude=-10,
        minimum_latitude=10,
        maximum_latitude=17,
        start_datetime="2026-01-01",
        end_datetime="2026-01-10"
    )

    chl = float(chl_ds["CHL"].mean().values)

    # --- Physique (SST + courant)
    phy_ds = copernicusmarine.open_dataset(
        dataset_id=DATASET_PHY,
        minimum_longitude=-20,
        maximum_longitude=-10,
        minimum_latitude=10,
        maximum_latitude=17,
        start_datetime="2026-01-01",
        end_datetime="2026-01-10"
    )

    sst = float(phy_ds["thetao"].isel(depth=0).mean().values)
    cur_u = phy_ds["uo"].isel(depth=0).mean().values
    cur_v = phy_ds["vo"].isel(depth=0).mean().values
    courant = float(np.sqrt(cur_u**2 + cur_v**2))

    # --- Normalisation (valeurs typiques Atlantique Sénégal)
    chl_n = normalize(chl, 0.1, 2.0)
    sst_n = normalize(sst, 18, 30)
    cur_n = normalize(courant, 0.05, 0.5)

    score = round(0.5 * chl_n + 0.3 * sst_n + 0.2 * cur_n, 2)

    result = {
        "zone": ZONE,
        "date": datetime.utcnow().isoformat() + "Z",
        "chlorophylle_mg_m3": round(chl, 3),
        "sst_celsius": round(sst, 2),
        "courant_ms": round(courant, 3),
        "score_peche": score,
        "etat": etat_zone(score)
    }

    # --- Écriture data.json
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("✅ data.json généré")
    print(result)

    # --- Telegram
    send_telegram(result)

# -------------------------
# TELEGRAM
# -------------------------
def send_telegram(data):
    import requests

    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")

    if not token or not chat_id:
        print("⚠️ Telegram non configuré")
        return

    message = (
        f"🌊 *PêcheurConnect – Bulletin Mer*\n\n"
        f"📍 Zone : {data['zone']}\n"
        f"📅 Date : {data['date'][:10]}\n\n"
        f"🌱 Chlorophylle : {data['chlorophylle_mg_m3']} mg/m³\n"
        f"🌡️ Température mer : {data['sst_celsius']} °C\n"
        f"🌊 Courant : {data['courant_ms']} m/s\n\n"
        f"🎯 *Score pêche* : {data['score_peche']}\n"
        f"📊 État : *{data['etat']}*"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    requests.post(url, json=payload)
    print("📲 Message Telegram envoyé")

if __name__ == "__main__":
    main()
