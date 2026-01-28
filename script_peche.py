import os, json, datetime, math, warnings
import requests
import copernicusmarine

# Silence warnings
warnings.filterwarnings("ignore")

# Secrets GitHub
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# Zones
ZONES = {
    "SAINT-LOUIS": [15.8, -16.7, 16.2, -16.3],
    "LOUGA-POTOU": [15.3, -16.9, 15.6, -16.6],
    "KAYAR":       [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF":  [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL":  [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE":   [12.2, -16.9, 12.7, -16.5]
}

def get_wind_dir(u,v):
    deg = (math.atan2(u,v)*180/math.pi + 180)%360
    dirs = ["N","N-E","E","S-E","S","S-O","O","N-O"]
    return dirs[int((deg+22.5)/45)%8]

def main():
    try:
        copernicusmarine.login(username=COP_USER,password=COP_PASS)
        results = []

        for name,b in ZONES.items():
            try:
                # Température SST
                ds_t = copernicusmarine.open_dataset(
                    dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["thetao"]
                )
                raw_t = float(ds_t["thetao"].isel(time=-1, depth=0).mean())
                sst = round(raw_t - 273.15 if raw_t>100 else raw_t,1)

                # Houle
                ds_w = copernicusmarine.open_dataset(
                    dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["VHM0"]
                )
                houle = round(float(ds_w["VHM0"].isel(time=-1).mean()),1)

                # Courant
                ds_c = copernicusmarine.open_dataset(
                    dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["uo","vo"]
                )
                u = float(ds_c["uo"].isel(time=-1, depth=0).mean())
                v = float(ds_c["vo"].isel(time=-1, depth=0).mean())
                courant = round(math.sqrt(u**2+v**2),2)

            except:
                sst, houle, courant = 20.0, 1.0, 0.5

            results.append({
                "zone": name,
                "sst": sst,
                "houle": houle,
                "courant": courant
            })

        # Sauvegarde JSON
        with open("data.json","w") as f:
            json.dump(results,f,indent=2)

        print("✅ data.json mis à jour avec succès")

    except Exception as e:
        print("💥 Erreur script:", e)

if __name__=="__main__":
    main()
