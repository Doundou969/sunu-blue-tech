import os
import json
import requests
from datetime import datetime, timedelta

# Configuration des ports
ZONES = {
    "Saint-Louis": {"lat": 16.03, "lon": -16.51},
    "Kayar": {"lat": 14.91, "lon": -17.12},
    "Dakar": {"lat": 14.68, "lon": -17.44},
    "Mbour": {"lat": 14.41, "lon": -16.96},
    "Ziguinchor": {"lat": 12.58, "lon": -16.27}
}

def send_telegram(message):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Erreur Telegram: {e}")

def run_update():
    print(f"🚀 Mise à jour PecheurConnect : {datetime.now()}")
    all_data = []
    now = datetime.now()

    for name, coord in ZONES.items():
        forecasts = []
        for i in range(3):
            d = now + timedelta(days=i)
            # Simulation (sera remplacé par la lecture Copernicus xarray)
            v_wave = 1.2 + (i * 0.2)
            temp_mer = 21.5 + i
            
            safety = "🟢 SÛR"
            if v_wave > 2.0: safety = "🔴 DANGER"
            elif v_wave > 1.6: safety = "🟡 VIGILANCE"
            
            # Alerte Telegram si Danger aujourd'hui
            if i == 0 and safety == "🔴 DANGER":
                send_telegram(f"🚨 *ALERTE DANGER* à {name}!\nVagues: {v_wave}m. Sortie déconseillée.")

            forecasts.append({
                "jour": d.strftime("%A"),
                "v_now": round(v_wave, 2),
                "t_now": round(temp_mer, 1),
                "c_now": 0.4,
                "safety": safety,
                "index": "Excellent 🐟🐟🐟" if temp_mer < 23 else "Moyen 🐟"
            })
            
        all_data.append({
            "zone": name,
            "lat": coord["lat"],
            "lon": coord["lon"],
            "date_update": now.strftime("%H:%M"),
            "forecasts": forecasts
        })

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)
    print("💾 Fichier data.json généré avec succès.")

if __name__ == "__main__":
    run_update()
