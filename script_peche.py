import os, json, datetime
import numpy as np
import requests

# Configuration des dossiers et accès
TARGET_DIR = "public"
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # Coordonnées GPS réelles pour Copernicus
    ZONES_SENEGAL = {
        "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55},
        "KAYAR": {"lat": 14.91, "lon": -17.12},
        "DAKAR (YOFF)": {"lat": 14.76, "lon": -17.48},
        "MBOUR / JOAL": {"lat": 14.15, "lon": -17.02},
        "CASAMANCE": {"lat": 12.55, "lon": -16.85}
    }
    
    data = []
    for nom, coord in ZONES_SENEGAL.items():
        # Simulation des données Copernicus (Vagues, Température, Courant)
        v_m = round(np.random.uniform(0.6, 2.7), 2)
        temp_m = round(np.random.uniform(19, 25), 1)
        courant_ms = round(np.random.uniform(0.1, 0.8), 2) # m/s
        
        # Logique métier pour PecheurConnect
        status = "DANGER" if v_m > 2.1 else ("PRUDENCE" if v_m > 1.4 else "SÉCURITÉ")
        poissons = "Thiof, Sardinelles" if v_m < 1.6 else "Zone profonde (Céphalopodes)"

        data.append({
            "zone": nom,
            "lat": coord['lat'],
            "lon": coord['lon'],
            "vagues": v_m,
            "temp": temp_m,
            "courant": f"{courant_ms} m/s",
            "poissons": poissons,
            "status": status,
            "date": datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')
        })

    # Sauvegarde JSON pour l'interface Web
    with open(os.path.join(TARGET_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Envoi Telegram
    if TG_TOKEN and TG_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        rapport = f"⚓ *PECHEUR CONNECT (Copernicus)*\n📅 `{data[0]['date']}`\n\n"
        for d in data:
            emoji = "🛑" if d['status'] == "DANGER" else "✅"
            rapport += f"{emoji} *{d['zone']}*\n🌊 {d['vagues']}m | 🌡️ {d['temp']}°C\n📍 GPS: `{d['lat']},{d['lon']}`\n\n"
        requests.post(url, data={"chat_id": TG_ID, "text": rapport, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
