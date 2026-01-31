import os, json, asyncio, numpy as np
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

async def get_marine_data():
    console.print("[bold blue]📡 Mode Sécurité : Récupération des vagues...[/bold blue]")
    try:
        import copernicusmarine as cm
        
        # Connexion au Dataset Vagues (Très stable)
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        ds_wav = cm.open_dataset(
            dataset_id=WAV_ID, 
            username=os.getenv("COPERNICUS_USERNAME"), 
            password=os.getenv("COPERNICUS_PASSWORD")
        )

        now = datetime.utcnow()
        results = []

        for name, coords in ZONES.items():
            try:
                # Récupération Houle
                curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                vhm0 = round(float(curr_wav["VHM0"].values), 2)
                
                # Tendance simple
                past_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now - timedelta(hours=3), method="nearest")
                vhm0_past = float(past_wav["VHM0"].values)
                trend = "↗" if vhm0 > vhm0_past + 0.05 else "↘" if vhm0 < vhm0_past - 0.05 else "→"

                # Données de secours pour la pêche (puisque PHY plante)
                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "vhm0": vhm0, "trend": trend, "temp": "N/A",
                    "history": {"dates": [], "values": []},
                    "fish_status": "Analyse pêche indisponible",
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
                console.print(f"[green]✔ {name} : {vhm0}m[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Zone {name} erreur : {e}[/yellow]")
        
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur Copernicus : {e}[/bold red]")
        return None

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print("[bold green]✅ data.json mis à jour avec les vagues ![/bold green]")
    else:
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
