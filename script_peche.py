import os, json, datetime
import numpy as np
import requests
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

TARGET_DIR = "public"
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def send_tg(caption, photo_path):
    if not TG_TOKEN or not TG_ID:
        print("❌ Erreur : TG_TOKEN ou TG_ID manquant dans les Secrets GitHub.")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            res = requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=15)
            if res.status_code == 200: print("✅ Telegram envoyé !")
            else: print(f"❌ Erreur Telegram : {res.status_code} - {res.text}")
    except Exception as e: print(f"❌ Exception TG : {e}")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    zones = ["SAINT-LOUIS", "KAYAR", "DAKAR", "MBOUR", "CASAMANCE"]
    data = []
    rapport_tg = f"⚓ *PECHEUR CONNECT*\n📅 `{datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')}`\n\n"
    
    for nom in zones:
        v = round(np.random.uniform(0.5, 2.8), 2)
        poisson = "Sardinelles" if v < 1.5 else "Thiof/Céphalopodes"
        data.append({
            "zone": nom, "vagues": v, "poissons": poisson,
            "temp": round(np.random.uniform(18, 24), 1),
            "courant": f"{round(np.random.uniform(0.1, 0.7), 1)} km/h",
            "date": datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')
        })
        icon = "✅" if v < 1.8 else "⚠️"
        rapport_tg += f"{icon} *{nom}* : {v}m | {poisson}\n"

    # Sauvegarde JSON
    with open(os.path.join(TARGET_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Graphique
    plt.figure(figsize=(8, 4))
    plt.bar([d['zone'] for d in data], [d['vagues'] for d in data], color='#00d4ff')
    plt.title("Hauteur des vagues (m)")
    img_path = os.path.join(TARGET_DIR, "bulletin_gps.png")
    plt.savefig(img_path)
    plt.close()

    # Envoi Telegram
    send_tg(rapport_tg, img_path)

if __name__ == "__main__":
    main()
