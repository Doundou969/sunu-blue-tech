#!/usr/bin/env python3
"""
PecheurConnect v2.0 - Version complète
- Météo (vent, pluie, visibilité)
- Marées en temps réel
- 18 zones au lieu de 5
"""

import os
import json
import numpy as np
import pandas as pd
import copernicusmarine as cm
import requests
from datetime import datetime, timedelta
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Configuration API
COPERNICUS_USER = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASSWORD")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WORLDTIDES_API_KEY = os.getenv("WORLDTIDES_API_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

# 18 ZONES ÉTENDUES
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65, "desc": "Ndar - Nord", "region": "Nord"},
    "GANDIOL": {"lat": 16.15, "lon": -16.55, "desc": "Gandiol", "region": "Nord"},
    "KAYAR": {"lat": 14.95, "lon": -17.35, "desc": "Kayar", "region": "Grande Côte"},
    "LOMPOUL": {"lat": 15.35, "lon": -16.85, "desc": "Lompoul", "region": "Grande Côte"},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65, "desc": "Yoff", "region": "Dakar"},
    "DAKAR-SOUMBEDIOUNE": {"lat": 14.68, "lon": -17.46, "desc": "Soumbédioune", "region": "Dakar"},
    "DAKAR-HANN": {"lat": 14.73, "lon": -17.43, "desc": "Hann", "region": "Dakar"},
    "RUFISQUE": {"lat": 14.72, "lon": -17.28, "desc": "Rufisque", "region": "Dakar"},
    "BARGNY": {"lat": 14.70, "lon": -17.23, "desc": "Bargny", "region": "Dakar"},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15, "desc": "Mbour-Joal", "region": "Petite Côte"},
    "NIANING": {"lat": 14.45, "lon": -17.10, "desc": "Nianing", "region": "Petite Côte"},
    "SALY": {"lat": 14.45, "lon": -17.00, "desc": "Saly", "region": "Petite Côte"},
    "PALMARIN": {"lat": 14.23, "lon": -16.80, "desc": "Palmarin", "region": "Sine Saloum"},
    "FOUNDIOUGNE": {"lat": 14.13, "lon": -16.47, "desc": "Foundiougne", "region": "Sine Saloum"},
    "CASAMANCE-ZIGUINCHOR": {"lat": 12.50, "lon": -16.95, "desc": "Ziguinchor", "region": "Casamance"},
    "CASAMANCE-CAP-SKIRRING": {"lat": 12.40, "lon": -16.75, "desc": "Cap Skirring", "region": "Casamance"},
    "KAFOUNTINE": {"lat": 12.92, "lon": -16.75, "desc": "Kafountine", "region": "Casamance"},
    "MISSIRAH": {"lat": 13.93, "lon": -16.75, "desc": "Missirah", "region": "Sine Saloum"}
}

DATASETS = {
    "temperature": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
    "current": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
    "waves": "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
}


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    emoji = {"ERROR": "❌", "WARNING": "⚠️", "SUCCESS": "✅", "INFO": "ℹ️"}
    print(f"[{timestamp}] {emoji.get(level, 'ℹ️')} {msg}")


def get_weather_data(lat, lon):
    """Récupère météo OpenWeatherMap"""
    if not OPENWEATHER_API_KEY:
        return None
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "fr"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "wind_speed": round(data["wind"]["speed"], 1),
                "wind_direction": data["wind"].get("deg", 0),
                "wind_gust": round(data["wind"].get("gust", 0), 1),
                "precipitation": data.get("rain", {}).get("1h", 0),
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "visibility": data.get("visibility", 10000) / 1000,
                "clouds": data["clouds"]["all"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"]
            }
    except:
        return None


def get_tide_data(lat, lon):
    """Récupère données marées"""
    if not WORLDTIDES_API_KEY:
        return None
    
    try:
        url = "https://www.worldtides.info/api/v3"
        now = datetime.utcnow()
        start = int(now.timestamp())
        
        params = {
            "heights": "",
            "extremes": "",
            "lat": lat,
            "lon": lon,
            "start": start,
            "length": 172800,
            "key": WORLDTIDES_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            extremes = data.get("extremes", [])[:6]
            
            tides = []
            for extreme in extremes:
                tide_time = datetime.fromtimestamp(extreme["dt"])
                tides.append({
                    "time": tide_time.strftime("%H:%M"),
                    "height": round(extreme["height"], 2),
                    "type": "Haute" if extreme["type"] == "High" else "Basse"
                })
            
            return {"tides": tides}
    except:
        return None


def calculate_safety_with_weather(wave, current, wind_speed, visibility, precipitation):
    """Calcul sécurité avec météo"""
    danger_score = 0
    reasons = []
    
    # Vagues (40%)
    if wave > 3.0:
        danger_score += 40
        reasons.append(f"Vagues {wave}m")
    elif wave > 2.1:
        danger_score += 25
    elif wave > 1.5:
        danger_score += 15
    
    # Courants (20%)
    if current > 1.0:
        danger_score += 20
    elif current > 0.6:
        danger_score += 12
    
    # Vent (20%)
    if wind_speed > 15:
        danger_score += 20
        reasons.append(f"Vent {wind_speed}m/s")
    elif wind_speed > 12:
        danger_score += 12
    elif wind_speed > 8:
        danger_score += 6
    
    # Visibilité (10%)
    if visibility < 1:
        danger_score += 10
        reasons.append(f"Visibilité {visibility}km")
    elif visibility < 5:
        danger_score += 5
    
    # Pluie (10%)
    if precipitation > 10:
        danger_score += 10
        reasons.append("Pluie forte")
    elif precipitation > 2:
        danger_score += 5
    
    if danger_score >= 60:
        return "🔴 DANGER", "danger", "#d32f2f", danger_score, reasons
    elif danger_score >= 35:
        return "🟠 PRUDENCE", "warning", "#ff9800", danger_score, reasons
    elif danger_score >= 20:
        return "🟡 VIGILANCE", "caution", "#ffc107", danger_score, reasons
    else:
        return "🟢 SÛR", "safe", "#28a745", danger_score, reasons


def fetch_zone_data(name, coords, now):
    """Récupère données pour une zone"""
    log(f"Traitement {name}...")
    
    wave, temp, current = None, None, None
    
    # Données océanographiques
    try:
        wave_df = cm.read_dataframe(
            dataset_id=DATASETS["waves"],
            variables=["VHM0"],
            minimum_longitude=coords["lon"] - 0.1,
            maximum_longitude=coords["lon"] + 0.1,
            minimum_latitude=coords["lat"] - 0.1,
            maximum_latitude=coords["lat"] + 0.1,
            start_datetime=now - timedelta(hours=6),
            end_datetime=now,
            username=COPERNICUS_USER,
            password=COPERNICUS_PASS
        )
        
        if wave_df is not None and len(wave_df) > 0 and 'VHM0' in wave_df.columns:
            wave_values = wave_df['VHM0'].dropna()
            if len(wave_values) > 0:
                wave = round(float(wave_values.iloc[-1]), 2)
    except:
        pass
    
    try:
        temp_df = cm.read_dataframe(
            dataset_id=DATASETS["temperature"],
            variables=["thetao"],
            minimum_longitude=coords["lon"] - 0.1,
            maximum_longitude=coords["lon"] + 0.1,
            minimum_latitude=coords["lat"] - 0.1,
            maximum_latitude=coords["lat"] + 0.1,
            minimum_depth=0,
            maximum_depth=1,
            start_datetime=now - timedelta(hours=12),
            end_datetime=now,
            username=COPERNICUS_USER,
            password=COPERNICUS_PASS
        )
        
        if temp_df is not None and len(temp_df) > 0 and 'thetao' in temp_df.columns:
            temp_values = temp_df['thetao'].dropna()
            if len(temp_values) > 0:
                temp = round(float(temp_values.iloc[-1]), 1)
    except:
        pass
    
    try:
        current_df = cm.read_dataframe(
            dataset_id=DATASETS["current"],
            variables=["uo", "vo"],
            minimum_longitude=coords["lon"] - 0.1,
            maximum_longitude=coords["lon"] + 0.1,
            minimum_latitude=coords["lat"] - 0.1,
            maximum_latitude=coords["lat"] + 0.1,
            minimum_depth=0,
            maximum_depth=1,
            start_datetime=now - timedelta(hours=12),
            end_datetime=now,
            username=COPERNICUS_USER,
            password=COPERNICUS_PASS
        )
        
        if current_df is not None and len(current_df) > 0:
            if 'uo' in current_df.columns and 'vo' in current_df.columns:
                u = current_df['uo'].dropna().iloc[-1] if len(current_df['uo'].dropna()) > 0 else 0
                v = current_df['vo'].dropna().iloc[-1] if len(current_df['vo'].dropna()) > 0 else 0
                current = round(float(np.sqrt(u**2 + v**2)), 2)
    except:
        pass
    
    # Valeurs par défaut
    if wave is None:
        wave = 1.5
    if temp is None:
        temp = 22.0
    if current is None:
        current = 0.3
    
    # Météo
    weather = get_weather_data(coords["lat"], coords["lon"])
    wind_speed = weather["wind_speed"] if weather else 5.0
    visibility = weather["visibility"] if weather else 10.0
    precipitation = weather["precipitation"] if weather else 0.0
    
    # Marées
    tide = get_tide_data(coords["lat"], coords["lon"])
    
    # Calcul sécurité
    safety, safety_level, color, danger_score, reasons = calculate_safety_with_weather(
        wave, current, wind_speed, visibility, precipitation
    )
    
    # Index pêche simplifié
    score = 0
    if 18 <= temp <= 24:
        score += 3
    if 0.2 <= current <= 0.5:
        score += 2
    if wave < 1.5:
        score += 2
    
    if score >= 5:
        fish = "🐟🐟🐟 EXCELLENT"
        fish_level = "excellent"
    elif score >= 3:
        fish = "🐟🐟 BON"
        fish_level = "good"
    else:
        fish = "🐟 MOYEN"
        fish_level = "moderate"
    
    result = {
        "zone": name,
        "description": coords["desc"],
        "region": coords["region"],
        "lat": coords["lat"],
        "lon": coords["lon"],
        "v_now": wave,
        "t_now": temp,
        "c_now": current,
        "wind_speed": wind_speed,
        "wind_direction": weather["wind_direction"] if weather else 0,
        "visibility": visibility,
        "precipitation": precipitation,
        "weather_desc": weather["description"] if weather else "Non disponible",
        "humidity": weather["humidity"] if weather else 0,
        "clouds": weather["clouds"] if weather else 0,
        "index": fish,
        "fish_level": fish_level,
        "safety": safety,
        "safety_level": safety_level,
        "color": color,
        "danger_score": danger_score,
        "danger_reasons": reasons,
        "date": now.strftime("%d/%m %H:%M"),
        "timestamp": now.isoformat(),
        "tide": tide,
        "forecast": [],
        "recommendations": []
    }
    
    log(f"  {safety} | 🌊{wave}m | 🌡️{temp}°C | 🌬️{wind_speed}m/s", "SUCCESS")
    
    return result


def fetch_data():
    """Récupère données pour toutes les zones"""
    log("Connexion à Copernicus...")
    
    if not COPERNICUS_USER or not COPERNICUS_PASS:
        log("Identifiants manquants", "ERROR")
        return None
    
    try:
        cm.login(username=COPERNICUS_USER, password=COPERNICUS_PASS)
        log("Connecté", "SUCCESS")
        
        now = datetime.utcnow()
        results = []
        
        for name, coords in ZONES.items():
            try:
                result = fetch_zone_data(name, coords, now)
                results.append(result)
            except Exception as e:
                log(f"Erreur {name}: {str(e)}", "ERROR")
                continue
        
        log(f"Collecte terminée: {len(results)}/{len(ZONES)} zones", "SUCCESS")
        return results
        
    except Exception as e:
        log(f"Erreur critique: {str(e)}", "ERROR")
        return None


def save_data(data):
    """Sauvegarde data.json"""
    try:
        Path("logs").mkdir(exist_ok=True)
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log(f"data.json sauvegardé ({len(data)} zones)", "SUCCESS")
        return True
    except Exception as e:
        log(f"Erreur sauvegarde: {str(e)}", "ERROR")
        return False


def send_telegram(data):
    """Envoie alerte Telegram"""
    if not TG_TOKEN or not TG_ID:
        return
    
    # Grouper par région
    regions = {}
    for zone in data:
        region = zone["region"]
        if region not in regions:
            regions[region] = []
        regions[region].append(zone)
    
    message = "🌊 *PECHEURCONNECT v2.0*\n"
    message += f"📊 {len(data)} zones | {len(regions)} régions\n\n"
    
    for region, zones in regions.items():
        message += f"📍 *{region}*\n"
        for z in zones:
            message += f"• {z['zone']}: {z['safety']}\n"
        message += "\n"
    
    message += f"🕐 {data[0]['date']} UTC"
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
        log("Telegram envoyé", "SUCCESS")
    except:
        pass


def main():
    start = datetime.now()
    
    log("=" * 60)
    log("PECHEURCONNECT v2.0 - DÉMARRAGE")
    log("18 zones | Météo | Marées")
    log("=" * 60)
    
    data = fetch_data()
    
    if not data:
        log("Échec", "ERROR")
        exit(1)
    
    if not save_data(data):
        log("Échec sauvegarde", "ERROR")
        exit(1)
    
    send_telegram(data)
    
    duration = (datetime.now() - start).total_seconds()
    log(f"Terminé en {duration:.2f}s", "SUCCESS")
    log("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Erreur fatale: {str(e)}", "ERROR")
        exit(1)
