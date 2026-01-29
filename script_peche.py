import copernicusmarine
import xarray as xr

def main():
    print("🔑 Connexion Copernicus Marine...")

    dataset_id = "cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1D"

    try:
        data = copernicusmarine.open_dataset(
            dataset_id=dataset_id,
            minimum_longitude=-20,   # Sénégal
            maximum_longitude=-10,
            minimum_latitude=10,
            maximum_latitude=17,
            start_datetime="2026-01-01",
            end_datetime="2026-01-10"
        )

        print("✅ Dataset chargé avec succès")
        print(data)

        # Exemple : moyenne chlorophylle
        chl = data["CHL"].mean().item()
        print(f"🌱 Chlorophylle moyenne : {chl:.3f} mg/m³")

    except Exception as e:
        print("❌ Erreur Copernicus Marine")
        print(e)

if __name__ == "__main__":
    main()
