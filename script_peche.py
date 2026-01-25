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

# 🔐 CONFIGURATION SECRETS
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

# 📍 6 ZONES STRATÉGIQUES SÉNÉGAL
ZONES = {
    "SAINT-LOUIS": {"bounds": [15.8, -16.7, 16.2, -16.3]},
    "LOUGA-POTOU": {"bounds": [15.3, -16.9, 15.6, -16.6]},
    "KAYAR":       {"bounds": [14.8, -17.3, 15.1, -17.1]},
    "DAKAR-YOFF":  {"bounds": [14.6, -17.6, 14.8, -17.4]},
    "MBOUR-JOAL":  {"bounds": [14.0, -17.1, 14.4, -16.7]},
    "CASAMANCE":   {"bounds": [12.2, -16.9, 12.7, -16.5]}
}

def get_wind_dir(u, v):
    deg = (math.atan2(u, v) * 180 / math.pi + 180) % 360
    dirs = ["N", "N-E", "E", "S-E", "S", "S-O", "O", "N-O"]
    return dirs[int((deg + 22.5) / 45) % 8]

def get_data(name, b):
    print(f"📡 Analyse & Prévision : {name}...")
    res = {'sst': 20.5, 'vhm0': 1.1, 'wind_speed': 15, 'wind_dir': 'N', 'next_vhm': 1.1}
    try:
        # 1. TEMPÉRATURE (SST)
        ds = open_dataset(dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m",
                          minimum_latitude=b[0], maximum_latitude=b[2],
                          minimum_longitude=b[1], maximum_longitude=b[3], variables=["thetao"])
        res['sst'] = round(float(ds["thetao"].isel(time=-1, depth=0).mean()), 1)
        
        # 2. HOULE (Aujourd'hui vs Demain)
        ds_w = open_dataset(dataset_id="global-analysis-forecast-wav-001-027",
                            minimum_latitude=b[0], maximum_latitude=b[2],
                            minimum_longitude=b[1], maximum_longitude=b[3], variables=["VHM0"])
        res['vhm0'] = round(float(ds_w["VHM0"].isel(time=-2).mean()), 1)
        res['next_vhm'] = round(float(ds_w["VHM0"].isel(time=-1).mean()), 1)

        # 3. VENT
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
        
        # Tendance & Sécurité
        prev_t = old_data.get(name, data['sst'])
        diff = round(data['sst'] - prev_t, 1)
        trend = "📉" if diff <= -0.4 else "📈" if diff >= 0.4 else "➡️"
        alert = "🟢" if data['vhm0'] < 1.4 else "🟡" if data['vhm0'] < 2.1 else "🔴"
        
        # Prévision
        forecast = "✅ Stable"
        if data['next_vhm'] > data['vhm0'] + 0.4: forecast = f"⚠️ Hausse ({data['next_vhm']}m)"
        
        advice = "Mer belle" if alert == "🟢" else "Prudence" if alert == "🟡" else "DANGER"
        fuel = "\n⛽ <b>Vent de face :</b> surplus carburant conseillé" if data['wind_speed'] > 22 else ""
        target = "🐟 THIOF ⭐⭐⭐" if data['sst'] < 21 else "🐟 THON / ESPADON ⭐⭐"

        report += f"📍 <b>{name}</b> {alert}\n"
        report += f"🌡️ {data['sst']}°C {trend} | 🌊 {data['vhm0']}m\n"
        report += f"🌬️ {data['wind_speed']}km/h ({data['wind_dir']})\n"
        report += f"🔮 <i>Demain: {forecast}</i>\n"
        report += f"🎣 {target}\n<i>{advice}</i>{fuel}\n\n"
        
        web_json.append({**{"zone": name, "trend": trend, "alert": alert, "advice": advice, "forecast": forecast}, **data})

    report += f"───────────────────\n📱 <b>GPS :</b> https://doundou969.github.io/sunu-blue-tech/"
    
    with open('data.json', 'w') as f: json.dump(web_json, f, indent=4)
    if TG_TOKEN and TG_ID:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      data={"chat_id": TG_ID, "text": report, "parse_mode": "HTML", "disable_web_page_preview": "true"})

if __name__ == "__main__":
    main()
