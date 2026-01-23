#!/usr/bin/env python3
import os, json
from datetime import datetime
print("🚀 FORCE DATA CREATION")
os.makedirs("public", exist_ok=True)

# DONNÉES FIXES SÉNÉGAL
data = [
    {"zone": "SAINT-LOUIS", "status": "⚠️", "lat": 16.03, "lon": -16.55, "vagues": 2.24, "temp": 17.5, "courant": 0.3, "carte": "https://www.google.com/maps?q=16.03,-16.55", "date": datetime.now().strftime('%d/%m/%Y | %H:%M')},
    {"zone": "LOMPOUL", "status": "⚠️", "lat": 15.42, "lon": -16.82, "vagues": 2.29, "temp": 17.8, "courant": 0.5, "carte": "https://www.google.com/maps?q=15.42,-16.82", "date": datetime.now().strftime('%d/%m/%Y | %H:%M')},
    {"zone": "DAKAR / KAYAR", "status": "⚠️", "lat": 14.85, "lon": -17.45, "vagues": 2.48, "temp": 19.0, "courant": 0.5, "carte": "https://www.google.com/maps?q=14.85,-17.45", "date": datetime.now().strftime('%d/%m/%Y | %H:%M')},
    {"zone": "MBOUR / JOAL", "status": "✅", "lat": 14.15, "lon": -17.02, "vagues": 1.08, "temp": 20.0, "courant": 0.2, "carte": "https://www.google.com/maps?q=14.15,-17.02", "date": datetime.now().strftime('%d/%m/%Y | %H:%M')},
    {"zone": "CASAMANCE", "status": "✅", "lat": 12.55, "lon": -16.85, "vagues": 0.66, "temp": 23.1, "courant": 0.2, "carte": "https://www.google.com/maps?q=12.55,-16.85", "date": datetime.now().strftime('%d/%m/%Y | %H:%M')}
]

# FORCE WRITE
with open("public/data.json", "w") as f:
    json.dump(data, f)
print("✅ public/data.json CRÉÉ")

# PWA
with open("public/manifest.json", "w") as f:
    json.dump({"name": "Sunu Blue Tech", "short_name": "SunuBlue", "start_url": "/", "display": "standalone"}, f)
print("✅ manifest.json CRÉÉ")

print("🎉 DONNÉES LIVE !")
