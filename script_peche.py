import os
import json
import datetime
import numpy as np
import requests
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# Configuration
TARGET_DIR = "public"
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # Zones avec coordonnées GPS réelles
    ZONES_GPS = {
        "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55},
        "KAYAR": {"lat": 14.91, "lon": -17.12},
        "DAKAR (YOFF)": {"lat": 14.76, "lon": -17.48},
        "MBOUR / JOAL": {"lat": 14.15, "lon": -17.02},
        "CASAMANCE": {"lat": 12.55, "lon": -16.85}
    }
    
    data = []
    for nom, coord in ZONES_GPS.items():
        # Simulation ou calcul Copernicus
        v_m = round(np.random.uniform(0.5, 2.5), 2)
        temp_m = round(np.random.uniform(20, 26), 1)
        vitesse_kmh = round(np.random.uniform(2, 18), 1)
        
        # Logique de localisation des poissons
        if v_m < 1.2 and temp_m > 22:
            poissons = "Thiof, Sardinelles (Abondant)"
        elif v_m > 2.0:
            poissons = "Céphalopodes (Zone agitée)"
        else:
            poissons = "Espadons, Thonines"

        data.append({
            "zone": nom,
            "lat": coord['lat'],
            "lon": coord['lon'],
            "vagues": v_m,
            "temp": temp_m,
            "courant": f"{vitesse_kmh} km/h",
            "poissons": poissons,
            "date": datetime.datetime.now().strftime('%d/%m/%Y'),
            "carte": f"https://www.google.com/maps?q={coord['lat']},{coord['lon']}"
        })

    # Sauvegarde JSON (Public)
    with open(os.path.join(TARGET_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Graphique pour Telegram
    plt.figure(figsize=(10, 5))
    plt.bar([d['zone'] for d in data], [d['vagues'] for d in data], color='#00d4ff')
    plt.axhline(y=2.0, color='red', linestyle='--', label='Danger (2m)')
    plt.title("État de la Mer au Sénégal")
    plt.ylabel("Hauteur Vagues (m)")
    
    img_path = os.path.join(TARGET_DIR, "bulletin_gps.png")
    plt.savefig(img_path)
    plt.close()

    # Envoi Telegram
    if TG_TOKEN and TG_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            msg = f"⚓ *PECHEUR CONNECT* (Ex-SunuBlue)\n📅 `{data[0]['date']}`\n\n"
            for d in data:
                icon = "✅" if d['vagues'] < 1.8 else "🛑"
                msg += f"{icon} *{d['zone']}*\n📍 GPS: `{d['lat']},{d['lon']}`\n🐟 {d['poissons']}\n\n"
            with open(img_path, 'rb') as f_img:
                requests.post(url, data={"chat_id": TG_ID, "caption": msg, "parse_mode": "Markdown"}, files={"photo": f_img})
        except Exception as e: print(f"Erreur TG: {e}")

if __name__ == "__main__":
    main()
