import os, json, asyncio, requests, numpy as np
import copernicusmarine as cm
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

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
    user = os.getenv("COPERNICUS_USERNAME")
    pw = os.getenv("COPERNICUS_PASSWORD")

    try:
        print("🚀 Connexion aux services Copernicus...")
        cm.login(username=user, password=pw)

        print("📡 Chargement des datasets...")
        # Dataset Physique complet (Temp + Courants)
        ds_phy = cm.open_dataset(dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT6H-i", username=user, password=pw)
        # Dataset Vagues
        ds_wav = cm.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", username=user, password=pw)
        
        # Dataset Bio (Chlorophylle) - ID alternatif stable
        ds_bio = None
        try:
            ds_bio = cm.open_dataset(dataset_id="cmems_mod_glo_bio_anfc_0.25deg_P1D-m", username=user, password=pw)
        except Exception as b_err:
            print(f"⚠️ Bio indisponible, on continue sans chlorophylle.")

        for name, coords in ZONES.items():
            try:
                # --- PHYSIQUE ---
                p = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                # On s'assure de prendre la surface (depth=0.5 environ)
                if 'depth' in p.coords: p = p.isel(depth=0)
                
                t_mer = round(float(p["thetao"].values.flatten()[0]), 1)
                uo = float(p["uo"].values.flatten()[0])
                vo = float(p["vo"].values.flatten()[0])
                c_speed = round(np.sqrt(uo**2 + vo**2), 2)

                # --- VAGUES ---
                w = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                v_now = round(float(w["VHM0"].values.flatten()[0]), 2)

                # --- CHL ---
                chl = 0
                if ds_bio:
                    try:
                        b = ds_bio.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                        chl = round(float(b["chl"].values.flatten()[0]), 3)
                    except: pass

                # --- LOGIQUE ---
                fish_index = "ÉLEVÉ" if (t_mer < 22) else "MOYEN" if (t_mer < 24) else "FAIBLE"
                safety = "DANGER" if v_now > 2.1 or c_speed > 0.6 else "SÛR"

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "v_now": v_now, "t_now": t_mer, "courant_ms": c_speed,
                    "chlorophylle": chl, "indice_poisson": fish_index,
                    "securite": safety, "date": now.strftime("%Y-%m-%d %H:%M")
                })
                print(f"✅ {name} : OK")

            except Exception as zone_err:
                print(f"❌ Erreur zone {name}: {zone_err}")

    except Exception as e:
        print(f"🔥 Erreur critique: {e}")
        return None
    return results

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id or not data: return
    try:
        bot = Bot(token=token)
        msg = "🚢 *PECHEURCONNECT - INFOS*\n📅 " + datetime.now().strftime('%d/%m/%Y') + "\n\n"
        for d in data:
            icon = "🔴" if d['securite'] == "DANGER" else "🟢"
            msg += f"{icon} *{d['zone']}*\n🌊 `{d['v_now']}m` | 🌡️ `{d['t_now']}°C` | 🧭 `{d['courant_ms']}m/s`\n🐟 Pêche: *{d['indice_poisson']}*\n\n"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
    except: pass

async def main():
    data = await fetch_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
    else: exit(1)

if __name__ == "__main__":
    asyncio.run(main())
