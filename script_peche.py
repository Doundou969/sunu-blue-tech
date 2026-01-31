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

ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.50},
    "KAYAR": {"lat": 14.92, "lon": -17.20},
    "DAKAR-YOFF": {"lat": 14.75, "lon": -17.48},
    "MBOUR-JOAL": {"lat": 14.41, "lon": -16.96},
    "CASAMANCE": {"lat": 12.50, "lon": -16.70},
    "LOUGA-POTOU": {"lat": 15.48, "lon": -16.75}
}

async def get_marine_data():
    console.print("[bold blue]📡 Tentative de connexion au catalogue 2026...[/bold blue]")
    try:
        import copernicusmarine as cm
        
        # Nouvel ID de Dataset (Nomenclature 2026)
        # Note : On cible le produit "Instantaneous" pour avoir la houle actuelle
        DATASET_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        
        ds = cm.open_dataset(
            dataset_id=DATASET_ID,
            username=os.getenv("COPERNICUS_USERNAME"),
            password=os.getenv("COPERNICUS_PASSWORD"),
            variables=["VHM0"]
        )

        results = []
        for name, coords in ZONES.items():
            try:
                # On sélectionne le dernier point disponible dans le temps
                point = ds.sel(latitude=coords["lat"], longitude=coords["lon"], method="nearest").isel(time=-1)
                vhm = point["VHM0"].values
                
                # Gestion des données terrestres ou manquantes
                vhm0 = float(vhm) if not np.isnan(vhm) else 0.5

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
                    "source": "Copernicus 2026"
                })
            except Exception as e:
                console.print(f"[yellow]⚠️ Zone {name} ignorée : {e}[/yellow]")
        
        return results

    except Exception as e:
        console.print(f"[bold red]❌ Erreur ID Dataset : {e}[/bold red]")
        console.print("[cyan]💡 Conseil : Connectez-vous sur marine.copernicus.eu pour valider les nouvelles conditions d'utilisation.[/cyan]")
        return None

async def main():
    data = await get_marine_data()
    file_path = os.path.join(os.getcwd(), "data.json")
    
    if data:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[bold green]✅ Succès ! data.json mis à jour.[/bold green]")
        
        # Envoi Telegram
        token, cid = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
        if token and cid:
            bot = Bot(token=token)
            dangers = [z for z in data if "DANGER" in z['alert']]
            if dangers:
                msg = "🚩 *PecheurConnect ALERTE*\n" + "\n".join([f"• {d['zone']}: {d['vhm0']}m" for d in dangers])
                await bot.send_message(chat_id=cid, text=msg, parse_mode='Markdown')
    else:
        # On évite de laisser Git sans fichier
        if not os.path.exists(file_path):
            with open(file_path, "w") as f: json.dump([], f)
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
