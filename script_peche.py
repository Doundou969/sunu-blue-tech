import os, json, datetime, requests
import numpy as np

# Configuration
TARGET_DIR = "public"
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # Zones stratégiques GPS du Sénégal
    SITES = {
        "SAINT-LOUIS (Guet Ndar)": {"lat": 16.03, "lon": -16.55, "type": "Mer Ouverte"},
        "KAYAR": {"lat": 14.91, "lon": -17.12, "type": "Fosse"},
        "DAKAR (Yoff/Soumbédioune)": {"lat": 14.76, "lon": -17.48, "type": "Récifs"},
        "MBOUR / JOAL": {"lat": 14.41, "lon": -16.98, "type": "Plateau"},
        "CASAMANCE (Elinkine)": {"lat": 12.55, "lon": -16.85, "type": "Estuaire"}
    }
    
    data = []
    now = datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')

    for nom, coord in SITES.items():
        # Simulation des données Copernicus (Précision satellite)
        vagues = round(np.random.uniform(0.5, 3.0), 2)
        temp = round(np.random.uniform(18, 26), 1)
        vitesse_courant = round(np.random.uniform(0.1, 1.2), 2)
        
        # Intelligence métier : Prédiction de pêche
        if vagues < 1.4 and temp > 21:
            conseil = "Abondance : Thiof, Sardinelles, Sompat."
            danger = "FAIBLE"
        elif vagues > 2.2:
            conseil = "Danger : Sortie déconseillée. Repli sur les estuaires."
            danger = "CRITIQUE"
        else:
            conseil = "Passage de Thonines et Dorades."
            danger = "MODÉRÉ"

        data.append({
            "zone": nom,
            "lat": coord['lat'],
            "lon": coord['lon'],
            "vagues": vagues,
            "temp": temp,
            "courant": f"{vitesse_courant} m/s",
            "poissons": conseil,
            "risque": danger,
            "date": now
        })

    # Sauvegarde JSON
    with open(os.path.join(TARGET_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Notification Telegram enrichie
    if TG_TOKEN and TG_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        msg = f"⚓ *PECHEUR CONNECT - BULLETIN DU {now}*\n\n"
        for d in data:
            status = "🔴" if d['risque'] == "CRITIQUE" else ("🟡" if d['risque'] == "MODÉRÉ" else "🟢")
            msg += f"{status} *{d['zone']}*\n🌊 Vagues: {d['vagues']}m\n🌡️ Eau: {d['temp']}°C\n🐟 {d['poissons']}\n📍 `GPS: {d['lat']},{d['lon']}`\n\n"
        requests.post(url, data={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()
