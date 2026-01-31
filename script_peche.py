import os
import json
import asyncio
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from telegram import Bot

load_dotenv()
console = Console()

# Zones stratégiques du Sénégal
ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.50},
    "KAYAR": {"lat": 14.92, "lon": -17.20},
    "DAKAR-YOFF": {"lat": 14.75, "lon": -17.48},
    "MBOUR-JOAL": {"lat": 14.41, "lon": -16.96},
    "CASAMANCE": {"lat": 12.50, "lon": -16.70},
    "LOUGA-POTOU": {"lat": 15.48, "lon": -16.75}
}

async def get_marine_data():
    console.print("[bold blue]📡 Connexion au Data Store Copernicus (METEOFRANCE)...[/bold blue]")
    try:
        import copernicusmarine as cm
        
        # ID EXACT correspondant au visualiseur Expert de 2026
        # Ce dataset contient la variable 'VHM0' (Hauteur significative des vagues)
        DATASET_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        
        # Connexion au Dataset
        ds = cm.open_dataset(
            dataset_id=DATASET_ID,
            username=os.getenv("COPERNICUS_USERNAME"),
            password=os.getenv("COPERNICUS_PASSWORD")
        )

        results = []
        # On récupère le dernier pas de temps disponible (Time-1)
        latest_time = ds.time.values[-1]
        console.print(f"[yellow]🕒 Données du : {latest_time}[/yellow]")

        for name, coords in ZONES.items():
            try:
                # Extraction par coordonnées
                point = ds.sel(
                    latitude=coords["lat"], 
                    longitude=coords["lon"], 
                    method="nearest"
                ).isel(time=-1)
                
                vhm_val = point["VHM0"].values
                vhm0 = float(vhm_val) if not np.isnan(vhm_val) else 0.0

                results.append({
                    "zone": name,
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "vhm0": round(vhm0, 2),
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "timestamp": str(latest_time),
                    "source": "PecheurConnect / Copernicus"
                })
            except Exception as e:
                console.print(f"[red]⚠️ Erreur Zone {name}: {e}[/red]")
        
        return results

    except Exception as e:
        console.print(f"[bold red]❌ Erreur de connexion au Dataset :[/bold red] {e}")
        return None

async def send_telegram(data):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    if not token or not chat_id: return

    bot = Bot(token=token)
    dangers = [z for z in data if "DANGER" in z['alert']]
    
    if dangers:
        msg = "🚩 *ALERTE HOULE SÉNÉGAL*\n\n"
        for d in dangers:
            msg += f"• *{d['zone']}* : {d['vhm0']}m\n"
        msg += "\n🔗 [Carte PecheurConnect](https://doundou969.github.io/sunu-blue-tech/)"
        
        try:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            console.print("[green]📲 Notification envoyée ![/green]")
        except Exception as te:
            console.print(f"[red]Telegram Error: {te}[/red]")

async def main():
    data = await get_marine_data()
    file_path = "data.json"
    
    if data:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print("[bold green]✅ Fichier data.json généré avec succès ![/bold green]")
        await send_telegram(data)
    else:
        # On crée un fichier de secours pour éviter le crash du workflow Git
        if not os.path.exists(file_path):
            with open(file_path, "w") as f: json.dump([], f)
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
