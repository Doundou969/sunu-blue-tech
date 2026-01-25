import os, json, datetime, math, requests, warnings
import copernicusmarine

warnings.filterwarnings("ignore")

TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

ZONES = {
    "SAINT-LOUIS": [15.8, -16.7, 16.2, -16.3],
    "LOUGA-POTOU": [15.3, -16.9, 15.6, -16.6],
    "KAYAR":       [14.8, -17.3, 15.1, -17.1],
    "DAKAR-YOFF":  [14.6, -17.6, 14.8, -17.4],
    "MBOUR-JOAL":  [14.0, -17.1, 14.4, -16.7],
    "CASAMANCE":   [12.2, -16.9, 12.7, -16.5]
}

def get_wind_dir(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N", "N-E", "E", "S-E", "S", "S-O", "O", "N-O"]
    return dirs[int((deg + 22.5) / 45) % 8]

def main():
    try:
        print("🔑 Connexion Copernicus...")
        copernicusmarine.login(username=COP_USER, password=COP_PASS)
        
        old_temp = {}
        if os.path.exists('data.json'):
            try:
                with open('data.json', 'r') as f:
                    history = json.load(f)
                    # On ne récupère l'historique que si la valeur était réaliste (>0)
                    old_temp = {item['zone']: item['temp'] for item in history if item['temp'] > 0}
            except: pass

        results = []
        now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        report = f"🌊 <b>PECHEUR CONNECT 🇸🇳</b>\n📅 {now} GMT\n───────────────────\n\n"

        for name, b in ZONES.items():
            print(f"📡 Analyse : {name}")
            try:
                # 🌡️ SST - Détection Intelligente Kelvin/Celsius
                ds_t = copernicusmarine.open_dataset(dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m", minimum_latitude=b[0], maximum_latitude=b[2], minimum_longitude=b[1], maximum_longitude=b[3], variables=["thetao"])
                raw_temp = float(ds_t["thetao"].isel(time=-1, depth=0).mean())
                
                # Si la valeur est > 100, c'est du Kelvin, sinon c'est déjà du Celsius
                sst = round(raw_temp - 273.15, 1) if raw_temp > 100 else round(raw_temp, 1)
                
                # 🌊 HOULE
                ds_w = copernicusmarine.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", minimum_latitude=b[0], maximum_latitude=b[2], minimum_longitude=b[1], maximum_longitude=b[3], variables=["VHM0"])
                vhm0 = round(float(ds_w["VHM0"].isel(time=-8).mean()), 1)
                next_v = round(float(ds_w["VHM0"].isel(time=-1).mean()), 1)

                # 🌬️ VENT
                ds_v = copernicusmarine.open_dataset(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m", minimum_latitude=b[0], maximum_latitude=b[2], minimum_longitude=b[1], maximum_longitude=b[3], variables=["uo", "vo"])
                u, v = float(ds_v["uo"].isel(time=-1, depth=0).mean()), float(ds_v["vo"].isel(time=-1, depth=0).mean())
                w_speed = round(math.sqrt(u**2 + v**2) * 3.6, 1)
                w_dir = get_wind_dir(u, v)
            except:
                sst, vhm0, next_v, w_speed, w_dir = 20.0, 1.2, 1.2, 12.0, "N"

            trend = "📉" if sst < old_temp.get(name, sst) - 0.2 else "📈" if sst > old_temp.get(name, sst) + 0.2 else "➡️"
            alert_emoji = "🟢" if vhm0 < 1.4 else "🟡" if vhm0 < 2.2 else "🔴"

            report += f"📍 <b>{name}</b> {alert_emoji}\n🌡️ {sst}°C {trend} | 🌊 {vhm0}m\n🌬️ {w_speed}km/h ({w_dir})\n\n"
            results.append({"zone": name, "temp": sst, "trend": trend, "vhm0": vhm0, "next_vhm": next_v, "wind_speed": w_speed, "wind_dir": w_dir, "alert": alert_emoji})

        # Sauvegarde et Envoi
        with open('data.json', 'w') as f: json.dump(results, f, indent=4)
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_ID, "text": report, "parse_mode": "HTML"})
        print("✅ Données corrigées et envoyées.")
    except Exception as e: print(f"💥 Erreur: {e}")

if __name__ == "__main__": main()
