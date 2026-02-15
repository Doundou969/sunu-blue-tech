#!/usr/bin/env python3
import os
import json
import asyncio
import numpy as np
import pandas as pd
import copernicusmarine as cm
from datetime import datetime, timedelta
from pathlib import Path
import requests
import warnings

warnings.filterwarnings('ignore')

# Charger les variables d'environnement
COPERNICUS_USER = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65},
    "KAYAR": {"lat": 14.95, "lon": -17.35},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95}
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

async def fetch_data():
    log("🔐 Connexion à Copernicus...")
    
    if not COPERNICUS_USER or not COPERNICUS_PASS:
        log("❌ Identifiants Copernicus manquants")
        return None
    
    try:
        cm.login(username=COPERNICUS_USER, password=COPERNICUS_PASS)
        log("✅ Connecté")
        
        log("📡 Chargement datasets...")
        ds_temp = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
            username=COPERNICUS_USER,
            password=COPERNICUS_PASS
        )
        ds_cur = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
            username=COPERNICUS_USER,
            password=COPERNICUS_PASS
        )
        ds_wav = cm.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
            username=COPERNICUS_USER,
            password=COPERNICUS_PASS
        )
        log("✅ Datasets chargés")
        
        results = []
        now = datetime.utcnow()
        
        for name, coords in ZONES.items():
            try:
                log(f"📍 {name}...")
                
                # Température
                st = ds_temp.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                if 'depth' in st.coords:
                    st = st.isel(depth=0)
                temp = round(float(st["thetao"].values.flatten()[0]), 1)
                
                # Courant
                sc = ds_cur.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                if 'depth' in sc.coords:
                    sc = sc.isel(depth=0)
                u = float(sc["uo"].values.flatten()[0])
                v = float(sc["vo"].values.flatten()[0])
                current = round(float(np.sqrt(u**2 + v**2)), 2)
                
                # Vagues
                sw = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=now, method="nearest")
                wave = round(float(sw["VHM0"].values.flatten()[0]), 2)
                
                # Sécurité
                if wave > 3.0 or current > 1.0:
                    safety = "🔴 DANGER"
                    level = "danger"
                    color = "#d32f2f"
                elif wave > 2.1 or current > 0.6:
                    safety = "🟠 PRUDENCE"
                    level = "warning"
                    color = "#ff9800"
                elif wave > 1.5 or current > 0.4:
                    safety = "🟡 VIGILANCE"
                    level = "caution"
                    color = "#ffc107"
                else:
                    safety = "🟢 SÛR"
                    level = "safe"
                    color = "#28a745"
                
                # Pêche
                if 18 <= temp <= 24 and wave < 1.5:
                    fish = "🐟🐟🐟 EXCELLENT"
                elif temp < 22 and wave < 2.0:
                    fish = "🐟🐟 BON"
                else:
                    fish = "🐟 MOYEN"
                
                # Prévisions
                forecast = []
                try:
                    times = ds_wav.sel(
                        latitude=coords["lat"],
                        longitude=coords["lon"],
                        time=slice(now, now + timedelta(hours=24)),
                        method="nearest"
                    )
                    for t in times.time.values[:8]:
                        sw_f = ds_wav.sel(latitude=coords["lat"], longitude=coords["lon"], time=t, method="nearest")
                        forecast.append({
                            "time": pd.to_datetime(t).strftime("%H:%M"),
                            "wave": round(float(sw_f["VHM0"].values.flatten()[0]), 2)
                        })
                except:
                    pass
                
                results.append({
                    "zone": name,
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "v_now": wave,
                    "t_now": temp,
                    "c_now": current,
                    "index": fish,
                    "safety": safety,
                    "safety_level": level,
                    "color": color,
                    "date": now.strftime("%d/%m %H:%M"),
                    "forecast": forecast,
                    "recommendations": [f"{safety} - Vagues {wave}m"]
                })
                
                log(f"  ✅ {safety} | 🌊 {wave}m | 🐟 {fish}")
                
            except Exception as e:
                log(f"  ❌ Erreur: {e}")
                continue
        
        return results
        
    except Exception as e:
        log(f"❌ Erreur critique: {e}")
        return None

def send_telegram(data):
    if not TG_TOKEN or not TG_ID:
        log("⚠️ Telegram non configuré")
        return
    
    danger = len([z for z in data if "🔴" in z['safety']])
    
    if danger > 0:
        msg = f"🚨 *ALERTE PECHEURCONNECT*\n\n⚠️ {danger} zone(s) en DANGER\n\n"
    else:
        msg = "🌊 *PECHEURCONNECT - Rapport*\n\n"
    
    for z in data:
        msg += f"📍 *{z['zone']}*\n{z['safety']} | {z['index']}\n🌊 {z['v_now']}m | 🌡️ {z['t_now']}°C\n\n"
    
    msg += f"🕐 {data[0]['date']} UTC"
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
        log("✅ Telegram envoyé")
    except Exception as e:
        log(f"❌ Telegram: {e}")

def main():
    log("="*50)
    log("🇸🇳 PECHEURCONNECT START")
    log("="*50)
    
    # Récupérer données
    data = asyncio.run(fetch_data())
    
    if not data:
        log("❌ Aucune donnée")
        exit(1)
    
    # Créer dossier logs
    Path("logs").mkdir(exist_ok=True)
    
    # Sauvegarder
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    log(f"✅ data.json sauvegardé ({len(data)} zones)")
    
    # Telegram
    send_telegram(data)
    
    log("="*50)
    log("✅ TERMINÉ")
    log("="*50)

if __name__ == "__main__":
    main()
