import os, json, asyncio, requests, numpy as np
import copernicusmarine as cm
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# Zones stratégiques (Sénégal)
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
        # Authentification simple (sans arguments obsolètes)
        cm.login(username=user, password=pw)

        print("📡 Chargement des datasets (Vagues, Physique, Bio)...")
        # Physique (Température et Courants)
        ds_phy = cm.open_dataset(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i", username=user, password=pw)
        # Vagues
        ds_wav = cm.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", username=user, password=pw)
        # Biologie (Chlorophylle)
        ds_bio = cm.open_dataset(dataset_id="cmems_mod_glo_bio-pft_anfc_0.25deg_P1D-m", username=user, password=pw)

        for name, coords in ZONES.items():
            try:
                # --- PHYSIQUE ---
                p = ds_phy.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                t_mer = round(float(p["thetao"].values[0] if p["thetao"].ndim > 0 else p["thetao"].values), 1)
                uo = float(p["uo"].values[0] if p["uo"].ndim > 0 else p["uo"].values)
                vo = float(p["vo"].values[0] if p["vo"].ndim > 0 else p["vo"].values)
                c_speed = round(np.sqrt(uo**2 + vo**2), 2)

                # --- VAGUES ---
                w = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                v_now = round(float(w["VHM0"].values[0] if w["VHM0"].ndim > 0 else w["VHM0"].values), 2)

                # --- BIO ---
                b = ds_bio.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                chl = round(float(b["chl"].values[0] if b["chl"].ndim > 0 else b["chl"].values), 3)

                # --- LOGIQUE MÉTIER ---
                fish_index = "ÉLEVÉ" if (t_mer < 23 and chl > 0.4) else "MOYEN" if (chl > 0.2) else "FAIBLE"
                safety = "DANGER" if v_now > 2.1 or c_speed > 0.6 else "SÛR"

                results.append({
                    "zone": name, "lat": coords["lat"], "lon": coords["lon"],
                    "v_now": v_now, "t_now": t_mer, "courant_ms": c_speed,
                    "chlorophylle": chl, "indice_poisson": fish_index,
                    "securite": safety, "date": now.strftime("%Y-%m-%d %H:%M")
                })
                print(f"✅ Données extraites pour {name}")

            except Exception as zone_err:
                print(f"⚠️ Erreur zone {name}: {zone_err}")

    except Exception as e:
        print(f"🔥 Erreur critique Copernicus: {e}")
        return None

    return results

async def send_telegram(data):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TG_ID")
    if not token or not chat_id or not data: return
    try:
        bot = Bot(token=token)
        msg = "🚢 *PECHEURCONNECT - RAPPORT MARIN*\n"
        msg += f"📅 {datetime.now().strftime('%d/%m/%Y')}\n"
        msg += "----------------------------------\n\n"
        for d in data:
            icon = "🔴" if d['securite'] == "DANGER" else "🟢"
            fish = "🐟" if d['indice_poisson'] == "ÉLEVÉ" else ""
            msg += f"{icon} *{d['zone']}* {fish}\n"
            msg += f"🌊 `{d['v_now']}m` | 🧭 `{d['courant_ms']}m/s`\n"
            msg += f"🌡️ `{d['t_now']}°C` | 🌿 `{d['chlorophylle']}`\n\n"
        await bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
    except Exception as e: print(f"Erreur Telegram: {e}")

async def main():
    data = await fetch_marine_data()
    if data and len(data) > 0:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        await send_telegram(data)
        print("🎉 Mise à jour terminée avec succès !")
    else:
        print("❌ Aucune donnée récupérée. Échec du workflow.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
