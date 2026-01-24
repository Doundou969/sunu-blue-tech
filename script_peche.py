import os
import requests
import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import json

# Configuration
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

# Dossier cible (doit être 'public' pour correspondre à votre index.html)
TARGET_DIR = "public"

ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55},
    "LOMPOUL": {"lat": 15.42, "lon": -16.82},
    "DAKAR / KAYAR": {"lat": 14.85, "lon": -17.45},
    "MBOUR / JOAL": {"lat": 14.15, "lon": -17.02},
    "CASAMANCE": {"lat": 12.55, "lon": -16.85}
}

def ensure_dirs():
    """Créer le dossier public s'il n'existe pas"""
    os.makedirs(TARGET_DIR, exist_ok=True)

def send_tg_with_photo(caption, photo_path):
    if not TG_TOKEN or not TG_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=10)
    except Exception as e: print(f"❌ Erreur Telegram: {e}")

def main():
    ensure_dirs()
    data = []
    
    # Récupération ou Simulation
    if not USER or not PASS:
        print("⚠️ Utilisation de données simulées")
        for nom, coord in ZONES.items():
            vague = np.random.uniform(0.5, 2.8)
            data.append({
                'zone': nom, 'lat': coord['lat'], 'lon': coord['lon'],
                'vagues': round(vague, 2), # JavaScript attend 'vagues'
                'temp': round(np.random.uniform(20, 26), 1),
                'courant': f"{round(np.random.uniform(5, 20), 1)} km/h", # JavaScript attend 'courant'
                'date': datetime.datetime.now().strftime('%d/%m/%Y'),
                'carte': f"https://www.google.com/maps?q={coord['lat']},{coord['lon']}"
            })
    else:
        # Code Copernicus (Similaire à votre original, mais avec les clés corrigées)
        # ... (Insertion de votre logique de récupération Copernicus ici)
        # Assurez-vous d'utiliser les noms de clés : vagues, courant, carte, date.
        pass

    # --- GÉNÉRATION DES FICHIEURS POUR LE WEB ---

    # 1. JSON (Clé du succès pour index.html)
    json_path = os.path.join(TARGET_DIR, "data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 2. Graphique pour Telegram
    plt.figure(figsize=(10, 6))
    # ... (Votre code de graphique plt ici) ...
    image_path = os.path.join(TARGET_DIR, "bulletin_gps.png")
    plt.savefig(image_path)
    plt.close()

    # 3. Rapport Telegram
    rapport = f"🇸🇳 *SUNU-BLUE-TECH* \n📅 `{datetime.datetime.now().strftime('%d/%m/%Y')}`\n"
    send_tg_with_photo(rapport, image_path)

    print(f"✅ Fichiers mis à jour dans le dossier '{TARGET_DIR}'")

if __name__ == "__main__":
    main()
