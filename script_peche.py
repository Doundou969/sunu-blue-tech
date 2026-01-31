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
    console.print("[bold blue]📡 Synchronisation Copernicus (Vagues + Poissons)...[/bold blue]")
    try:
        import copernicusmarine as cm
        # IDs des Datasets 2026
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        PHY_ID = "cmems_mod_glo_phy_anfc_0.083deg_PT24H-i"
        
        # 1. Ouverture des datasets
        ds_wav = cm.open_dataset(dataset_id=WAV_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))
        ds_phy = cm.open_dataset(dataset_id=PHY_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))

        now = datetime.utcnow()
        past_time = now - timedelta(hours=3)
        results = []

        for name, coords in ZONES.items():
            try:
                # --- DONNÉES VAGUES ---
                curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                past_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=past_time, method="nearest")
                vhm0 = round(float(curr_wav["VHM0"].values), 2)
                vhm0_past = float(past_wav["VHM0"].values)
                trend = "↗" if vhm0 > vhm0_past + 0.05 else "↘" if vhm0 < vhm0_past - 0.05 else "→"

                # --- DONNÉES TEMPÉRATURE (POISSONS) ---
                curr_phy = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                temp = round(float(curr_phy["thetao"].values), 1)
                
                # Logique de pêche : Upwelling (eaux froides entre 17 et 22°C au Sénégal)
                if 17 <= temp <= 22:
                    fish_status = "🐟 Zone de Pêche Riche (Eau Froide)"
                    fish_icon = "🔵"
                else:
                    fish_status = "🌊 Eau Chaude (Moins de poissons)"
                    fish_icon = "🟡"

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "vhm0": vhm0, "trend": trend, "temp": temp,
                    "fish_status": fish_status, "fish_icon": fish_icon,
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
            except Exception: continue
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur : {e}[/bold red]"); return None

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id: return
    try:
        bot = Bot(token=token)
        msg = f"🚢 *PECHEURCONNECT : SÉCURITÉ & PÊCHE*\n📅 _{datetime.now().strftime('%d/%m/%Y')}_\n"
        msg += "------------------------------------\n\n"
        for d in data:
            msg += f"📍 *{d['zone']}*\n"
            msg += f"   🌊 Vagues : {d['vhm0']}m ({d['trend']}) -> {d['alert']}\n"
            msg += f"   🌡️ Temp : {d['temp']}°C | {d['fish_icon']} {d['fish_status']}\n\n"
        msg += "------------------------------------\n🔗 [Carte en direct](https://doundou969.github.io/sunu-blue-tech/)"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
    except Exception as e: console.print(f"[red]❌ Telegram : {e}[/red]")

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
        console.print("[bold green]✅ Données Sécurité + Pêche mises à jour ![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())
