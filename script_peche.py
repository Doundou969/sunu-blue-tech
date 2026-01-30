import os, json, random, requests
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

def fallback_data():
  data = []
  for z,(lat,lon) in ZONES.items():
    vhm0 = round(random.uniform(0.8, 3.2), 2)
    alert = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"
    data.append({
      "zone": z,
      "lat": lat,
      "lon": lon,
      "vhm0": vhm0,
      "temp": round(random.uniform(22, 28), 1),
      "alert": alert,
      "trend": "↗" if random.random() > 0.5 else "↘"
    })
  return data

data = fallback_data()

with open("data.json", "w", encoding="utf-8") as f:
  json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ data.json généré")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

if TG_TOKEN and TG_ID:
  msg = "📡 PecheurConnect – État mer\n"
  for d in data:
    msg += f"\n{d['zone']} : {d['vhm0']}m {d['alert']}"
  requests.post(
    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
    data={"chat_id": TG_ID, "text": msg}
  )
  print("📨 Telegram envoyé")
else:
  print("⚠️ Telegram non configuré")

print("✅ Script terminé sans erreur")
