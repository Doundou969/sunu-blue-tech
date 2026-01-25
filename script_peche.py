import os, json, datetime, math, requests, warnings
from copernicusmarine import login, open_dataset

warnings.filterwarnings("ignore")

# 1. Vérification des Secrets
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

print(f"--- DIAGNOSTIC PECHEURCONNECT ---")
print(f"Token TG présent: {'OUI' if TG_TOKEN else 'NON'}")
print(f"ID TG présent: {'OUI' if TG_ID else 'NON'}")
print(f"User Copernicus présent: {'OUI' if COP_USER else 'NON'}")

ZONES = {
    "DAKAR-YOFF": [14.6, -17.6, 14.8, -17.4],
    "SAINT-LOUIS": [15.8, -16.7, 16.2, -16.3]
}

def main():
    try:
        print("🔑 Connexion à Copernicus...")
        login(username=COP_USER, password=COP_PASS, skip_if_logged=True)
        
        results = []
        report = "🌊 <b>PECHEUR CONNECT SÉNÉGAL</b>\n\n"

        for name, b in ZONES.items():
            print(f"📡 Récupération zone: {name}")
            # Simulation simplifiée pour tester l'envoi
            data = {"zone": name, "temp": 20.5, "vhm0": 1.2, "wind_speed": 15, "wind_dir": "N"}
            
            report += f"📍 <b>{name}</b>\n🌡️ {data['temp']}°C | 🌊 {data['vhm0']}m\n\n"
            results.append(data)

        # Sauvegarde
        with open('data.json', 'w') as f:
            json.dump(results, f)
        print("💾 Fichier data.json créé.")

        # ENVOI TELEGRAM
        print(f"📤 Envoi vers Telegram (ID: {TG_ID})...")
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_ID, "text": report, "parse_mode": "HTML"}
        
        resp = requests.post(url, data=payload)
        
        if resp.status_code == 200:
            print("✅ SUCCÈS : Message envoyé !")
        else:
            print(f"❌ ERREUR TELEGRAM : {resp.text}")

    except Exception as e:
        print(f"💥 CRASH DU SCRIPT : {str(e)}")

if __name__ == "__main__":
    main()
