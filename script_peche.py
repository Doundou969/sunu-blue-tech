import os
import json
from datetime import datetime
import copernicusmarine
from rich import print

LAT = 14.7167    # Dakar
LON = -17.4677

def load_copernicus_chl():
    username = os.getenv("COPERNICUS_USERNAME")
    password = os.getenv("COPERNICUS_PASSWORD")

    if not username or not password:
        raise RuntimeError("❌ Identifiants Copernicus manquants")

    print("🔑 Connexion Copernicus Marine (non-interactive)...")

    try:
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_bgc_my_0.25deg_P1D-m",
            variables=["CHL"],
            username=username,
            password=password
        )

        # Sélection géographique APRÈS ouverture
        ds_point = ds.sel(
            latitude=LAT,
            longitude=LON,
            method="nearest"
        )

        return ds_point

    except Exception as e:
        print(f"❌ Erreur Copernicus Marine: {e}")
        return None


def compute_fishing_score(chl):
    if chl < 0.1:
        return 20
    elif chl < 0.3:
        return 50
    elif chl < 1.0:
        return 80
    else:
        return 95


def main():
    chl_ds = load_copernicus_chl()

    if chl_ds is None or "CHL" not in chl_ds:
        raise RuntimeError("❌ Dataset CHL indisponible")

    chl = float(chl_ds["CHL"].mean().values)
    score = compute_fishing_score(chl)

    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "location": "Dakar",
        "latitude": LAT,
        "longitude": LON,
        "chlorophyll": round(chl, 3),
        "fishing_score": score,
        "advice": "Zone favorable à la pêche 🎣" if score >= 60 else "Zone peu productive ⚠️"
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ data.json généré avec succès")
    print(data)


if __name__ == "__main__":
    main()
