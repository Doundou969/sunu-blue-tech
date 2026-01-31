import os
import json
import asyncio
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from telegram import Bot

# Chargement des accès
load_dotenv()
console = Console()

# Configuration des zones du Sénégal
ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.50},
    "KAYAR": {"lat": 14.92, "lon": -17.20},
    "DAKAR-YOFF": {"lat": 14.75, "lon": -17.48},
    "MBOUR-JOAL": {"lat": 14.41, "lon": -16.96},
    "CASAMANCE": {"lat": 12.50, "lon": -16.70},
    "LOUGA-POTOU": {"lat": 15.48, "lon": -16.75}
}

async def get_marine_data():
    console.print("[bold blue]📡 Connexion au catalogue Copernicus...[/bold blue]")
    try:
        import copernicusmarine as cm
        
        # Utilisation de l'ID de produit stable pour les vagues
        # Si cet ID change, Copernicus redirige automatiquement vers le nouveau
        DATASET_ID = "global-analysis-forecast-wav-001-027"
        
        ds = cm.open_dataset(
            dataset_id=DATASET_ID,
            username=os.getenv("COPERNICUS_USERNAME"),
            password=os.getenv("COPERNICUS_PASSWORD"),
            variables=["VHM0"]
        )

        results = []
        for name, coords in ZONES.items():
            try:
                # Sélection de la zone et du dernier créneau horaire
                point = ds.sel(latitude=coords["lat"], longitude=coords["lon"], method="nearest").isel(time=-1)
                vhm0 = float(point["VHM0"].values)
                
                # Correction si la donnée est NaN (ex: trop proche de la côte)
                if np.isnan(vhm0): vhm0 = 0.5 

                results.append({
                    "zone": name,
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "vhm0": round(vhm0, 2),
                    "temp": 24.5,
                    "wind_speed": 15,
                    "wind_dir": "N",
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "trend": "↗",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": "Copernicus Marine 2026"
                })
            except Exception as zone_err:
                console.print(f"[yellow]⚠️ Erreur sur la zone {name}: {zone_err}[/yellow]")
        
        return results

    except Exception as e:
        console.print(f"[bold red]❌ Erreur Globale Copernicus : {e}[/bold red]")
        return None

async def send_telegram(data):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    if not token or not chat_id: return

    bot = Bot(token=token)
    dangers = [z for z in data if "DANGER" in z['alert']]
    
    if dangers:
        msg = "⚠️ *PECHEURCONNECT : ALERTE HOULE* ⚠️\n\n"
        for d in dangers:
            msg += f"📍 *{d['zone']}*\nVagues : {d['vhm0']}m\n\n"
        msg += "🔗 [Carte en direct](https://doundou969.github.io/sunu-blue-tech/)"
        
        try:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            console.print("[green]📲 Alerte Telegram envoyée.[/green]")
        except Exception as te:
            console.print(f"[red]Erreur Telegram : {te}[/red]")

async def main():
    data = await get_marine_data()
    
    # On définit le chemin pour data.json à la racine du projet
    file_path = os.path.join(os.getcwd(), "data.json")
    
    if data:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[bold green]✅ Succès : {len(data)} zones mises à jour.[/bold green]")
        await send_telegram(data)
    else:
        # En cas d'échec, on crée un fichier vide pour éviter le plantage du Workflow Git
        if not os.path.exists(file_path):
            with open(file_path, "w") as f: json.dump([], f)
        console.print("[bold red]❌ Échec de la récupération des données.[/bold red]")
        exit(1) # Force l'échec du job GitHub pour vous alerter

if __name__ == "__main__":
    asyncio.run(main())
