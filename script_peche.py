import os, json, asyncio, numpy as np
import copernicusmarine as cm
from datetime import datetime
from dotenv import load_dotenv

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
                # Température
                st = ds_temp.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                if 'depth' in st.coords: st = st.isel(depth=0)
                t_now = round(float(st["thetao"].values.flatten()[0]), 1)

                # Courants
                sc = ds_cur.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                if 'depth' in sc.coords: sc = sc.isel(depth=0)
                uo, vo = sc["uo"].values.flatten()[0], sc["vo"].values.flatten()[0]
                c_now = round(np.sqrt(uo**2 + vo**2), 2)

                # Vagues
                sw = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                v_now = round(float(sw["VHM0"].values.flatten()[0]), 2)

                # Sécurité et Indice
                safety = "DANGER" if v_now > 2.1 or c_now > 0.6 else "SÛR"
                fish = "ÉLEVÉ" if t_now < 22 else "MOYEN"

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "v_now": v_now, "t_now": t_now, "c_now": c_now,
                    "index": fish, "safety": safety,
                    "date": now.strftime("%H:%M")
                })
            except: continue
    except: return None
    return results

async def main():
    data = await fetch_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else: exit(1)

if __name__ == "__main__":
    asyncio.run(main())
