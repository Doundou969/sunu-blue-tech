# ============================================================
# 🌊 PECHEURCONNECT 🇸🇳
# Alerte maritime & info satellite pour pêche artisanale
# Données : Copernicus Marine (UE)
# Diffusion : Telegram / WhatsApp-ready
# ============================================================

import os
import json
import math
import datetime
import requests
import warnings
import copernicusmarine

warnings.filterwarnings("ignore")

# ============================================================
# 🔐 VARIABLES D’ENVIRONNEMENT
# ============================================================
TG_TOKEN = os.getenv("TG_TOKEN", "").strip()
TG_ID = os.getenv("TG_ID", "").strip()
COP_USER = os.getenv("COPERNICUS_USERNAME", "").strip()
COP_PASS = os.getenv("COPERNICUS_PASSWORD", "").strip()

if not TG_TOKEN or not TG_ID:
    print("❌ Telegram non configuré")
    exit(1)

# ============================================================
# 📍 ZONES CÔTIÈRES DU SÉNÉGAL
# ============================================================
ZONES = {
    "SAINT-LOUIS": [15.8, -16.7, 16.2, -16.3],
    "KAYAR": [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF": [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL": [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE": [12.2, -16.9, 12.7, -16.5],
}

DATA_FILE = "data.json"

# ============================================================
# 🧭 FONCTIONS UTILES
# ============================================================
def direction_from_uv(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N", "N-E", "E", "S-E", "S", "S-O", "O", "N-O"]
    return dirs[int((deg + 22.5) / 45) % 8]

def decision_mer(houle, courant):
    if houle >= 2.3:
        return "🔴", "⛔ Sortie déconseillée"
    if houle >= 1.4 or courant >= 1.5:
        return "🟡", "⚠️ Prudence en mer"
    return "🟢", "✅ Sortie conseillée"

# ============================================================
# 🚀 MAIN
# ============================================================
def main():
    print("🔑 Connexion Copernicus Marine…")
    copernicusmarine.login(username=COP_USER, password=COP_PASS)

    # Historique SST (tendance)
    old_temp = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                old_temp = {i["zone"]: i["sst"] for i in json.load(f)}
        except:
            pass

    now = datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    report = f"🌊 <b>PECHEUR CONNECT 🇸🇳</b>\n📅 {now} GMT\n──────────────────\n\n"
    alertes = []
    results = []

    for zone, b in ZONES.items():
        print(f"📡 Analyse {zone}…")
        try:
            # 🌡️ TEMPÉRATURE DE SURFACE
            ds_t = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
                minimum_latitude=b[0], maximum_latitude=b[2],
                minimum_longitude=b[1], maximum_longitude=b[3],
                variables=["thetao"]
            )
            raw = float(ds_t["thetao"].isel(time=-1, depth=0).mean())
            sst = round(raw - 273.15, 1) if raw > 100 else round(raw, 1)

            # 🌊 HOULE
            ds_w = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                minimum_latitude=b[0], maximum_latitude=b[2],
                minimum_longitude=b[1], maximum_longitude=b[3],
                variables=["VHM0"]
            )
            houle = round(float(ds_w["VHM0"].isel(time=-1).mean()), 1)

            # 🌊 COURANTS MARINS
            ds_c = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                minimum_latitude=b[0], maximum_latitude=b[2],
                minimum_longitude=b[1], maximum_longitude=b[3],
                variables=["uo", "vo"]
            )
            u = float(ds_c["uo"].isel(time=-1, depth=0).mean())
            v = float(ds_c["vo"].isel(time=-1, depth=0).mean())
            courant = round(math.sqrt(u**2 + v**2) * 3.6, 1)
            c_dir = direction_from_uv(u, v)

        except Exception as e:
            print(f"⚠️ Données manquantes {zone} : {e}")
            sst, houle, courant, c_dir = 20.0, 1.0, 1.0, "N"

        # 📉📈 TENDANCE
        prev = old_temp.get(zone, sst)
        trend = "📉" if sst < prev - 0.2 else "📈" if sst > prev + 0.2 else "➡️"

        # 🟢🟡🔴 DÉCISION
        emoji, decision = decision_mer(houle, courant)

        if emoji == "🔴":
            alertes.append(f"🚨 {zone} – Houle {houle} m")

        report += (
            f"📍 <b>{zone}</b> {emoji}\n"
            f"🌡️ Eau : {sst}°C {trend}\n"
            f"🌊 Houle : {houle} m\n"
            f"🌊 Courant : {courant} km/h ({c_dir})\n"
            f"{decision}\n\n"
        )

        results.append({
            "zone": zone,
            "sst": sst,
            "houle": houle,
            "courant": courant
        })

    # ⛽ CONSEIL ÉCO
    best = min(results, key=lambda x: x["sst"])
    report += f"⛽ <b>CONSEIL ÉCO :</b> Zone favorable : {best['zone']}\n"
    report += "ℹ️ Données satellites – Sécurité avant tout\n"

    if alertes:
        report = "🚨 <b>ALERTE MER</b>\n" + "\n".join(alertes) + "\n\n" + report

    # 💾 Sauvegarde
    with open(DATA_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # 📤 Envoi Telegram
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_ID, "text": report, "parse_mode": "HTML"}
    )

    print("✅ Rapport envoyé avec succès")

# ============================================================
if __name__ == "__main__":
    main()
