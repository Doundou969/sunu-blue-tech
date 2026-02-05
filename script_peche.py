import os
import json
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Remplacez par les coordonnées réelles si nécessaire
ZONES = {
    "Saint-Louis": {"lat": 16.03, "lon": -16.51},
    "Kayar": {"lat": 14.91, "lon": -17.12},
    "Dakar": {"lat": 14.68, "lon": -17.44},
    "Mbour": {"lat": 14.41, "lon": -16.96},
    "Ziguinchor": {"lat": 12.58, "lon": -16.27}
}

def send_telegram_alert(zone, vagues, securite):
    """Envoie une notification Telegram en cas de danger"""
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    
    if not token or not chat_id:
        print(f"⚠️ Erreur Telegram : Secrets manquants (Token ou ID).")
        return

    message = (
        f"🚨 *ALERTE DANGER MÉTÉO - PECHEURCONNECT*\n\n"
        f"📍 *Zone* : {zone}\n"
        f"🌊 *Vagues* : {vagues}m\n"
        f"📢 *Statut* : {securite}\n\n"
        f"🔗 [Voir la carte en direct](https://doundou969.github.io/)"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id, 
            "text": message, 
            "parse_mode": "Markdown"
        })
        if r.status_code == 200:
            print(f"✅ Notification envoyée pour {zone}")
        else:
            print(f"❌ Erreur API Telegram : {r.text}")
    except Exception as e:
        print(f"❌ Erreur réseau Telegram : {e}")

def run_pecheur_connect():
    print(f"🚀 Démarrage de la mise à jour : {datetime.now()}")
    
    all_results = []
    now = datetime.now()

    for name, coord in ZONES.items():
        forecasts = []
        # Simulation/Récupération des données pour 3 jours (J, J+1, J+2)
        for i in range(3):
            target_date = now + timedelta(days=i)
            
            # --- LOGIQUE SCIENTIFIQUE (Copernicus) ---
            # Ici, les valeurs sont simulées pour l'exemple. 
            # En production, utilisez xarray pour extraire les vraies valeurs.
            v_wave = 1.2 + (i * 0.3)  # Hauteur des vagues
            temp_mer = 21.0 + i       # Température (Upwelling si < 23)
            curr_speed = 0.4 + (i * 0.1)
            
            # Détermination de la sécurité
            safety = "🟢 SÛR"
            if v_wave > 2.2 or curr_speed > 0.7:
                safety = "🔴 DANGER"
            elif v_wave > 1.8:
                safety = "🟡 VIGILANCE"

            # Envoi Telegram : Uniquement si DANGER et uniquement pour AUJOURD'HUI (i=0)
            if safety == "🔴 DANGER" and i == 0:
                send_telegram_alert(name, round(v_wave, 2), safety)

            # Indice de pêche (Upwelling)
            idx = "Excellent 🐟🐟🐟" if temp_mer < 23 else "Moyen 🐟"

            forecasts.append({
                "jour": target_date.strftime("%A"),
                "v_now": round(v_wave, 2),
                "t_now": round(temp_mer, 1),
                "c_now": round(curr_speed, 2),
                "safety": safety,
                "index": idx
            })

        all_results.append({
            "zone": name,
            "lat": coord["lat"],
            "lon": coord["lon"],
            "date_update": now.strftime("%H:%M"),
            "forecasts": forecasts
        })

    # Sauvegarde finale pour index.html
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)
    
    print("💾 Fichier data.json mis à jour avec succès.")

if __name__ == "__main__":
    run_pecheur_connect()
