#!/usr/bin/env python3
import os
import json
from datetime import datetime

print("🚀 Sunu Blue Tech - Format Sénégal")
os.makedirs("public", exist_ok=True)

# DONNÉES SENEGAL AIRE - Zones pêcheurs
donnees = [
    {
        "nom": "SAINT-LOUIS",
        "lat": 16.03, "lon": -16.55,
        "vagues": 2.24, "temp": 17.5, "courant": 0.3,
        "status": "⚠️"
    },
    {
        "nom": "LOMPOUL", 
        "lat": 15.42, "lon": -16.82,
        "vagues": 2.29, "temp": 17.8, "courant": 0.5,
        "status": "⚠️"
    },
    {
        "nom": "DAKAR / KAYAR",
        "lat": 14.85, "lon": -17.45, 
        "vagues": 2.48, "temp": 19.0, "courant": 0.5,
        "status": "⚠️"
    },
    {
        "nom": "MBOUR / JOAL",
        "lat": 14.15, "lon": -17.02,
        "vagues": 1.08, "temp": 20.0, "courant": 0.2, 
        "status": "✅"
    },
    {
        "nom": "CASAMANCE",
        "lat": 12.55, "lon": -16.85,
        "vagues": 0.66, "temp": 23.1, "courant": 0.2,
        "status": "✅"
    }
]

# FORMAT TELEGRAM + SITE
date_fmt = datetime.now().strftime('%d/%m/%Y | %H:%M')
message = f"""🇸🇳 SUNU-BLUE-TECH : NAVIGATION
📅 {date_fmt}
━━━━━━━━━━━━━━━
"""

for zone in donnees:
    message += f"""📍 {zone['nom']} {zone['status']}
🌐 GPS : {zone['lat']:.2f}, {zone['lon']:.2f}
🌊 Vagues : {zone['vagues']:.2f} m | 🌡 {zone['temp']}°C
🚩 Courant : {zone['courant']} km/h
🔗 Voir sur la Carte (https://www.google.com/maps?q={zone['lat']},{zone['lon']})
───────────────
"""

message += """🆘 URGENCE MER : 119
⚓️ Xam-Xam au service du Géej."""

# TELEGRAM
try:
    tg_token = os.getenv('TG_TOKEN')
    tg_id = os.getenv('TG_ID')
    if tg_token and tg_id:
        import requests
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        requests.post(url, data={"chat_id": tg_id, "text": message, "parse_mode": "HTML"}).raise_for_status()
        print("✅ Telegram Sénégal envoyé")
except:
    print("⚠️ Telegram skip")

# SITE WEB (JSON)
data_web = []
for zone in donnees:
    data_web.append({
        "zone": zone['nom'],
        "status": zone['status'],
        "lat": zone['lat'],
        "lon": zone['lon'], 
        "vagues": zone['vagues'],
        "temp": zone['temp'],
        "courant": zone['courant'],
        "carte": f"https://www.google.com/maps?q={zone['lat']},{zone['lon']}",
        "date": date_fmt
    })

# SAUVEGARDE
with open("public/data.json", "w") as f:
    json.dump(data_web, f, indent=2)
print("✅ data.json Sénégal")

print("🎉 Xam-Xam Géej Format OFFICIEL !")
