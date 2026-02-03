import os, json, asyncio, requests, numpy as np
import copernicusmarine as cm
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# Zones stratégiques du Sénégal
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65},
    "KAYAR": {"lat": 14.95, "lon": -17.35},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95}
}

async def fetch_marine_data():
    # Chargement des 3 piliers Copernicus
    # 1. Vagues  2. Physique (Temp/Courants) 3. Bio (Chlorophylle)
    ds_wav = cm.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i")
    ds_phy = cm.open_dataset(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i")
    ds_bio = cm.open_dataset(dataset_id="cmems_mod_glo_bio-pft_anfc_0.25deg_P1D-m")
    
    results = []
    now = datetime.utcnow()

    for name, coords in ZONES.items():
        try:
            # --- VAGUES ---
            w = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
            v_now = round(float(w["VHM0"].values), 2)
            
            # --- COURANTS & TEMPÉRATURE ---
            p = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
            t_mer = round(float(p["thetao"].values), 1)
            # Calcul de la vitesse du courant (m/s) à partir des vecteurs U et V
            uo, vo = float(p["uo"].values), float(p["vo"].values)
            c_speed = round(np.sqrt(uo**2 + vo**2), 2)

            # --- BIOLOGIE (CHLOROPHYLLE) ---
            b = ds_bio.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
            chl = round(float(b["chl"].values), 3)

            # --- INDICE DE PÊCHE (Logique métier PecheurConnect) ---
            # Un bon indice = Eau fraîche (upwelling) + forte chlorophylle
            fish_index = "ÉLEVÉ" if (t_mer < 22 and chl > 0.5) else "MOYEN" if (chl > 0.2) else "FAIBLE"
            
            # --- SÉCURITÉ ---
            safety = "DANGER" if v_now > 2.2 or c_speed > 0.6 else "SÛR"

            results.append({
                "zone": name,
                "vagues": v_now,
                "temp_mer": t_mer,
                "courant_ms": c_speed,
                "chlorophylle": chl,
                "indice_poisson": fish_index,
                "securite": safety,
                "timestamp": now.strftime("%H:%M")
            })
        except Exception as e:
            print(f"Erreur sur {name}: {e}")

    return results

async def send_telegram_rich(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id: return
    bot = Bot(token=token)
    
    header = "🌊 *PECHEURCONNECT - INTELLIGENCE MARINE*\n"
    header += f"📅 {datetime.now().strftime('%d/%m/%Y')}\n"
    header += "----------------------------------\n\n"
    
    msg = header
    for d in data:
        icon = "🔴" if d['securite'] == "DANGER" else "🟢"
        msg += f"{icon} *{d['zone']}*\n"
        msg += f"🌊 Vagues: `{d['vagues']}m` | 🧭 Courant: `{d['courant_ms']}m/s`\n"
        msg += f"🌡️ Eau: `{d['temp_mer']}°C` | 🌿 Chl: `{d['chlorophylle']}mg/m³`\n"
        msg += f"🐟 Potentiel Pêche: *{d['indice_poisson']}*\n\n"
        
    await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')

async def main():
    data = await fetch_marine_data()
    # Sauvegarde pour le dashboard web
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Envoi Telegram
    await send_telegram_rich(data)

if __name__ == "__main__":
    asyncio.run(main())
