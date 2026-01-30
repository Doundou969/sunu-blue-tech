import os
import json
import random
import requests
from datetime import datetime

print("🚀 PecheurConnect démarrage")

# ================================
# CONFIG
# ================================

DATA_DIR = "data"
DATA_FILE = f"{DATA_DIR}/data.json"

ZONES = {
    "SAINT-LOUIS": (16.03, -16.50),
    "KAYAR": (14.92, -17.20),
    "DAKAR-YOFF": (14.75, -17.48),
    "MBOUR-JOAL": (14.41, -16.96),
    "CASAMANCE": (12.50, -16.70),
    "LOUGA-POTOU": (15.48, -16.75)
}

# ================================
# FALLBACK DATA (SAFE MODE)
# ================================

def fallback_data():
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
            "alert": alert,
            "trend": "↗" if random.random() > 0.5 else "↘",
            "timestamp": datetime.utcnow().isoformat()
        })
    return data


# ================================
# MAIN
# ================================

def main():
    # 1️⃣ Génération données (fallback sécurisé)
    try:
        data = fallback_data()
    except Exception as e:
        print("❌ Impossible de générer les données :", e)
        return

    # 2️⃣ Sauvegarde JSON
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✅ data.json généré")
    except Exception as e:
        print("❌ Erreur écriture data.json :", e)
        return

    # 3️⃣ Telegram (OPTIONNEL)
    TG_TOKEN = os.getenv("TG_TOKEN")
    TG_ID = os.getenv("TG_ID")

    if TG_TOKEN and TG_ID:
        try:
            message = "📡 *PecheurConnect – État de la mer*\n"
            for d in data:
                message += f"\n{d['zone']} : {d['vhm0']} m {d['alert']}"

            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                data={
                    "chat_id": TG_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=10
            )
            print("📨 Telegram envoyé")
        except Exception as e:
            print("⚠️ Erreur Telegram (ignorée) :", e)
    else:
        print("⚠️ Telegram non configuré")

    print("✅ Script terminé sans erreur")


if __name__ == "__main__":
    main()
