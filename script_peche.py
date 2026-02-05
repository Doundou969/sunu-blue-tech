import xarray as xr
import json
from datetime import datetime, timedelta

# Configuration des zones (Coordonnées du Sénégal)
ZONES = {
    "Saint-Louis": {"lat": 16.03, "lon": -16.51},
    "Kayar": {"lat": 14.91, "lon": -17.12},
    "Dakar": {"lat": 14.68, "lon": -17.44},
    "Mbour": {"lat": 14.41, "lon": -16.96},
    "Ziguinchor": {"lat": 12.58, "lon": -16.27}
}

def get_forecast_data():
    all_data = []
    # Simulation de l'accès aux fichiers Copernicus (Motem ou OPeNDAP)
    # Pour l'Upwelling et les prévisions J+1, J+2
    
    now = datetime.now()
    
    for name, coords in ZONES.items():
        zone_forecasts = []
        for day in range(3): # Aujourd'hui, Demain, Après-demain
            forecast_date = now + timedelta(days=day)
            
            # Simulation des calculs (remplacer par l'extraction xarray réelle)
            v_wave = 1.2 + (day * 0.3) # Exemple de vagues qui montent
            temp_mer = 22.5 # Si < 24°C = Upwelling actif (Zone riche en poisson)
            courant = 0.4
            
            # Analyse de sécurité
            status = "🟢 SÛR"
            if v_wave > 2.2 or courant > 0.7:
                status = "🔴 DANGER"
            elif v_wave > 1.8:
                status = "🟡 VIGILANCE"

            # Analyse Upwelling (Indice de pêche)
            peche_idx = "Excellent 🐟🐟🐟" if temp_mer < 23 else "Moyen 🐟"

            zone_forecasts.append({
                "jour": forecast_date.strftime("%A"),
                "v_now": round(v_wave, 2),
                "t_now": temp_mer,
                "c_now": courant,
                "safety": status,
                "index": peche_idx
            })
        
        all_data.append({
            "zone": name,
            "lat": coords["lat"],
            "lon": coords["lon"],
            "forecasts": zone_forecasts,
            "date_update": now.strftime("%H:%M")
        })

    with open('data.json', 'w') as f:
        json.dump(all_data, f, indent=4)

if __name__ == "__main__":
    get_forecast_data()
