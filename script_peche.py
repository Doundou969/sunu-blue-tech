import os, json, asyncio, requests, numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from rich.console import Console
from telegram import Bot

load_dotenv()
console = Console()

# Coordonnées ajustées pour éviter la terre ferme (Correction du "nan")
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65},
    "KAYAR": {"lat": 14.95, "lon": -17.35},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95}
}

def get_forecast_data(lat, lon):
    """Récupère Température + Prévisions Vagues demain via Open-Meteo"""
    try:
        # API Marine pour les vagues de demain
        url_wave = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&daily=wave_height_max&timezone=GMT"
        r_wave = requests.get(url_wave, timeout=10).json()
        wave_tomorrow = r_wave['daily']['wave_height_max'][1]

        # API Forecast pour la température (7 jours passés + 2 jours futur)
        url_temp = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m&past_days=7&forecast_days=2"
        r_temp = requests.get(url_temp, timeout=10).json()
        
        temps = r_temp['hourly']['temperature_2m']
        dates = r_temp['hourly']['time']
        
        return {
            "current_temp": round(temps[-1], 1),
            "tomorrow_wave": round(wave_tomorrow, 2) if wave_tomorrow else "N/A",
            "history_values": [round(t, 1) for t in temps[-168::24]],
            "history_dates": dates[-168::24]
        }
    except Exception as e:
        console.print(f"[yellow]⚠️ Erreur API externe : {e}[/yellow]")
        return {"current_temp": "N/A", "tomorrow_wave": "N/A", "history_values": [], "history_dates": []}

async def send_telegram(data):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    if not token or not chat_id: return
    
    try:
        bot = Bot(token=token)
        msg = "🚢 *PECHEURCONNECT : RAPPORT & PRÉVISIONS*\n"
        msg += f"📅 _Le {datetime.now().strftime('%d/%m/%Y à %H:%M')}_\n\n"
        
        for d in data:
            # Logique d'alerte demain
            alert_tomorrow = "⚠️ *PRUDENCE DEMAIN*" if (isinstance(d['tomorrow_wave'], float) and d['tomorrow_wave'] >= 2.1) else "✅ Calme demain"
            
            msg += f"📍 *{d['zone']}*\n"
            msg += f"🌊 Aujourd'hui : `{d['vhm0']}m`\n"
            msg += f"🔮 Demain (max) : `{d['tomorrow_wave']}m` ({alert_tomorrow})\n"
            msg += f"🌡️ Temp : `{d['temp']}°C` | {d['fish_status']}\n\n"
        
        msg += "📢 _Partagez ces infos pour sauver des vies._"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
        console.print("[green]🚀 Rapport prédictif envoyé sur Telegram ![/green]")
    except Exception as e:
        console.print(f"[bold red]❌ Erreur Telegram : {e}[/bold red]")

async def get_marine_data():
    console.print("[bold blue]📡 Analyse Sécurité & Prévisions...[/bold blue]")
    try:
        import copernicusmarine as cm
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        ds_wav = cm.open_dataset(dataset_id=WAV_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))
        
        now = datetime.utcnow()
        results = []
        for name, coords in ZONES.items():
            # 1. Vagues Temps Réel (Copernicus)
            curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
            raw_vhm0 = curr_wav["VHM0"].values
            vhm0 = round(float(raw_vhm0), 2) if not np.isnan(raw_vhm0) else "N/A"
            
            # 2. Température + Prévisions (Open-Meteo)
            forecast = get_forecast_data(coords["lat"], coords["lon"])
            
            results.append({
                "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                "vhm0": vhm0, 
                "temp": forecast["current_temp"],
                "tomorrow_wave": forecast["tomorrow_wave"],
                "history": {"dates": forecast["history_dates"], "values": forecast["history_values"]},
                "fish_status": "🐟 Zone Riche" if (forecast["current_temp"] != "N/A" and forecast["current_temp"] <= 22) else "🌊 Zone Pauvre",
                "alert": "🔴 DANGER" if (vhm0 != "N/A" and vhm0 >= 2.2) else "🟢 OK",
                "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
            })
            console.print(f"[green]✔ Données OK pour {name}[/green]")
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur Copernicus : {e}[/bold red]"); return None

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
    else: exit(1)

if __name__ == "__main__":
    asyncio.run(main())
