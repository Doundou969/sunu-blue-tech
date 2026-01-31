import os, json, asyncio, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.50},
    "KAYAR": {"lat": 14.92, "lon": -17.20},
    "DAKAR-YOFF": {"lat": 14.75, "lon": -17.48},
    "MBOUR-JOAL": {"lat": 14.41, "lon": -16.96},
    "CASAMANCE": {"lat": 12.50, "lon": -16.70}
}

def get_temp_open_meteo(lat, lon):
    """Récupère la température et l'historique via Open-Meteo (Sans login)"""
    try:
        url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height&daily=wave_height_max&timezone=GMT"
        # Pour la température pure, Open-Meteo utilise souvent l'API météo classique même sur mer
        url_temp = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m&past_days=7&forecast_days=1"
        r = requests.get(url_temp, timeout=10).json()
        
        temps = r['hourly']['temperature_2m']
        dates = r['hourly']['time']
        
        # On prend une mesure par jour pour l'historique (toutes les 24h)
        return {
            "current": temps[-1],
            "values": temps[-168::24], # 7 derniers jours
            "dates": dates[-168::24]
        }
    except:
        return {"current": "N/A", "values": [], "dates": []}

async def get_marine_data():
    console.print("[bold blue]📡 Synchronisation Hybride (Copernicus + Open-Meteo)...[/bold blue]")
    try:
        import copernicusmarine as cm
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        
        ds_wav = cm.open_dataset(
            dataset_id=WAV_ID, 
            username=os.getenv("COPERNICUS_USERNAME"), 
            password=os.getenv("COPERNICUS_PASSWORD")
        )

        now = datetime.utcnow()
        results = []

        for name, coords in ZONES.items():
            # 1. Vagues via Copernicus
            curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
            vhm0 = round(float(curr_wav["VHM0"].values), 2)

            # 2. Température via Open-Meteo (Plus d'erreur 404 !)
            temp_data = get_temp_open_meteo(coords["lat"], coords["lon"])
            
            results.append({
                "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                "vhm0": vhm0, "trend": "→", 
                "temp": temp_data["current"],
                "history": {"dates": temp_data["dates"], "values": temp_data["values"]},
                "fish_status": "🐟 Zone Riche" if (temp_data["current"] != "N/A" and temp_data["current"] <= 22) else "🌊 Zone Pauvre",
                "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
            })
            console.print(f"[green]✔ {name} mis à jour.[/green]")
        
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur : {e}[/bold red]")
        return None

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else: exit(1)

if __name__ == "__main__":
    asyncio.run(main())
