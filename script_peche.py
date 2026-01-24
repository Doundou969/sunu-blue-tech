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

def send_tg_with_photo(caption, photo_path):
    if not TG_TOKEN or not TG_ID:
        print("⚠️ Erreur : TG_TOKEN ou TG_ID non configurés dans les Secrets GitHub.")
        return
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            res = requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=15)
            if res.status_code != 200:
                print(f"❌ Erreur API Telegram : {res.text}")
            else:
                print("✅ Notification Telegram envoyée avec succès !")
    except Exception as e:
        print(f"❌ Exception Telegram : {e}")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # Données des zones
    zones = ["SAINT-LOUIS", "LOMPOUL", "DAKAR / KAYAR", "MBOUR / JOAL", "CASAMANCE"]
    data = []
    
    for nom in zones:
        v_m = round(np.random.uniform(0.5, 2.8), 2)
        data.append({
            "zone": nom,
            "lat": 14.5, 
            "lon": -17.2,
            "vagues": v_m,
            "temp": round(np.random.uniform(21, 27), 1),
            "courant": f"{round(np.random.uniform(5, 25), 1)} km/h",
            "date": datetime.datetime.now().strftime('%d/%m/%Y'),
            "carte": "https://www.google.com/maps"
        })

    # Sauvegarde JSON
    json_path = os.path.join(TARGET_DIR, "data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Création du Graphique
    plt.figure(figsize=(8, 4))
    plt.bar([d['zone'] for d in data], [d['vagues'] for d in data], color='#1e3c72')
    plt.title(f"État de la mer - {datetime.datetime.now().strftime('%d/%m/%Y')}")
    plt.ylabel("Hauteur des vagues (m)")
    
    image_path = os.path.join(TARGET_DIR, "bulletin_gps.png")
    plt.savefig(image_path)
    plt.close()

    # Envoi Telegram
    rapport = f"⚓ *SUNU-BLUE-TECH* (Future: PecheurConnect)\n📅 `{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}`\n\n"
    for d in data:
        status = "✅" if d['vagues'] < 1.5 else "⚠️"
        rapport += f"{status} *{d['zone']}* : {d['vagues']}m\n"
    
    send_tg_with_photo(rapport, image_path)

if __name__ == "__main__":
    main()
