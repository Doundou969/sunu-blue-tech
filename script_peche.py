import json
import os
import random
from datetime import datetime

print("🚀 PecheurConnect démarrage")

ZONES = {
    "SAINT-LOUIS": (16.03, -16.50),
    "KAYAR": (14.92, -17.20),
    "DAKAR-YOFF": (14.75, -17.48),
    "MBOUR-JOAL": (14.41, -16.96),
    "CASAMANCE": (12.50, -16.70),
    "LOUGA-POTOU": (15.48, -16.75)
}

def generate_fallback():
    data = []
    for zone, (lat, lon) in ZONES.items():
        vhm0 = round(random.uniform(0.8, 3.2), 2)
        alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"

        data.append({
            "zone": zone,
            "lat": lat,
            "lon": lon,
            "vhm0": vhm0,
            "temp": round(random.uniform(22, 28), 1),
            "wind_speed": random.randint(8, 30),
            "wind_dir": random.choice(["N", "NE", "NW", "W", "SW"]),
            "alert": alert,
            "trend": "↗" if random.random() > 0.5 else "↘",
            "next_vhm": round(vhm0 + random.uniform(-0.5, 0.6), 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "fallback"
        })
    return data

# Génération données
data = generate_fallback()

# Écriture data.json
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ data.json généré")

# Telegram volontairement désactivé
print("⚠️ Telegram non configuré")

print("✅ Script terminé sans erreur")
