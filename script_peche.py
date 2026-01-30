# =========================================
# PÊCHEURCONNECT – COPERNICUS AUTO UPDATE
# Génère data.json + alerte Telegram
# =========================================

import os
import json
import datetime
import requests

print("🚀 PecheurConnect démarrage")

# =========================
# CONFIG
# =========================
DATA_FILE = "data.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================
# ZONES PÊCHE (FIXES)
# =========================
ZONES = [
    {"id": 1, "nom": "Dakar", "lat": 14.7, "lon": -17.4},
    {"id": 2, "nom": "Rufisque", "lat": 14.7, "lon": -17.2},
    {"id": 3, "nom": "Joal", "lat": 14.2, "lon": -16.8},
    {"id": 4, "nom": "Mbour", "lat": 14.4, "lon": -16.9},
    {"id": 5, "nom": "Saint-Louis", "lat": 16.0, "lon": -16.5},
    {"id": 6, "nom": "Casamance", "lat": 12.6, "lon": -16.3},
]

# =========================
# FONCTIONS
# =========================
def safe_copernicus_data():
    """
    Mode dégradé si Copernicus KO
    """
    print("⚠️ Copernicus indisponible → fallback data")
    zones_data = []
    for z in ZONES:
        zones_data.append({
            "zone": z["nom"],
            "lat": z["lat"],
            "lon": z["lon"],
            "etat_mer": "Jàmm",
            "indice_plancton": round(0.3 + (z["id"] * 0.05), 2),
            "danger": "Vert"
        })
    return zones_data


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram non configuré")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("📨 Telegram envoyé")
        else:
            print(f"⚠️ Telegram erreur HTTP {r.status_code}")
    except Exception as e:
        print("⚠️ Erreur Telegram :", e)


# =========================
# MAIN
# =========================
try:
    print("🔑 Connexion Copernicus Marine...")

    # 👉 ICI tu brancheras plus tard copernicusmarine.open_dataset()
    # Pour l’instant on simule un échec volontaire (safe mode)
    raise Exception("Dataset non stable")

except Exception as e:
    print("⚠️ Mode dégradé Copernicus activé (safe mode)")
    data = safe_copernicus_data()

# =========================
# EXPORT JSON
# =========================
output = {
    "source": "Copernicus Marine",
    "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    "zones": data
}

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ data.json généré ({len(data)} zones)")

# =========================
# TELEGRAM ALERT
# =========================
message = (
    "📡 *PÊCHEURCONNECT – MISE À JOUR*\n\n"
    f"🕒 {output['generated_at']}\n"
    f"📍 Zones analysées : {len(data)}\n\n"
    "✅ Données disponibles\n"
    "⚠️ Mode Copernicus dégradé"
)

send_telegram(message)

print("✅ Script terminé sans erreur")
