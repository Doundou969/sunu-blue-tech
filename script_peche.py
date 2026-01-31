import os
import json
import asyncio
import numpy as np
from datetime import datetime, timedelta
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
    console.print("[bold blue]📡 Synchronisation Copernicus...[/bold blue]")
    try:
        import copernicusmarine as cm
        DATASET_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        
        ds = cm.open_dataset(
            dataset_id=DATASET_ID,
            username=os.getenv("COPERNICUS_USERNAME"),
            password=os.getenv("COPERNICUS_PASSWORD")
        )

        now = datetime.utcnow()
        past_time = now - timedelta(hours=3)
        results = []

        for name, coords in ZONES.items():
            try:
                curr = ds.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                vhm0_now = float(curr["VHM0"].values)
                
                past = ds.sel(latitude=coords["lat"], longitude=coords["lon"], time=past_time, method="nearest")
                vhm0_past = float(past["VHM0"].values)

                trend = "↗" if vhm0_now > vhm0_past + 0.05 else "↘" if vhm0_now < vhm0_past - 0.05 else "→"
                vhm0 = round(vhm0_now, 2) if not np.isnan(vhm0_now) else 0.5

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "vhm0": vhm0, "trend": trend,
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
            except Exception:
                continue
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur Copernicus : {e}[/bold red]")
        return None

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id: return

    try:
        bot = Bot(token=token)
        date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
        
        msg = f"🌊 *BULLETIN PECHEURCONNECT*\n📅 _{date_str}_\n"
        msg += "------------------------------------\n\n"

        for d in data:
            icon = "🚩" if "DANGER" in d['alert'] else "✅"
            msg += f"{icon} *{d['zone']}*\n   🌊 Houle : {d['vhm0']}m ({d['trend']})\n   📊 État : {d['alert']}\n\n"

        msg += "------------------------------------\n🔗 [Carte en direct](https://doundou969.github.io/sunu-blue-tech/)"
        
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
        console.print("[bold green]📲 Bulletin envoyé.[/bold green]")
        
    except Exception as e:
        console.print(f"[red]❌ Erreur Telegram : {e}[/red]")

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
    else:
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
