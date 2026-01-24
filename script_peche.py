import os, json, datetime
import numpy as np

# Dossier cible pour GitHub Pages
TARGET_DIR = "public"

def main():
    # SECURITÉ : Créer le dossier s'il n'existe pas
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
    
    zones = ["SAINT-LOUIS", "KAYAR", "DAKAR", "MBOUR", "CASAMANCE"]
    data = []
    
    for nom in zones:
        v = round(np.random.uniform(0.5, 2.5), 2)
        data.append({
            "zone": nom,
            "lat": 14.7, "lon": -17.4, # Coordonnées par défaut
            "vagues": v,
            "temp": round(np.random.uniform(18, 24), 1),
            "courant": f"{round(np.random.uniform(0.1, 0.6), 1)} km/h",
            "poissons": "Thiof" if v < 1.5 else "Sardinelles",
            "date": datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')
        })

    # Sauvegarde dans public/data.json
    with open(os.path.join(TARGET_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("✅ Fichier JSON généré avec succès dans le dossier public/")

if __name__ == "__main__":
    main()
