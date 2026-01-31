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
    console.print("[bold blue]📡 Analyse Sécurité + Upwelling (Vérification 2026)...[/bold blue]")
    try:
        import copernicusmarine as cm
        WAV_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
        PHY_ID = "cmems_mod_glo_phy_anfc_0.083deg_PT1D-m" 

        ds_wav = cm.open_dataset(dataset_id=WAV_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))
        ds_phy = cm.open_dataset(dataset_id=PHY_ID, username=os.getenv("COPERNICUS_USERNAME"), password=os.getenv("COPERNICUS_PASSWORD"))

        now = datetime.utcnow()
        results = []

        for name, coords in ZONES.items():
            try:
                # Vagues
                curr_wav = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                vhm0 = round(float(curr_wav["VHM0"].values), 2)
                
                # Historique Température
                start_date = now - timedelta(days=7)
                hist_phy = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=slice(start_date, now), method="nearest")
                temps_hist = [round(float(t), 1) for t in hist_phy["thetao"].values if not np.isnan(t)]
                dates_hist = [str(d)[:10] for d in hist_phy["time"].values]
                
                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "vhm0": vhm0, "trend": "→", "temp": temps_hist[-1],
                    "history": {"dates": dates_hist, "values": temps_hist},
                    "fish_status": "🐟 Zone Riche" if temps_hist[-1] <= 22 else "🌊 Zone Pauvre",
                    "alert": "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK",
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ")
                })
            except: continue
        return results
    except Exception as e:
        console.print(f"[red]❌ Erreur : {e}[/red]"); return None

async def main():
    data = await get_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
        # Bloc Telegram Optionnel ici
    else: exit(1)

if __name__ == "__main__": asyncio.run(main())
