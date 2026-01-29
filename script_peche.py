#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import datetime
import requests

try:
    import copernicusmarine
except ImportError:
    print("⚠️ CopernicusMarine non installé, fallback activé")
    copernicusmarine = None

# -----------------------------
# 🟦 CONFIG ZONES
# -----------------------------
zones = {
    "SAINT-LOUIS": [16.03, -16.50],
    "LOUGA-POTOU": [15.48, -16.75],
    "KAYAR": [14.92, -17.20],
    "DAKAR-YOFF": [14.75, -17.48],
    "MBOUR-JOAL": [14.41, -16.96],
    "CASAMANCE": [12.50, -16.70]
}

# -----------------------------
# 🟦 FONCTIONS TELEGRAM
# -----------------------------
def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Telegram non configuré")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        print("📨 Notification Telegram envoyée")
    except Exception as e:
        print(f"⚠️ Telegram erreur : {e}")

# -----------------------------
# 🟦 DATES
# -----------------------------
END_DATE = datetime.datetime.utcnow()
START_DATE = END_DATE - datetime.timedelta(days=1)
DATE_STR = END_DATE.strftime("%d/%m/%Y %H:%M UTC")

# -----------------------------
# 🟦 RÉCUPÉRATION DONNÉES
# -----------------------------
results = {}

for zone, coords in zones.items():
    lat, lon = coords
    data = {}
    source = "fallback"

    if copernicusmarine:
        try:
            # Connexion Copernicus
            copernicusmarine.login(
                username=os.getenv("COPERNICUS_USERNAME"),
                password=os.getenv("COPERNICUS_PASSWORD")
            )
            print(f"📡 Récupération données : {zone}")

            # Exemple dataset : ocean physical daily
            ds = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_phy_my_0.083_P1D-m",
                time_range=(START_DATE, END_DATE),
                latitude=lat,
                longitude=lon
            )

            data["temp"] = round(float(ds.variables["thetao"][-1]), 2)
            data["vhm0"] = round(float(ds.variables["vhm0"][-1]), 2)
            data["trend"] = "📈" if data["vhm0"] > 0.5 else "📉"
            source = "Copernicus Marine"

        except Exception as e:
            print(f"⚠️ SST/Vent indisponible pour {zone}: {e}")
            # fallback simple : valeur par défaut
            data["temp"] = 27.0
            data["vhm0"] = 1.0
            data["trend"] = "📉"
    else:
        # fallback si Copernicus absent
        data["temp"] = 27.0
        data["vhm0"] = 1.0
        data["trend"] = "📉"

    data["alert"] = "🔴" if data["vhm0"] >= 2.2 else "🟢"
    data["wind_speed"] = 15
    data["wind_dir"] = "NE"
    data["next_vhm"] = data["vhm0"] + 0.2

    results[zone] = {"data": data, "source": source}

# -----------------------------
# 🟦 SAUVEGARDE DATA.JSON
# -----------------------------
output = {
    "updated_utc": DATE_STR,
    "zones": results
}

with open("data.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"✅ data.json mis à jour ({DATE_STR})")

# -----------------------------
# 🟦 ENVOI TELEGRAM
# -----------------------------
ok_zones = [z for z, d in results.items() if d["source"] == "Copernicus Marine"]
fallback_zones = [z for z, d in results.items() if d["source"] != "Copernicus Marine"]

telegram_message = f"""
🌊 *PÊCHEURCONNECT 🇸🇳*
📡 *Mise à jour satellite*

🕒 {DATE_STR}

✅ Données Copernicus :
{', '.join(ok_zones) if ok_zones else 'Aucune'}

⚠️ Mode fallback :
{', '.join(fallback_zones) if fallback_zones else 'Aucune'}

📅 Fenêtre données :
{START_DATE.strftime('%d/%m/%Y')} → {END_DATE.strftime('%d/%m/%Y')}
"""

send_telegram(telegram_message)
