import os
import json
import requests
import xarray as xr
from datetime import datetime, timedelta

# Configuration des zones
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
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

def run_update():
    print(f"🚀 Début de la mise à jour : {datetime.now()}")
    all_data = []
    
    # Simulation des données (À remplacer par l'appel API Copernicus avec vos identifiants)
    # Pour le test, nous générons des valeurs réalistes
    for name, coord in ZONES.items():
        forecasts = []
        for i in range(3):
            d = datetime.now() + timedelta(days=i)
            v_wave = 1.2 + (i * 0.2)  # Hauteur vagues
            t_sea = 22.0 + i         # Température
            
            # Logique de sécurité
            safety = "🟢 SÛR"
            if v_wave > 2.1: safety = "🔴 DANGER"
            elif v_wave > 1.7: safety = "🟡 VIGILANCE"
            
            # Alerte Telegram immédiate pour aujourd'hui si Danger
            if i == 0 and safety == "🔴 DANGER":
                send_telegram(f"🚨 *ALERTE DANGER* à {name} !\nVagues : {v_wave}m. Prudence conseillée.")

            forecasts.append({
                "jour": d.strftime("%A"),
                "v_now": round(v_wave, 2),
                "t_now": round(t_sea, 1),
                "c_now": 0.4,
                "safety": safety,
                "index": "Excellent 🐟" if t_sea < 24 else "Moyen 🐟"
            })
            
        all_data.append({
            "zone": name, "lat": coord["lat"], "lon": coord["lon"],
            "date_update": datetime.now().strftime("%H:%M"),
            "forecasts": forecasts
        })

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)
    print("💾 Fichier data.json généré.")

if __name__ == "__main__":
    run_update()
