import os, json, asyncio, numpy as np
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
    console.print("[bold blue]📡 Analyse Sécurité + Upwelling (Vérification ID 2026)...[/bold blue]")
    try:
        import copernicusmarine as cm
        
        # IDENTIFIANTS CORRIGÉS POUR 2026
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        PHY_ID = "cmems_mod_glo_phy_anfc_0.083deg_PT1D-m" # Nouveau format standard

        # Ouverture des datasets avec authentification
        ds_wav = cm.open_dataset(
            dataset_id=WAV_ID, 
            username=os.getenv("COPERNICUS_USERNAME"), 
            password=os.getenv("COPERNICUS_PASSWORD")
        )
        ds_phy = cm.open_dataset(
            dataset_id=PHY_ID, 
            username=os.getenv("COPERNICUS_USERNAME"), 
            password=os.getenv("COPERNICUS_PASSWORD")
        )

        now = datetime.utcnow()
        results = []

        for name, coords in ZONES.items():
            try:
                # 🌊 DONNÉES VAGUES
                curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                vhm0 = round(float(curr_wav["VHM0"].values), 2)
                
                # Comparaison 3h avant pour la tendance
                past_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now - timedelta(hours=3), method="nearest")
                vhm0_past = float(past_wav["VHM0"].values)
                trend = "↗" if vhm0 > vhm0_past + 0.05 else "↘" if vhm0 < vhm0_past - 0.05 else "→"

                # 🌡️ TEMPÉRATURE (7 jours)
                start_date = now - timedelta(days=7)
                hist_phy = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=slice(start_date, now), method="nearest")
                
                # Conversion des données en listes propres
                temps_hist = [round(float(t), 1) for t in hist_phy["thetao"].values if not np.isnan(t)]
                dates_hist = [str(d)[:10] for d in hist_phy["time"].values]
                
                current_temp = temps_hist[-1]

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "vhm0": vhm0, "trend": trend, "temp": current_temp,
                    "history": {"dates": dates_hist, "values": temps_hist},
                    "fish_status": "🐟 Zone Riche (Eau froide)" if current_temp <= 22 else "🌊 Zone Pauvre",
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
            except Exception as ze:
                console.print(f"[yellow]⚠️ Zone {name} ignorée : {ze}[/yellow]")
                continue
                
        return results
    except Exception as e:
        console.print(f"[bold red]❌ Erreur fatale : {e}[/bold red]")
        return None

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not (token and chat_id): return
    try:
        bot = Bot(token=token)
        msg = f"🚢 *PECHEURCONNECT : RAPPORT DU {datetime.now().strftime('%d/%m/%Y')}*\n\n"
        for d in data:
            msg += f"📍 *{d['zone']}*\n🌊 Houle: {d['vhm0']}m ({d['trend']})\n🌡️ Temp: {d['temp']}°C | {d['fish_status']}\n\n"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
        console.print("[green]📲 Telegram envoyé.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Erreur Telegram : {e}[/red]")

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
        console.print("[bold green]✅ Tout est à jour ![/bold green]")
    else:
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
