import os
import requests
import copernicusmarine
import datetime

# --- RÉCUPÉRATION ---
user = os.getenv("COPERNICUS_USERNAME")
pw = os.getenv("COPERNICUS_PASSWORD")
tg_token = os.getenv("TG_TOKEN")
tg_id = os.getenv("TG_ID")

def test_telegram(message):
    """Fonction isolée pour tester l'envoi Telegram"""
    print(f"📡 Tentative d'envoi Telegram vers {tg_id}...")
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": tg_id, "text": message})
        if r.status_code == 200:
            print("✅ TELEGRAM : Message reçu par les serveurs de Telegram !")
        else:
            print(f"❌ TELEGRAM : Erreur {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ TELEGRAM : Erreur de connexion - {e}")

def job():
    print("--- DÉBUT DU DIAGNOSTIC ---")
    
    # ÉTAPE A : Tester les secrets
    if not all([user, pw, tg_token, tg_id]):
        print(f"❌ SECRETS : Certains secrets sont vides !")
        print(f"User: {'OK' if user else 'VIDE'}, Pass: {'OK' if pw else 'VIDE'}")
        print(f"Token: {'OK' if tg_token else 'VIDE'}, ID: {'OK' if tg_id else 'VIDE'}")
        return

    # ÉTAPE B : Tester Telegram tout de suite (Avant Copernicus)
    test_telegram("🚀 Sunu-Blue-Tech : Le script vient de démarrer sur GitHub !")

    # ÉTAPE C : Connexion Copernicus
    try:
        print(f"🚀 Connexion Copernicus ({user})...")
        copernicusmarine.login(username=user, password=pw, force_persist=True)
        print("✅ COPERNICUS : Connexion réussie !")
        
        # Test d'envoi final
        test_telegram("🌊 Connexion Copernicus OK ! Le système est prêt.")
        
    except Exception as e:
        print(f"❌ COPERNICUS : Erreur de connexion - {e}")
        test_telegram(f"❌ Erreur Copernicus : {e}")

if __name__ == "__main__":
    job()
