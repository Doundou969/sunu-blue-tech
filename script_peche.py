import os
import json
import math
import datetime
import warnings
import random

warnings.filterwarnings("ignore")

# Si tu as copernicusmarine installé et configuré :
try:
    import copernicusmarine
    COPERNICUS_AVAILABLE = True
except ImportError:
    COPERNICUS_AVAILABLE = False

# ============================================================
# 🔐 SECRETS
# ============================================================
TG_TOKEN = os.getenv("TG_TOKEN", "")
TG_ID = os.getenv("TG_ID", "")
COP_USER = os.getenv("COPERNICUS_USERNAME", "")
COP_PASS = os.getenv("COPERNICUS_PASSWORD", "")

# ============================================================
# 📍 ZONES CÔTIÈRES DU SÉNÉGAL
# ============================================================
ZONES = {
    "SAINT-LOUIS":  [15.8, -16.7, 16.2, -16.3],
    "LOUGA-POTOU":  [15.3, -16.9, 15.6, -16.6],
    "KAYAR":        [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF":   [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL":   [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE":    [12.2, -16.9, 12.7, -16.5]
}

# ============================================================
# 🧭 Direction vent (rose des vents)
# ============================================================
def wind_direction(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[int((deg + 22.5) / 45) % 8]

# ============================================================
# 🚀 Génération de données fallback
# ============================================================
def generate_mock(zone):
    temp = round(random.uniform(18, 24), 1)
    vhm0 = round(random.uniform(0.5, 2.5), 1)
    trend = "➡️"
    if random.random() > 0.7: trend = "📈"
    if random.random() < 0.2: trend = "📉"
    alert = "🟢"
    if vhm0 >= 2.2: alert = "🔴"
    elif vhm0 >= 1.8: alert = "🟠"
    wind_speed = round(random.uniform(0.3, 6.0), 1)
    wind_dir = random.choice(["N","NE","E","SE","S","SW","W","NW"])
    next_vhm = max(0.5, round(vhm0 + random.uniform(-0.5,0.3),1))
    return {
        "zone": zone,
        "temp": temp,
        "vhm0": vhm0,
        "trend": trend,
        "alert": alert,
        "wind_speed": wind_speed,
        "wind_dir": wind_dir,
        "next_vhm": next_vhm
    }

# ============================================================
# 🚀 Tentative Copernicus
# ============================================================
def get_copernicus_data(zone):
    if not COPERNICUS_AVAILABLE:
        raise Exception("copernicusmarine non installé")
    
    copernicusmarine.login(username=COP_USER, password=COP_PASS)
    
    # Ici tu mets ton dataset ID réel pour SST / VHM0
    # Exemple fictif :
    dataset_id_sst = "cmems_mod_glo_phy_my_0.083_P1D-m"  # à adapter
    dataset_id_vhm = "cmems_mod_glo_phy_my_0.083_P1D-m"  # à adapter
    
    # Simulation récupération : à remplacer par code réel
    raise Exception(f"Dataset {dataset_id_sst} non disponible pour test")

# ============================================================
# 🚀 MAIN
# ============================================================
def main():
    results = []
    now = datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    for zone in ZONES:
        try:
            data = get_copernicus_data(zone)
            results.append(data)
        except Exception as e:
            print(f"⚠️ Erreur SST/Vent pour {zone} : {e}")
            results.append(generate_mock(zone))

    # Sauvegarde dans data.json
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ data.json mis à jour ({now})")

if __name__ == "__main__":
    main()
