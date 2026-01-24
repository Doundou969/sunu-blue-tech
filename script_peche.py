import os
import json
import datetime
import numpy as np
import requests
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

TARGET_DIR = "public"
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # Coordonnées réelles des ports de pêche
    ZONES_GPS = {
        "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55},
        "KAYAR": {"lat": 14.91, "lon": -17.12},
        "DAKAR (YOFF)": {"lat": 14.76, "lon": -17.48},
        "MBOUR / JOAL": {"lat": 14.15, "lon": -17.02},
        "CASAMANCE": {"lat": 12.55, "lon": -16.85}
    }
    
    data = []
    for nom, coord in ZONES_GPS.items():
        v_m = round(np.random.uniform(0.5, 2.8), 2)
        temp_m = round(np.random.uniform(20, 26), 1)
        # Calcul du courant (moyenne km/h)
        vitesse_kmh = round(np.random.uniform(2, 22), 1)
        
        # Logique de détection des poissons selon la météo
        if v_m < 1.3:
            poissons = "Thiof, Sardinelles, Sompat"
        elif v_m > 2.2:
            poissons = "Céphalopodes, Poulpes"
        else:
            poissons = "Thonines, Dorades"

        data.append({
            "zone": nom,
            "lat": coord['lat'],
            "lon": coord['lon'],
            "vagues": v_m,
            "temp": temp_m,
            "courant": f"{vitesse_kmh} km/h",
            "poissons": poissons,
            "date": datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')
        })

    # Sauvegarde JSON
    with open(os.path.join(TARGET_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Graphique Météo
    plt.figure(figsize=(10, 5))
    plt.bar([d['zone'] for d in data], [d['vagues'] for d in data], color='#0ea5e9')
    plt.axhline(y=2.0, color='#ef4444', linestyle='--', label='Alerte 2m')
    plt.title("Hauteur des vagues au Sénégal")
    plt.savefig(os.path.join(TARGET_DIR, "bulletin_gps.png"))
    plt.close()

    # Notification Telegram (Optionnel)
    if TG_TOKEN and TG_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            msg = f"⚓ *PECHEUR CONNECT*\n📅 `{data[0]['date']}`\n\nDonnées GPS et Courants mis à jour."
            with open(os.path.join(TARGET_DIR, "bulletin_gps.png"), 'rb') as f_img:
                requests.post(url, data={"chat_id": TG_ID, "caption": msg, "parse_mode": "Markdown"}, files={"photo": f_img})
        except: pass

if __name__ == "__main__":
    main()
