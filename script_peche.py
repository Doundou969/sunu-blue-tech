import os
import json
from datetime import datetime
import numpy as np
import xarray as xr
import copernicusmarine
import folium
from rich import print
from telegram import Bot

# -------------------------
# CONFIG
# -------------------------
LAT = 14.7167
LON = -17.4677
ZONE = "Grande Côte – Sénégal"

DATASET_CHL = "cmems_mod_glo_bgc_my_0.25deg_P1D-m"
DATASET_PHY = "cmems_mod_glo_phy_my_0.083_P1D-m"

DATA_FILE = "data.json"
MAP_FILE = "templates/map_template.html"

# Telegram
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

# -------------------------
# UTILITAIRES
# -------------------------
def normalize(value, vmin, vmax):
    return max(0, min(1, (value - vmin) / (vmax - vmin)))

def etat_zone(score):
    if score >= 0.7: return "🟢 Favorable"
    elif score >= 0.4: return "🟠 Moyen"
    else: return "🔴 Faible"

def send_telegram(data):
    if not TG_TOKEN or not TG_ID:
        print("⚠️ Telegram non configuré")
        return
    try:
        bot = Bot(token=TG_TOKEN)
        msg = (
            f"[PecheurConnect] {ZONE}\n"
            f"Date: {data['timestamp']}\n"
            f"Chlorophylle: {data['chlorophyll']} mg/m³\n"
            f"SST: {data['sst']} °C\n"
            f"Courants: {data['courant']} m/s\n"
            f"Score pêche: {data['score_peche']} ({data['etat']})"
        )
        bot.send_message(chat_id=TG_ID, text=msg)
        print("✅ Telegram envoyé")
    except Exception as e:
        print(f"❌ Erreur Telegram: {e}")

# -------------------------
# CHARGEMENT DATA COPERNICUS
# -------------------------
def load_copernicus(dataset_id, variables):
    username = os.getenv("COPERNICUS_USERNAME")
    password = os.getenv("COPERNICUS_PASSWORD")

    if not username or not password:
        raise RuntimeError("❌ Secrets Copernicus manquants")

    os.environ["COPERNICUSMARINE_DISABLE_INTERACTIVE"] = "true"

    ds = copernicusmarine.open_dataset(
        dataset_id=dataset_id,
        username=username,
        password=password
    )

    # sélection point
    ds_point = ds.sel(latitude=LAT, longitude=LON, method="nearest")

    return ds_point

# -------------------------
# SCORE PÊCHE MULTI-FACTEURS
# -------------------------
def compute_score(chl, sst, courant):
    chl_n = normalize(chl, 0.1, 2.0)
    sst_n = normalize(sst, 18, 30)
    cur_n = normalize(courant, 0.05, 0.5)
    score = round(0.5*chl_n + 0.3*sst_n + 0.2*cur_n, 2)
    return score

# -------------------------
# GENERATION CARTE LEAFLET
# -------------------------
def generate_map(data):
    m = folium.Map(location=[LAT, LON], zoom_start=7)
    color = {"🟢 Favorable":"green","🟠 Moyen":"orange","🔴 Faible":"red"}[data['etat']]
    folium.CircleMarker(
        location=[LAT, LON],
        radius=15,
        color=color,
        fill=True,
        fill_opacity=0.6,
        popup=f"Score: {data['score_peche']}"
    ).add_to(m)
    os.makedirs("templates", exist_ok=True)
    m.save(MAP_FILE)
    print(f"✅ Carte générée: {MAP_FILE}")

# -------------------------
# SCRIPT PRINCIPAL
# -------------------------
def main():
    print("🔑 Connexion Copernicus Marine...")
    chl_ds = load_copernicus(DATASET_CHL, ["chl"])
    phy_ds = load_copernicus(DATASET_PHY, ["thetao","uo","vo"])

    chl = float(chl_ds["chl"].mean().values)
    sst = float(phy_ds["thetao"].isel(depth=0).mean().values)
    u = phy_ds["uo"].isel(depth=0).mean().values
    v = phy_ds["vo"].isel(depth=0).mean().values
    courant = float(np.sqrt(u**2 + v**2))

    score = compute_score(chl, sst, courant)
    etat = etat_zone(score)

    data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "zone": ZONE,
        "chlorophyll": round(chl, 3),
        "sst": round(sst,2),
        "courant": round(courant,3),
        "score_peche": score,
        "etat": etat
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ data.json généré")
    print(data)

    generate_map(data)
    send_telegram(data)

# -------------------------
if __name__ == "__main__":
    main()
