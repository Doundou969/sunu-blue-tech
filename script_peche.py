import os
import requests
import copernicusmarine
import datetime
import numpy as np

# --- RÉCUPÉRATION ---
user = os.getenv("COPERNICUS_USERNAME")
pw = os.getenv("COPERNICUS_PASSWORD")
tg_token = os.getenv("TG_TOKEN")
tg_id = os.getenv("TG_ID")

def send_tg(message):
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    requests.post(url, data={"chat_id": tg_id, "text": message, "parse_mode": "Markdown"})

def job():
    # Liste des IDs possibles (Copernicus change parfois les tirets en points)
    # Liste mise à jour pour les serveurs 2026
    dataset_ids = [
        "cmems_mod_glo_phy_anfc_0.083deg_PT1H-m", # Version temps réel haute précision
        "cmems_mod_glo_phy_anfc_0.083deg_static",
        "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
    ]
            if ds is not None:
                print(f"✅ Succès avec {d_id}")
                break
        except:
            continue

    if ds is None:
        send_tg("❌ Erreur : Impossible de trouver le catalogue Copernicus. Vérifiez l'ID.")
        return

    try:
        # Extraction Dakar/Kayar
        data = ds.isel(time=-1).sel(latitude=14.9, longitude=-17.5, method="nearest")
        
        # Données physiques (uo, vo sont les courants)
        u = float(data.uo.values)
        v = float(data.vo.values)
        vitesse = np.sqrt(u**2 + v**2) * 3.6
        
        dir_c = "Est ➡️" if u > 0 else "Ouest ⬅️" if abs(u) > abs(v) else "Nord ⬆️" if v > 0 else "Sud ⬇️"

        now = datetime.datetime.now()
        edition = "🌅 MATIN" if now.hour < 12 else "🌙 SOIR"
        
        rapport = (
            f"🚀 *SUNU-BLUE-TECH : {edition}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 *ZONE : DAKAR / KAYAR*\n"
            f"🌊 Courant : {dir_c}\n"
            f"💨 Vitesse : {vitesse:.1f} km/h\n\n"
            f"⚓ *Bonne pêche !* (Test OK)"
        )

        send_tg(rapport)
        print("✅ Terminé !")

    except Exception as e:
        send_tg(f"❌ Erreur lecture données : {str(e)}")

if __name__ == "__main__":
    job()
