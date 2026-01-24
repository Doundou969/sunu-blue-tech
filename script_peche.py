import os
import json
import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# Dossier cible unique pour GitHub Pages
TARGET_DIR = "public"

def main():
    # 1. Création du dossier
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 2. Simulation des données (ou récupération Copernicus)
    zones = ["SAINT-LOUIS", "LOMPOUL", "DAKAR / KAYAR", "MBOUR / JOAL", "CASAMANCE"]
    data = []
    
    for nom in zones:
        v_m = round(np.random.uniform(0.5, 2.8), 2)
        data.append({
            "zone": nom,
            "lat": 14.5, # À adapter selon vos coordonnées réelles
            "lon": -17.2,
            "vagues": v_m,
            "temp": round(np.random.uniform(21, 27), 1),
            "courant": f"{round(np.random.uniform(5, 25), 1)} km/h",
            "date": datetime.datetime.now().strftime('%d/%m/%Y'),
            "carte": "https://www.google.com/maps"
        })

    # 3. Sauvegarde du JSON
    with open(os.path.join(TARGET_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 4. Sauvegarde de l'image (pour Telegram)
    plt.figure(figsize=(8, 4))
    plt.bar([d['zone'] for d in data], [d['vagues'] for d in data], color='skyblue')
    plt.title("Hauteur des vagues (m)")
    plt.savefig(os.path.join(TARGET_DIR, "bulletin_gps.png"))
    plt.close()
    
    print(f"✅ Terminé : {len(data)} zones générées dans {TARGET_DIR}/")

if __name__ == "__main__":
    main()
