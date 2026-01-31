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
    console.print("[bold blue]📡 Analyse Sécurité + Upwelling (7 jours)...[/bold blue]")
    try:
        import copernicusmarine as cm
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        PHY_ID = "cmems_mod_glo_phy_anfc_0.083deg_PT24H-i"
        
        ds_wav = cm.open_dataset(dataset_id=WAV_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))
        ds_phy = cm.open_dataset(dataset_id=PHY_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))

        now = datetime.utcnow()
        results = []

        for name, coords in ZONES.items():
            try:
                # --- VAGUES (Actuel) ---
                curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                vhm0 = round(float(curr_wav["VHM0"].values), 2)

                # --- TEMPÉRATURE (Historique 7 jours) ---
                # On récupère une plage de temps
                start_date = now - timedelta(days=7)
                hist_phy = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=slice(start_date, now), method="nearest")
                
                # Extraction des valeurs et des dates pour le graphique
                temps_hist = [round(float(t), 1) for t in hist_phy["thetao"].values]
                dates_hist = [str(d)[:10] for d in hist_phy["time"].values]
                
                current_temp = temps_hist[-1]
                
                # Calcul de la tendance de température (7 jours)
                temp_trend = "🥶 Refroidissement" if temps_hist[-1] < temps_hist[0] else "🔥 Réchauffement"

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "vhm0": vhm0, "temp": current_temp,
                    "temp_trend": temp_trend,
                    "history": {"dates": dates_hist, "values": temps_hist},
                    "fish_status": "🐟 Zone Riche" if current_temp <= 22 else "🌊 Zone Pauvre",
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
            except Exception as e:
                console.print(f"⚠️ Erreur zone {name}: {e}")
                continue
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur Copernicus : {e}[/bold red]"); return None

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id: return
    bot = Bot(token=token)
    msg = f"📊 *RAPPORT PÊCHE & SÉCURITÉ*\n📅 _{datetime.now().strftime('%d/%m/%Y')}_\n\n"
    for d in data:
        msg += f"📍 *{d['zone']}*\n🌊 Houle: {d['vhm0']}m | 🌡️ Temp: {d['temp']}°C\n📈 Evolution: {d['temp_trend']}\n\n"
    await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
        console.print("[bold green]✅ Données et Historique mis à jour ![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())
