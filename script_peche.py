#!/usr/bin/env python3
import os
import json
import datetime
import warnings
import math
import requests
from copernicusmarine import login, open_dataset

warnings.filterwarnings("ignore")

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

# 🔐 SECRETS GITHUB
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

ZONES = {
    "SAINT-LOUIS": {"bounds": [15.8, -16.7, 16.2, -16.3]},
    "DAKAR-YOFF":  {"bounds": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"bounds": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"bounds": [12.2, -16.9, 12.7, -16.5]}
}

def get_wind_dir(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N", "N-E", "E", "S-E", "S", "S-O", "O", "N-O"]
    return dirs[int((deg + 22.5) / 45) % 8]

def get_data(name, b):
    print(f"📡 Analyse : {name}...")
    res = {'sst': 21.0, 'vhm0': 1.1, 'wind_speed': 12, 'wind_dir': 'N'}
    try:
        # Température (SST)
        ds = open_dataset(dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
                          minimum_latitude=b[0], maximum_latitude=b[2],
                          minimum_longitude=b[1], maximum_longitude=b[3], variables=["thetao"])
        res['sst'] = round(float(ds["thetao"].isel(time=-1, depth=0).mean()), 1)
        
        # Vagues (Houle)
        ds_w = open_dataset(dataset_id="global-analysis-forecast-wav-001-027",
                            minimum_latitude=b[0], maximum_latitude=b[2],
                            minimum_longitude=b[1], maximum_longitude=b[3], variables=["VHM0"])
        res['vhm0'] = round(float(ds_w["VHM0"].isel(time=-1).mean()), 1)

        # Vent (Vitesse & Direction)
        ds_v = open_dataset(dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
                            minimum_latitude=b[0], maximum_latitude=b[2],
                            minimum_longitude=b[1], maximum_longitude=b[3], variables=["uo", "vo"])
        u = float(ds_v["uo"].isel(time=-1, depth=0).mean())
        v = float(ds_v["vo"].isel(time=-1, depth=0).mean())
        res['wind_speed'] = round(math.sqrt(u**2 + v**2) * 3.6, 1)
        res['wind_dir'] = get_wind_dir(u, v)
    except: pass
    return res

def main():
    if COP_USER and COP_PASS:
        try: login(username=COP_USER, password=COP_PASS)
        except: pass

    old_data = {}
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r') as f:
                history = json.load(f)
                old_data = {item['zone']: item['temp'] for item in history}
        except: pass

    web_json = []
    now = datetime.datetime.now(UTC)
    report = f"<b>🌊 PECHEUR CONNECT 🇸🇳</b>\n📅 <i>{now.strftime('%d/%m/%Y %H:%M')} GMT</i>\n───────────────────\n\n"
    
    for name, config in ZONES.items():
        data = get_data(name, config['bounds'])
        
        # Comparaison Température
        prev_t = old_data.get(name, data['sst'])
        diff = round(data['sst'] - prev_t, 1)
        trend = "📉" if diff <= -0.4 else "📈" if diff >= 0.4 else "➡️"
        
        # Sécurité & Conseils
        alert = "🟢" if data['vhm0'] < 1.4 else "🟡" if data['vhm0'] < 2.1 else "🔴"
        advice = "✅ Mer calme" if alert == "🟢" else "⚠️ Vigilance" if alert == "🟡" else "🚫 Danger"
        fuel = "\n⛽ <i>Prévoyez surplus carburant (Vent fort)</i>" if data['wind_speed'] > 22 else ""
        target = "🐟 THIOF ⭐⭐⭐" if data['sst'] < 21 else "🐟 THON / ESPADON ⭐⭐"

        report += f"📍 <b>{name}</b> {alert}\n"
        report += f"🌡️ Mer: <b>{data['sst']}°C</b> {trend}\n"
        report += f"🌊 Houle: <b>{data['vhm0']}m</b> | 🌬️ <b>{data['wind_speed']}km/h</b> ({data['wind_dir']})\n"
        report += f"🎣 {target}\n<i>{advice}</i>{fuel}\n\n"
        
        web_json.append({**{"zone": name, "temp": data['sst'], "trend": trend, "alert": alert, "advice": advice, "fuel": fuel != ""}, **data})

    report += f"───────────────────\n📱 <b>Carte GPS :</b> https://doundou969.github.io/sunu-blue-tech/"
    
    with open('data.json', 'w') as f: json.dump(web_json, f, indent=4)
    if TG_TOKEN and TG_ID:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_ID, "text": report, "parse_mode": "HTML", "disable_web_page_preview": "true"})

if __name__ == "__main__":
    main()
