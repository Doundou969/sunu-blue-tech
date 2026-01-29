import os
import copernicusmarine

def main():
    print("🔑 Connexion Copernicus Marine...")

    # 🔐 Auth non-interactive (GitHub Actions safe)
    os.environ["COPERNICUSMARINE_USERNAME"] = os.getenv("COPERNICUS_USERNAME", "")
    os.environ["COPERNICUSMARINE_PASSWORD"] = os.getenv("COPERNICUS_PASSWORD", "")
    os.environ["COPERNICUSMARINE_DISABLE_CREDENTIALS_CACHE"] = "true"

    dataset_id = "cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1D"

    data = copernicusmarine.open_dataset(
        dataset_id=dataset_id,
        minimum_longitude=-20,
        maximum_longitude=-10,
        minimum_latitude=10,
        maximum_latitude=17,
        start_datetime="2026-01-01",
        end_datetime="2026-01-10"
    )

    # 🛑 Sécurité absolue
    if data is None:
        raise RuntimeError("❌ Dataset non chargé (authentification ou dataset ID invalide)")

    print("✅ Dataset chargé")

    # 🔍 Variables disponibles (debug utile)
    print("📦 Variables disponibles :", list(data.data_vars))

    # 🌱 Chlorophylle (nom variable standard CMEMS)
    chl_var = "CHL"

    if chl_var not in data:
        raise KeyError(f"❌ Variable {chl_var} introuvable dans le dataset")

    chl_mean = float(data[chl_var].mean().values)

    print(f"🌱 Chlorophylle moyenne : {chl_mean:.3f} mg/m³")

if __name__ == "__main__":
    main()
