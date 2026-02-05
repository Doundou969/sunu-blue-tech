import os, json, asyncio, numpy as np
import copernicusmarine as cm
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65},
    "KAYAR": {"lat": 14.95, "lon": -17.35},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95}
}

async def fetch_marine_data():
    results = []
    now = datetime.utcnow()
    user, pw = os.getenv("COPERNICUS_USERNAME"), os.getenv("COPERNICUS_PASSWORD")
    try:
        cm.login(username=user, password=pw)
        ds_temp = cm.open_dataset(dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i", username=user, password=pw)
        ds_cur = cm.open_dataset(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i", username=user, password=pw)
        ds_wav = cm.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", username=user, password=pw)

        for name, coords in ZONES.items():
            try:
                st = ds_temp.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                if 'depth' in st.coords: st = st.isel(depth=0)
                t_now = round(float(st["thetao"].values.flatten()[0]), 1)

                sc = ds_cur.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                if 'depth' in sc.coords: sc = sc.isel(depth=0)
                c_now = round(float(np.sqrt(float(sc["uo"].values.flatten()[0])**2 + float(sc["vo"].values.flatten()[0])**2)), 2)

                sw = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                v_now = round(float(sw["VHM0"].values.flatten()[0]), 2)

                safety = "🔴 DANGER" if v_now > 2.1 or c_now > 0.6 else "🟢 SÛR"
                fish = "🐟 ÉLEVÉ" if t_now < 22 else "🎣 MOYEN"

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "v_now": v_now, "t_now": t_now, "c_now": c_now,
                    "index": fish, "safety": safety,
                    "date": now.strftime("%d/%m %H:%M")
                })
            except: continue
    except: return None
    return results

def send_telegram_alert(data):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    if not token or not chat_id: return

    message = "🚢 *PECHEURCONNECT - RAPPORT DU JOUR*\n\n"
    for z in data:
        message += f"📍 *{z['zone']}*\n"
        message += f"{z['safety']} | Pêche: {z['index']}\n"
        message += f"🌊 Vagues: {z['v_now']}m | 🌡️ Temp: {z['t_now']}°C\n\n"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

async def main():
    data = await fetch_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        send_telegram_alert(data)
        print("🎉 data.json mis à jour et alerte Telegram envoyée !")

if __name__ == "__main__":
    asyncio.run(main())
