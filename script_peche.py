import os, json, asyncio, requests, numpy as np
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
    "CASAMANCE": {"lat": 12.50, "lon": -16.70}
}

def get_temp_data(lat, lon):
    """Récupère la température (7 jours) via Open-Meteo"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m&past_days=7&forecast_days=1"
        r = requests.get(url, timeout=10).json()
        temps = r['hourly']['temperature_2m']
        dates = r['hourly']['time']
        return {
            "current": round(temps[-1], 1),
            "values": [round(t, 1) for t in temps[-168::24]], # 1 point par jour
            "dates": dates[-168::24]
        }
    except Exception as e:
        console.print(f"[yellow]⚠️ Erreur Temp ({lat}): {e}[/yellow]")
        return {"current": "N/A", "values": [], "dates": []}

async def send_telegram(data):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    if not token or not chat_id: return
    try:
        bot = Bot(token=token)
        msg = "🚢 *PECHEURCONNECT : RAPPORT DU JOUR*\n\n"
        for d in data:
            msg += f"📍 *{d['zone']}*\n🌊 Houle: {d['vhm0']}m\n🌡️ Temp: {d['temp']}°C | {d['fish_status']}\n\n"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
        console.print("[green]🚀 Notification Telegram envoyée ![/green]")
    except Exception as e:
        console.print(f"[bold red]❌ Erreur Telegram : {e}[/bold red]")

async def get_marine_data():
    console.print("[bold blue]📡 Synchronisation Hybride en cours...[/bold blue]")
    try:
        import copernicusmarine as cm
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        ds_wav = cm.open_dataset(dataset_id=WAV_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))
        
        now = datetime.utcnow()
        results = []
        for name, coords in ZONES.items():
            # 1. Houle (Copernicus)
            curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
            vhm0 = round(float(curr_wav["VHM0"].values), 2)
            
            # 2. Température (Open-Meteo)
            temp_info = get_temp_data(coords["lat"], coords["lon"])
            
            results.append({
                "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                "vhm0": vhm0, "temp": temp_info["current"],
                "history": {"dates": temp_info["dates"], "values": temp_info["values"]},
                "fish_status": "🐟 Zone Riche" if (temp_info["current"] != "N/A" and temp_info["current"] <= 22) else "🌊 Zone Pauvre",
                "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
            })
            console.print(f"[green]✔ {name} : OK[/green]")
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur Globale : {e}[/bold red]"); return None

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
    else: exit(1)

if __name__ == "__main__": asyncio.run(main())
