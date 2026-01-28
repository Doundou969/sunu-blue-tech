# script_peche.py
import os, json, math, datetime
import copernicusmarine
import numpy as np

# =====================
# CONFIG
# =====================
ZONES = {
    "SAINT-LOUIS":  [15.8, -16.7, 16.2, -16.3],
    "LOUGA-POTOU":  [15.3, -16.9, 15.6, -16.6],
    "KAYAR":        [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF":   [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL":   [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE":    [12.2, -16.9, 12.7, -16.5]
}

copernicusmarine.login(
    username=os.environ["COPERNICUS_USERNAME"],
    password=os.environ["COPERNICUS_PASSWORD"]
)

results = []
now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

for zone, b in ZONES.items():
    try:
        # 🌡️ SST
        ds_sst = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
            minimum_latitude=b[0], maximum_latitude=b[2],
            minimum_longitude=b[1], maximum_longitude=b[3],
            variables=["thetao"]
        )
        sst_raw = float(ds_sst["thetao"].isel(time=-1, depth=0).mean())
        sst = round(sst_raw - 273.15, 1)

        # 🌊 Houle
        ds_wave = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
            minimum_latitude=b[0], maximum_latitude=b[2],
            minimum_longitude=b[1], maximum_longitude=b[3],
            variables=["VHM0"]
        )
        houle = round(float(ds_wave["VHM0"].isel(time=-1).mean()), 1)

        # 🌀 Courant
        ds_cur = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
            minimum_latitude=b[0], maximum_latitude=b[2],
            minimum_longitude=b[1], maximum_longitude=b[3],
            variables=["uo", "vo"]
        )
        u = float(ds_cur["uo"].isel(time=-1, depth=0).mean())
        v = float(ds_cur["vo"].isel(time=-1, depth=0).mean())
        courant = round(math.sqrt(u*u + v*v), 2)

        results.append({
            "zone": zone,
            "sst": sst,
            "houle": houle,
            "courant": courant,
            "timestamp": now
        })

    except Exception as e:
        results.append({
            "zone": zone,
            "sst": None,
            "houle": None,
            "courant": None,
            "error": str(e)
        })

with open("data.json", "w") as f:
    json.dump(results, f, indent=2)

print("✅ data.json généré avec succès")
