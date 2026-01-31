import os, json, asyncio, requests, numpy as np
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# Coordonnées décalées vers le large pour éviter le sable (Erreur nan et température faussée)
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65},
    "KAYAR": {"lat": 14.95, "lon": -17.35},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95}
}

def get_forecast(lat, lon):
    try:
        # Vagues (Marine API)
        r_w = requests.get(f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&daily=wave_height_max&timezone=GMT", timeout=10).json()
        # Température (Forecast API)
        r_t = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m&past_days=7&forecast_days=1", timeout=10).json()
        
        return {
            "t_now": round(r_t['hourly']['temperature_2m'][-1], 1),
            "w_tomorrow": round(r_w['daily']['wave_height_max'][1], 2),
            "h_val": [round(t, 1) for t in r_t['hourly']['temperature_2m'][-168::24]],
            "h_dat": r_t['hourly']['time'][-168::24]
        }
    except:
        return {"t_now": 0, "w_tomorrow": 0, "h_val": [], "h_dat": []}

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id: return
    try:
        bot = Bot(token=token)
        msg = "🚢 *PECHEURCONNECT : RAPPORT & PRÉVISIONS*\n\n"
        for d in data:
            alert = "⚠️ PRUDENCE" if d['w_tomorrow'] >= 2.1 else "✅ CALME"
            msg += f"📍 *{d['zone']}*\n🌊 Aujourd'hui : `{d['v_now']}m`\n🔮 Demain : `{d['w_tomorrow']}m` ({alert})\n🌡️ Temp : `{d['t_now']}°C`\n\n"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
    except Exception as e: print(f"Erreur Telegram: {e}")

async def main():
    import copernicusmarine as cm
    ds = cm.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", 
                         username=os.getenv("COPERNICUS_USERNAME"), 
                         password=os.getenv("COPERNICUS_PASSWORD"))
    results = []
    for name, coords in ZONES.items():
        curr = ds.sel(latitude=coords["lat"], longitude=coords["lon"], time=datetime.utcnow(), method="nearest")
        v_now = round(float(curr["VHM0"].values), 2) if not np.isnan(curr["VHM0"].values) else 0
        ext = get_forecast(coords["lat"], coords["lon"])
        
        results.append({
            "zone": name, "lat": coords["lat"], "lon": coords["lon"],
            "v_now": v_now, "t_now": ext["t_now"], "w_tomorrow": ext["w_tomorrow"],
            "h_val": ext["h_val"], "h_dat": ext["h_dat"]
        })
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    await send_telegram(results)

if __name__ == "__main__":
    asyncio.run(main())
