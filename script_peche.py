import os, json, asyncio, requests, numpy as np
import copernicusmarine as cm
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# Zones stratégiques décalées au large (pour éviter les erreurs de pixels côtiers)
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
    
    # Identifiants depuis les secrets GitHub
    user = os.getenv("COPERNICUS_USERNAME")
    pw = os.getenv("COPERNICUS_PASSWORD")

    try:
        print("🚀 Connexion aux services Copernicus...")
        # Authentification forcée
        cm.login(username=user, password=pw, skip_if_logged=True)

        # 1. Ouverture des Datasets (Physique, Vagues, Bio)
        # Physique (Température et Courants)
        ds_phy = cm.open_dataset(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i", username=user, password=pw)
        # Vagues
        ds_wav = cm.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", username=user, password=pw)
        # Biologie (Chlorophylle)
        ds_bio = cm.open_dataset(dataset_id="cmems_mod_glo_bio-pft_anfc_0.25deg_P1D-m", username=user, password=pw)

        for name, coords in ZONES.items():
            try:
                # --- EXTRACTION PHYSIQUE (Température & Courants) ---
                p = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                t_mer = round(float(p["thetao"].values), 1)
                uo, vo = float(p["uo"].values), float(p["vo"].values)
                c_speed = round(np.sqrt(uo**2 + vo**2), 2)

                # --- EXTRACTION VAGUES ---
                w = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                v_now = round(float(w["VHM0"].values), 2)

                # --- EXTRACTION BIO (Chlorophylle) ---
                b = ds_bio.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                chl = round(float(b["chl"].values), 3)

                # --- LOGIQUE MÉTIER PECHEURCONNECT ---
                # Un bon indice de poisson = Eau fraîche (<22°C) + Chl élevée (>0.4)
                if t_mer < 22 and chl > 0.4: fish_index = "ÉLEVÉ"
                elif chl > 0.2: fish_index = "MOYEN"
                else: fish_index = "FAIBLE"

                # Sécurité (Vagues > 2.1m ou Courant > 0.6 m/s)
                safety = "DANGER" if v_now > 2.1 or c_speed > 0.6 else "SÛR"

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "v_now": v_now, "t_now": t_mer, "courant_ms": c_speed,
                    "chlorophylle": chl, "indice_poisson": fish_index,
                    "securite": safety, "date": now.strftime("%Y-%m-%d %H:%M")
                })
                print(f"✅ {name} traité.")

            except Exception as e:
                print(f"❌ Erreur sur la zone {name}: {e}")

    except Exception as e:
        print(f"🔥 Erreur critique Copernicus: {e}")
        return None

    return results

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id or not data: return
    try:
        bot = Bot(token=token)
        msg = "🚢 *PECHEURCONNECT - RAPPORT DU MATIN*\n"
        msg += f"📅 {datetime.now().strftime('%d/%m/%Y')}\n"
        msg += "----------------------------------\n\n"
        for d in data:
            alert = "🔴" if d['securite'] == "DANGER" else "🟢"
            fish = "🐟" if d['indice_poisson'] == "ÉLEVÉ" else ""
            msg += f"{alert} *{d['zone']}* {fish}\n"
            msg += f"🌊 `{d['v_now']}m` | 🧭 `{d['courant_ms']}m/s`\n"
            msg += f"🌡️ `{d['t_now']}°C` | 🌿 `{d['chlorophylle']}`\n\n"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
    except Exception as e: print(f"Erreur Telegram: {e}")

async def main():
    data = await fetch_marine_data()
    if data:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
    else:
        # Forcer une erreur pour l'alerte GitHub Action
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
