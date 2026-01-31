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
    console.print("[bold blue]📡 Accès Copernicus...[/bold blue]")
    try:
        import copernicusmarine as cm
        # On force l'utilisation des credentials pour GitHub Actions
        ds = cm.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H",
            username=os.getenv("COPERNICUS_USERNAME"),
            password=os.getenv("COPERNICUS_PASSWORD")
        )
        
        results = []
        for name, coords in ZONES.items():
            point = ds.sel(latitude=coords["lat"], longitude=coords["lon"], method="nearest").isel(time=-1)
            vhm0 = float(point["VHM0"].values)
            results.append({
                "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                "vhm0": round(vhm0, 2), "temp": 24.5, "wind_speed": 15, "wind_dir": "N",
                "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                "trend": "↗", "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "Copernicus Marine"
            })
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur : {e}[/bold red]")
        return None

async def main():
    data = await get_marine_data()
    if data:
        # Chemin absolu pour éviter l'erreur pathspec sur GitHub
        file_path = os.path.join(os.getcwd(), "data.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✅ Fichier généré : {file_path}[/green]")
        
        # Alerte Telegram
        token, cid = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
        if token and cid:
            bot = Bot(token=token)
            dangers = [z for z in data if "DANGER" in z['alert']]
            if dangers:
                msg = "⚠️ *ALERTE PECHEURCONNECT*\n" + "\n".join([f"- {d['zone']}: {d['vhm0']}m" for d in dangers])
                await bot.send_message(chat_id=cid, text=msg, parse_mode='Markdown')
    else:
        # Création d'un fichier vide pour éviter que le Workflow ne plante sur Git Add
        with open("data.json", "w") as f: json.dump([], f)
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
