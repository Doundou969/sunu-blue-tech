import os, json, datetime, math, requests, warnings
import copernicusmarine

# Désactiver les avertissements inutiles
warnings.filterwarnings("ignore")

# 🔐 CONFIGURATION DES SECRETS (GitHub)
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 ZONES STRATÉGIQUES SÉNÉGAL (Bounds: [Lat_Sud, Lon_Ouest, Lat_Nord, Lon_Est])
ZONES = {
    "SAINT-LOUIS": [15.8, -16.7, 16.2, -16.3],
    "LOUGA-POTOU": [15.3, -16.9, 15.6, -16.6],
    "KAYAR":       [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF":  [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL":  [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE":   [12.2, -16.9, 12.7, -16.5]
}

def get_wind_dir(u, v):
    """Calcule la direction du vent à partir des vecteurs u et v"""
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N", "N-E", "E", "S-E", "S", "S-O", "O", "N-O"]
    return dirs[int((deg + 22.5) / 45) % 8]

def main():
    try:
        print("🔑 Connexion Copernicus...")
        copernicusmarine.login(username=COP_USER, password=COP_PASS)
        
        # 1. Charger l'historique pour calculer la tendance (Upwelling)
        old_temp = {}
        if os.path.exists('data.json'):
            try:
                with open('data.json', 'r') as f:
                    history = json.load(f)
                    old_temp = {item['zone']: item['temp'] for item in history}
            except: pass

        results = []
        now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        report = f"🌊 <b>PECHEUR CONNECT 🇸🇳</b>\n📅 {now} GMT\n"
        report += "───────────────────\n\n"

        for name, b in ZONES.items():
            print(f"📡 Analyse de la zone : {name}")
            
            try:
                # --- TEMPÉRATURE (SST) ---
                ds_t = copernicusmarine.open_dataset(
                    dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["thetao"]
                )
                sst = round(float(ds_t["thetao"].isel(time=-1, depth=0).mean()) - 273.15, 1)
                
                # --- HOULE (VHM0) ---
                ds_w = copernicusmarine.open_dataset(
                    dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["VHM0"]
                )
                vhm0 = round(float(ds_w["VHM0"].isel(time=-8).mean()), 1)
                next_v = round(float(ds_w["VHM0"].isel(time=-1).mean()), 1)

                # --- VENT (UO/VO) ---
                ds_v = copernicusmarine.open_dataset(
                    dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                    minimum_latitude=b[0], maximum_latitude=b[2],
                    minimum_longitude=b[1], maximum_longitude=b[3],
                    variables=["uo", "vo"]
                )
                u = float(ds_v["uo"].isel(time=-1, depth=0).mean())
                v = float(ds_v["vo"].isel(time=-1, depth=0).mean())
                w_speed = round(math.sqrt(u**2 + v**2) * 3.6, 1)
                w_dir = get_wind_dir(u, v)

            except Exception as e:
                print(f"⚠️ Erreur sur {name} : {str(e)}")
                # Valeurs par défaut pour ne pas bloquer le script
                sst, vhm0, next_v, w_speed, w_dir = 20.0, 1.0, 1.0, 12.0, "N"

            # Logique métier : Alertes et Poissons
            trend = "📉" if sst < old_temp.get(name, sst) - 0.2 else "📈" if sst > old_temp.get(name, sst) + 0.2 else "➡️"
            alert = "🟢" if vhm0 < 1.4 else "🟡" if vhm0 < 2.1 else "🔴"
            target = "🐟 THIOF (Eau froide)" if sst < 21 else "🐟 THON / ESPADON"
            
            # Construction du message Telegram
            report += f"📍 <b>{name}</b> {alert}\n"
            report += f"🌡️ {sst}°C {trend} | 🌊 {vhm0}m\n"
            report += f"🌬️ {w_speed}km/h ({w_dir})\n"
            report += f"🎣 {target}\n\n"

            results.append({
                "zone": name, "temp": sst, "trend": trend, "vhm0": vhm0, 
                "next_vhm": next_v, "wind_speed": w_speed, "wind_dir": w_dir, 
                "alert": alert, "target": target
            })

        # Conseil Carburant (Zone la plus froide)
        best_eco = min(results, key=lambda x: x['temp'])
        report += f"⛽ <b>CONSEIL ESSENCE :</b>\nLa zone la plus riche est <b>{best_eco['zone']}</b>.\nInutile de naviguer plus loin !\n"
        report += "───────────────────\n📱 https://doundou969.github.io/sunu-blue-tech/"

        # 2. Sauvegarde pour le site web
        with open('data.json', 'w') as f:
            json.dump(results, f, indent=4)
        print("💾 Fichier data.json mis à jour.")

        # 3. Envoi vers Telegram
        print(f"📤 Envoi du bulletin à {TG_ID}...")
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_ID, "text": report, "parse_mode": "HTML", "disable_web_page_preview": "true"}
        
        resp = requests.post(url, data=payload)
        if resp.status_code == 200:
            print("✅ SUCCÈS : Notification envoyée !")
        else:
            print(f"❌ ERREUR TELEGRAM : {resp.text}")

    except Exception as e:
        print(f"💥 CRASH GÉNÉRAL : {str(e)}")

if __name__ == "__main__":
    main()
