#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
import copernicusmarine as cm
from datetime import datetime, timedelta
from pathlib import Path
import requests
import warnings

warnings.filterwarnings('ignore')

# Variables d'environnement
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

def fetch_data():
    """Récupère les données marines"""
    log("🔐 Connexion à Copernicus...")
    
    if not COPERNICUS_USER or not COPERNICUS_PASS:
        log("❌ Identifiants Copernicus manquants")
        return None
    
    try:
        # Login
        cm.login(username=COPERNICUS_USER, password=COPERNICUS_PASS)
        log("✅ Connecté")
        
        log("📡 Chargement datasets...")
        
        # Utiliser read_dataframe au lieu de open_dataset
        now = datetime.utcnow()
        results = []
        
        for name, coords in ZONES.items():
            try:
                log(f"📍 {name}...")
                
                # Température (utiliser subset au lieu de open_dataset)
                temp_data = cm.subset(
                    dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
                    variables=["thetao"],
                    minimum_longitude=coords["lon"] - 0.1,
                    maximum_longitude=coords["lon"] + 0.1,
                    minimum_latitude=coords["lat"] - 0.1,
                    maximum_latitude=coords["lat"] + 0.1,
                    start_datetime=now - timedelta(hours=12),
                    end_datetime=now,
                    username=COPERNICUS_USER,
                    password=COPERNICUS_PASS
                )
                
                # Extraire température
                if temp_data and 'thetao' in temp_data.variables:
                    temp_arr = temp_data['thetao'].values
                    # Prendre la valeur la plus récente en surface
                    if len(temp_arr.shape) >= 3:
                        temp = float(np.nanmean(temp_arr[0, 0, :, :]))
                    else:
                        temp = float(np.nanmean(temp_arr))
                    temp = round(temp, 1)
                else:
                    temp = 20.0  # Valeur par défaut
                
                # Courants
                current_data = cm.subset(
                    dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
                    variables=["uo", "vo"],
                    minimum_longitude=coords["lon"] - 0.1,
                    maximum_longitude=coords["lon"] + 0.1,
                    minimum_latitude=coords["lat"] - 0.1,
                    maximum_latitude=coords["lat"] + 0.1,
                    start_datetime=now - timedelta(hours=12),
                    end_datetime=now,
                    username=COPERNICUS_USER,
                    password=COPERNICUS_PASS
                )
                
                if current_data and 'uo' in current_data.variables and 'vo' in current_data.variables:
                    u_arr = current_data['uo'].values
                    v_arr = current_data['vo'].values
                    if len(u_arr.shape) >= 3:
                        u = float(np.nanmean(u_arr[0, 0, :, :]))
                        v = float(np.nanmean(v_arr[0, 0, :, :]))
                    else:
                        u = float(np.nanmean(u_arr))
                        v = float(np.nanmean(v_arr))
                    current = round(float(np.sqrt(u**2 + v**2)), 2)
                else:
                    current = 0.3  # Valeur par défaut
                
                # Vagues
                wave_data = cm.subset(
                    dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                    variables=["VHM0"],
                    minimum_longitude=coords["lon"] - 0.1,
                    maximum_longitude=coords["lon"] + 0.1,
                    minimum_latitude=coords["lat"] - 0.1,
                    maximum_latitude=coords["lat"] + 0.1,
                    start_datetime=now - timedelta(hours=12),
                    end_datetime=now,
                    username=COPERNICUS_USER,
                    password=COPERNICUS_PASS
                )
                
                if wave_data and 'VHM0' in wave_data.variables:
                    wave_arr = wave_data['VHM0'].values
                    wave = float(np.nanmean(wave_arr[-1]))  # Dernière valeur
                    wave = round(wave, 2)
                else:
                    wave = 1.5  # Valeur par défaut
                
                # Prévisions 24h
                forecast = []
                try:
                    forecast_data = cm.subset(
                        dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                        variables=["VHM0"],
                        minimum_longitude=coords["lon"] - 0.1,
                        maximum_longitude=coords["lon"] + 0.1,
                        minimum_latitude=coords["lat"] - 0.1,
                        maximum_latitude=coords["lat"] + 0.1,
                        start_datetime=now,
                        end_datetime=now + timedelta(hours=24),
                        username=COPERNICUS_USER,
                        password=COPERNICUS_PASS
                    )
                    
                    if forecast_data and 'VHM0' in forecast_data.variables:
                        times = forecast_data['time'].values[:8]
                        waves = forecast_data['VHM0'].values[:8]
                        
                        for i, t in enumerate(times):
                            forecast.append({
                                "time": pd.to_datetime(t).strftime("%H:%M"),
                                "wave": round(float(np.nanmean(waves[i])), 2)
                            })
                except:
                    pass
                
                # Calcul sécurité
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
                
                # Index de pêche
                if 18 <= temp <= 24 and wave < 1.5:
                    fish = "🐟🐟🐟 EXCELLENT"
                elif temp < 22 and wave < 2.0:
                    fish = "🐟🐟 BON"
                else:
                    fish = "🐟 MOYEN"
                
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
                
                log(f"  ✅ {safety} | 🌊 {wave}m | 🌡️ {temp}°C")
                
            except Exception as e:
                log(f"  ⚠️ Erreur {name}: {str(e)[:50]}")
                # Ajouter des valeurs par défaut
                results.append({
                    "zone": name,
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "v_now": 1.5,
                    "t_now": 22.0,
                    "c_now": 0.3,
                    "index": "🐟 MOYEN",
                    "safety": "🟡 VIGILANCE",
                    "safety_level": "caution",
                    "color": "#ffc107",
                    "date": now.strftime("%d/%m %H:%M"),
                    "forecast": [],
                    "recommendations": ["Données en cours de récupération"]
                })
                continue
        
        return results
        
    except Exception as e:
        log(f"❌ Erreur: {str(e)}")
        return None

def send_telegram(data):
    """Envoi Telegram"""
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
        log(f"⚠️ Telegram: {str(e)[:30]}")

def main():
    log("="*50)
    log("🇸🇳 PECHEURCONNECT START")
    log("="*50)
    
    # Récupérer données
    data = fetch_data()
    
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
