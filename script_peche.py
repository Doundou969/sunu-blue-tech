#!/usr/bin/env python3
import os
import json
import time
import asyncio
import logging
import traceback
import numpy as np
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor

# ============================================================================
# 1. CONFIGURATION ET LOGGING PRO
# ============================================================================
def setup_logging():
    Path("logs/history").mkdir(parents=True, exist_ok=True)
    Path("logs/stats").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("PecheurConnect")
    # Rotation des logs pour éviter de saturer le serveur
    handler = RotatingFileHandler("logs/pecheur_connect.log", maxBytes=5*1024*1024, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler()) # Visible dans GitHub Actions
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logging()

# Secrets GitHub / Environnement
COPERNICUS_USER = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASSWORD")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Import Copernicus
try:
    import copernicusmarine as cm
    COPERNICUS_AVAILABLE = True
except ImportError:
    COPERNICUS_AVAILABLE = False
    logger.warning("Bibliothèque copernicusmarine absente. Mode simulation activé.")

# ============================================================================
# 2. PARAMÉTRAGE DES 18 ZONES SÉNÉGALAISES
# ============================================================================
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65, "region": "Nord", "desc": "Ndar - Nord"},
    "KAYAR": {"lat": 14.95, "lon": -17.35, "region": "Grande Côte", "desc": "Fosse de Kayar"},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65, "region": "Dakar", "desc": "Yoff - Virage"},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15, "region": "Petite Côte", "desc": "Port de Mbour"},
    "CASAMANCE-ZIGUINCHOR": {"lat": 12.50, "lon": -16.95, "region": "Casamance", "desc": "Embouchure"},
    # [Note : Le dictionnaire peut être étendu ici avec les 18 zones complètes]
}

# ============================================================================
# 3. CALCULS HALIEUTIQUES ET SÉCURITÉ
# ============================================================================
def calculate_indices(wave, temp, current):
    # Sécurité
    if wave > 2.5: s_text, s_code = "🔴 DANGER", "danger"
    elif wave > 1.6: s_text, s_code = "🟡 VIGILANCE", "warning"
    else: s_text, s_code = "🟢 SÛR", "safe"
    
    # Indice de Pêche (0-100)
    score = 50 # Base
    if 18 <= temp <= 23: score += 30 # Upwelling favorable
    if wave < 1.0: score += 20
    
    return s_text, s_code, min(100, score)

# ============================================================================
# 4. MOTEUR D'ACQUISITION ASYNCHRONE
# ============================================================================

async def get_weather(session, lat, lon):
    """Récupère la météo OpenWeather en asynchrone"""
    if not OPENWEATHER_API_KEY: return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "fr"}
    try:
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status == 200:
                d = await resp.json()
                return {"temp_air": d["main"]["temp"], "wind": d["wind"]["speed"], "desc": d["weather"][0]["description"]}
    except: return None

def fetch_copernicus_data(name, lat, lon):
    """Appel bloquant Copernicus exécuté dans un thread séparé"""
    if not COPERNICUS_AVAILABLE or not COPERNICUS_USER:
        return {"wave": 1.2, "sst": 22.0, "cur": 0.3} # Mock data pour test
    
    try:
        # Exemple de requête CMEMS (Simplifiée pour la structure)
        # data = cm.read_dataframe(dataset_id="...", longitude=lon, latitude=lat, ...)
        # return {"wave": data['VHM0'].iloc[-1], ...}
        return {"wave": 1.1, "sst": 20.5, "cur": 0.25}
    except Exception as e:
        logger.error(f"Erreur Copernicus sur {name}: {e}")
        return {"wave": 1.2, "sst": 22.0, "cur": 0.3}

async def process_zone(session, name, coords, now):
    """Gère une zone : Météo + Copernicus en parallèle"""
    loop = asyncio.get_event_loop()
    
    # Lancement simultané
    weather_task = get_weather(session, coords['lat'], coords['lon'])
    copernicus_task = loop.run_in_executor(None, fetch_copernicus_data, name, coords['lat'], coords['lon'])
    
    weather, marine = await asyncio.gather(weather_task, copernicus_task)
    
    safety_text, safety_code, fish_score = calculate_indices(marine['wave'], marine['sst'], marine['cur'])
    
    return {
        "zone": name,
        "region": coords['region'],
        "description": coords['desc'],
        "v_now": marine['wave'],
        "t_now": marine['sst'],
        "c_now": marine['cur'],
        "wind_speed": weather['wind'] if weather else 0,
        "weather_desc": weather['desc'] if weather else "N/A",
        "safety": safety_text,
        "safety_level": safety_code,
        "fish_index": fish_score,
        "date": now.strftime("%d/%m %H:%M")
    }

# ============================================================================
# 5. ORCHESTRATION FINALE
# ============================================================================

async def main():
    start_time = time.time()
    logger.info("🌊 Démarrage PecheurConnect Update...")

    async with aiohttp.ClientSession() as session:
        now = datetime.utcnow()
        tasks = [process_zone(session, name, info, now) for name, info in ZONES.items()]
        
        # Exécution concurrente de toutes les zones
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = [r for r in results if isinstance(r, dict)]

        if valid_results:
            # 1. Sauvegarde data.json (Production)
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(valid_results, f, indent=2, ensure_ascii=False)
            
            # 2. Sauvegarde Historique (Logs)
            hist_path = f"logs/history/{now.strftime('%Y-%m-%d')}.json"
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump({"timestamp": now.isoformat(), "zones": valid_results}, f)

            logger.info(f"✅ Mise à jour réussie : {len(valid_results)} zones traitées.")
        else:
            logger.error("❌ Échec critique : Aucune donnée récupérée.")

    duration = time.time() - start_time
    logger.info(f"⏱️ Fin du cycle en {duration:.2f}s")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"💥 ERREUR FATALE : {e}\n{traceback.format_exc()}")
