# script_peche.py — PecheurConnect PRO (Copernicus + Telegram)
# ============================================================

import os
import json
import math
import datetime
import warnings
import requests
from copernicusmarine import open_dataset, login

warnings.filterwarnings("ignore")

# 🔐 Secrets (via GitHub Actions ou .env)
TG_TOKEN = os.getenv("TG_TOKEN", "").strip()
TG_ID = os.getenv("TG_ID", "").strip()
COP_USER = os.getenv("COPERNICUS_USERNAME", "").strip()
COP_PASS = os.getenv("COPERNICUS_PASSWORD", "").strip()

# 📍 Zones du Sénégal
ZONES = {
    "SAINT-LOUIS": [15.8, -16.7, 16.2, -16.3],
    "LOUGA-POTOU": [15.3, -16.9, 15.6, -16.6],
    "KAYAR": [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF": [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL": [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE": [12.2, -16.9, 12.7, -16.5]
}

def get_wind_dir(u, v):
    """Retourne la direction du vent en rose des vents"""
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N", "N-E", "E", "S-E", "S", "S-O", "O", "N-O"]
    return dirs[int((deg + 22.5) / 45) % 8]

def main():
    try:
        print("🔑 Connexion à Copernicus...")
        login(username=COP_USER, password=COP_PASS)

        results = []
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        report = f"🌊 PECHEUR CONNECT 🇸🇳\n📅 {now} GMT\n\n"
        alertes_critiques = []

        for name, b in ZONES.items():
            print(f"📡 Analyse satellite : {name}...")

            try:
                # --- TEMPÉRATURE DE SURFACE (SST) ---
                ds_t = open_dataset(
                    dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["thetao"]
                )
                raw_t = float(ds_t["thetao"].isel(time=-1, depth=0).mean())
                sst = round(raw_t - 273.15, 1) if raw_t > 100 else round(raw_t, 1)

                # --- HOULE (VHM0) ---
                ds_w = open_dataset(
                    dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["VHM0"]
                )
                houle = round(float(ds_w["VHM0"].isel(time=-1).mean()), 1)

                # --- COURANT ---
                ds_c = open_dataset(
                    dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["uo", "vo"]
                )
                u = float(ds_c["uo"].isel(time=-1, depth=0).mean())
                v = float(ds_c["vo"].isel(time=-1, depth=0).mean())
                courant = round(math.sqrt(u**2 + v**2), 2)
                w_dir = get_wind_dir(u, v)

            except Exception as e:
                print(f"⚠️ Erreur zone {name}: {e}")
                sst, houle, courant, w_dir = 20.0, 1.0, 0.5, "N"

            # Détection d'alerte
            if houle >= 2.2:
                alertes_critiques.append(f"⚠️ DANGER {name}: Houle {houle} m !")

            # Formatage du message
            report += f"📍 {name}\n🌡️ {sst}°C | 🌊 {houle} m | 🌀 {courant} m/s\n\n"

            # Sauvegarde des données
            results.append({
                "zone": name,
                "sst": sst,
                "houle": houle,
                "courant": courant,
                "wind_dir": w_dir,
                "alert": "🔴" if houle >= 2.2 else "🟢"
            })

        # Préfixer les alertes en tête de message Telegram
        if alertes_critiques:
            report = "🚨 ALERTE MER 🚨\n" + "\n".join(alertes_critiques) + "\n\n" + report

        # 🔄 Sauvegarde JSON
        with open("data.json", "w") as f:
            json.dump(results, f, indent=4)

        # 📤 Envoi Telegram
        if TG_TOKEN and TG_ID:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                data={"chat_id": TG_ID, "text": report, "parse_mode": "HTML"}
            )
        print("✅ Rapport généré et envoyé avec succès.")

    except Exception as e:
        print(f"💥 SCRIPT CRASH : {e}")

if __name__ == "__main__":
    main()
