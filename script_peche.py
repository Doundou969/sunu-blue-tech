import copernicusmarine
import xarray as xr
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION DES PORTS SÉNÉGALAIS ---
ZONES = {
    "Saint-Louis": {"lat": 16.03, "lon": -16.51},
    "Kayar": {"lat": 14.91, "lon": -17.12},
    "Dakar": {"lat": 14.68, "lon": -17.44},
    "Mbour": {"lat": 14.41, "lon": -16.96},
    "Ziguinchor": {"lat": 12.58, "lon": -16.27}
}

def fetch_marine_data():
    username = os.getenv("COPERNICUS_USERNAME")
    password = os.getenv("COPERNICUS_PASSWORD")
    
    # Dates pour les prévisions (Aujourd'hui à J+2)
    start_date = datetime.now()
    end_date = start_date + timedelta(days=2)

    all_results = []

    try:
        # 1. RÉCUPÉRATION DES DONNÉES (Vagues & Température)
        # On utilise le dataset global de Copernicus (Exemple simplifié)
        print("Connexion à Copernicus...")
        
        # Note: Dans une version réelle, on chargerait le dataset spécifique :
        # 'cmems_mod_glo_phy-cur_anfc_0.083deg_PT1H-m' pour le courant/temp
        # 'cmems_mod_glo_wav_anfc_0.083deg_PT3H-i' pour les vagues

        for name, coord in ZONES.items():
            forecasts = []
            for i in range(3): # Boucle sur 3 jours
                current_target = start_date + timedelta(days=i)
                
                # --- SIMULATION DE CALCULS SCIENTIFIQUES (Basé sur les grilles Copernicus) ---
                # Dans le script final, ces valeurs viendraient de ds.sel(lat=..., lon=...)
                v_wave = 1.1 + (i * 0.2)  # Hauteur des vagues
                temp_mer = 21.5 + i        # Température (Upwelling si < 23°C)
                speed_curr = 0.3 + (i * 0.1) # Vitesse courant
                
                # --- LOGIQUE DE SÉCURITÉ ---
                safety_status = "🟢 SÛR"
                if v_wave > 2.2 or speed_curr > 0.7:
                    safety_status = "🔴 DANGER"
                elif v_wave > 1.8:
                    safety_status = "🟡 VIGILANCE"

                # --- INDICE DE PÊCHE (Upwelling) ---
                fish_idx = "Moyen 🐟"
                if temp_mer < 23:
                    fish_idx = "Excellent 🐟🐟🐟"
                elif temp_mer < 25:
                    fish_idx = "Bon 🐟🐟"

                forecasts.append({
                    "jour": current_target.strftime("%A"),
                    "v_now": round(v_wave, 2),
                    "t_now": round(temp_mer, 1),
                    "c_now": round(speed_curr, 2),
                    "safety": safety_status,
                    "index": fish_idx
                })

            all_results.append({
                "zone": name,
                "lat": coord["lat"],
                "lon": coord["lon"],
                "date_update": start_date.strftime("%H:%M"),
                "forecasts": forecasts
            })

        # 2. SAUVEGARDE DU JSON
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=4, ensure_ascii=False)
        
        print("Mise à jour réussie : data.json généré.")

    except Exception as e:
        print(f"Erreur lors de la mise à jour : {e}")

if __name__ == "__main__":
    fetch_marine_data()
