import os
import json
from datetime import datetime
import numpy as np
import copernicusmarine
import folium
from rich import print
from telegram import Bot

# -------------------------
# CONFIG
# -------------------------
LAT = 14.7167
LON = -17.4677
ZONE = "Côte sénégalaise"

DATA_FILE = "data.json"
MAP_FILE = "templates/map_template.html"

DATASET_CHL = "cmems_mod_glo_bgc_my_0.25deg_P1D-m"
DATASET_PHY = "cmems_mod_glo_phy_my_0.25deg_P1D-m"  # fallback robuste

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
def load_copernicus(dataset_id, variables=None):
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

    print(f"📦 Variable
