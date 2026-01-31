import os, json, asyncio, requests, numpy as np
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# Coordonnées optimisées pour le large (Évite le sable et les erreurs de température)
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65},
    "KAYAR": {"lat": 14.95, "lon": -17.35},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95}
}

def get_external_data(lat, lon):
    try:
        # Marine API pour les vagues demain
        r_wave = requests.get(f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&daily=wave_height_max&timezone=GMT", timeout=10).json()
        wave_tomorrow = r_wave['daily']['wave_height_max'][1]

        # Forecast API pour température (7j passé + 1j futur)
        r_temp = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m&past_days=7&forecast_days=1", timeout=10).json()
        temps = r_temp['hourly']['temperature_2m']
        dates = r_temp['hourly']['time']
        
        return {
            "temp": round(temps[-1], 1),
            "tomorrow_wave": round(wave_tomorrow, 2) if wave_tomorrow else 0,
            "h_values": [round(t, 1) for t in temps[-168::24]],
            "h_dates": dates[-168::24]
        }
    except:
        return {"temp": 0, "tomorrow_wave": 0, "h_values": [], "h_dates": []}

async def get_marine_data():
    import copernicusmarine as cm
    ds_wav = cm.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", 
                             username=os.getenv("COPERNICUS_USERNAME"), 
                             password=os.getenv("COPERNICUS_PASSWORD"))
    now = datetime.utcnow()
    results = []
    for name, coords in ZONES.items():
        curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
        vhm0 = round(float(curr_wav["VHM0"].values), 2) if not np.isnan(curr_wav["VHM0"].values) else 0
        
        ext = get_external_data(coords["lat"], coords["lon"])
        results.append({
            "zone": name, "lat": coords["lat"], "lon": coords["lon"],
            "vhm0": vhm0, "temp": ext["temp"], "tomorrow_wave": ext["tomorrow_wave"],
            "history": {"dates": ext["h_dates"], "values": ext["h_values"]},
            "fish_status": "🐟 Zone Riche" if ext["temp"] <= 22 else "🌊 Zone Pauvre"
        })
    return results

async def main():
    data = await get_marine_data()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
