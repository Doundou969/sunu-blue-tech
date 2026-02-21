#!/usr/bin/env python3
"""
PecheurConnect v2.1 - Système complet avec historique + Bot Telegram
Auteur: PecheurConnect Team
Date: 2026
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
import time
from functools import lru_cache

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Variables d'environnement
COPERNICUS_USER = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASSWORD")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
WORLDTIDES_API_KEY = os.getenv("WORLDTIDES_API_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Pour le bot interactif

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
    "MISSIRAH": {"lat": 13.93, "lon": -16.75, "desc": "Missirah", "region": "Sine Saloum"},
    "CASAMANCE-ZIGUINCHOR": {"lat": 12.50, "lon": -16.95, "desc": "Ziguinchor", "region": "Casamance"},
    "CASAMANCE-CAP-SKIRRING": {"lat": 12.40, "lon": -16.75, "desc": "Cap Skirring", "region": "Casamance"},
    "KAFOUNTINE": {"lat": 12.92, "lon": -16.75, "desc": "Kafountine", "region": "Casamance"}
}

DATASETS = {
    "temperature": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
    "current": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
    "waves": "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
}

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def log(msg, level="INFO"):
    """Affiche un message avec timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    emoji = {"ERROR": "❌", "WARNING": "⚠️", "SUCCESS": "✅", "INFO": "ℹ️", "DEBUG": "🔍"}
    print(f"[{timestamp}] {emoji.get(level, 'ℹ️')} {msg}")


def calculate_safety_level(wave, current):
    """Calcule le niveau de sécurité maritime"""
    if wave > 3.0 or current > 1.0:
        return "🔴 DANGER", "danger", "#d32f2f"
    elif wave > 2.1 or current > 0.6:
        return "🟠 PRUDENCE", "warning", "#ff9800"
    elif wave > 1.5 or current > 0.4:
        return "🟡 VIGILANCE", "caution", "#ffc107"
    else:
        return "🟢 SÛR", "safe", "#28a745"


def calculate_fish_index(temp, current, wave):
    """Calcule l'indice de pêche"""
    score = 0
    factors = []
    
    if 18 <= temp <= 24:
        score += 3
        factors.append("Température idéale")
    elif 15 <= temp <= 27:
        score += 1
        factors.append("Température acceptable")
    
    if 0.2 <= current <= 0.5:
        score += 2
        factors.append("Courants favorables")
    elif current < 0.2:
        score += 1
        factors.append("Courants faibles")
    
    if wave < 1.0:
        score += 3
        factors.append("Mer très calme")
    elif wave < 1.5:
        score += 2
        factors.append("Mer calme")
    elif wave < 2.0:
        score += 1
        factors.append("Mer modérée")
    
    if score >= 7:
        return "🐟🐟🐟 EXCELLENT", "excellent", factors
    elif score >= 5:
        return "🐟🐟 BON", "good", factors
    elif score >= 3:
        return "🐟 MOYEN", "moderate", factors
    else:
        return "🎣 FAIBLE", "poor", factors


def generate_recommendations(safety_level, fish_level, wave, current, temp):
    """Génère des recommandations"""
    recommendations = []
    
    if safety_level == "danger":
        recommendations.extend([
            "NE PAS SORTIR EN MER",
            "Restez à quai - Conditions dangereuses"
        ])
    elif safety_level == "warning":
        recommendations.extend([
            "Sortie fortement déconseillée",
            "Si nécessaire, restez près des côtes"
        ])
    elif safety_level == "caution":
        recommendations.extend([
            "Vigilance accrue recommandée",
            "Sortie en groupe privilégiée"
        ])
    else:
        recommendations.append("Conditions sûres pour la navigation")
    
    if fish_level == "excellent":
        recommendations.append("Conditions OPTIMALES pour la pêche")
    elif fish_level == "good":
        recommendations.append("Bonnes conditions de pêche")
    elif fish_level == "moderate":
        recommendations.append("Pêche possible - Conditions moyennes")
    
    return recommendations


# ============================================================================
# MÉTÉO OPENWEATHER
# ============================================================================

@lru_cache(maxsize=50)
def get_weather_data_cached(lat, lon, cache_timestamp):
    """Récupère météo avec cache 30 min"""
    if not OPENWEATHER_API_KEY:
        return None
    
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": round(lat, 2),
            "lon": round(lon, 2),
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
                "visibility": round(data.get("visibility", 10000) / 1000, 1),
                "clouds": data["clouds"]["all"],
                "weather_description": data["weather"][0]["description"],
                "weather_icon": data["weather"][0]["icon"]
            }
    except Exception as e:
        log(f"Weather API error: {str(e)[:50]}", "WARNING")
    
    return None


def get_weather_for_zone(lat, lon):
    """Wrapper avec cache automatique"""
    cache_timestamp = int(time.time() / 1800)  # 30 min
    return get_weather_data_cached(lat, lon, cache_timestamp)


# ============================================================================
# RÉCUPÉRATION DONNÉES MARINES
# ============================================================================

def fetch_zone_data(name, coords, now):
    """Récupère données pour une zone"""
    log(f"Traitement {name}...")
    
    wave, temp, current = None, None, None
    
    # VAGUES
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
    except Exception as e:
        log(f"  Vagues: {str(e)[:30]}", "WARNING")
    
    # TEMPÉRATURE
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
    except Exception as e:
        log(f"  Température: {str(e)[:30]}", "WARNING")
    
    # COURANTS
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
    except Exception as e:
        log(f"  Courants: {str(e)[:30]}", "WARNING")
    
    # Valeurs par défaut
    if wave is None:
        wave = 1.5
    if temp is None:
        temp = 22.0
    if current is None:
        current = 0.3
    
    # Météo
    weather = get_weather_for_zone(coords["lat"], coords["lon"])
    wind_speed = weather["wind_speed"] if weather else 5.0
    visibility = weather["visibility"] if weather else 10.0
    precipitation = weather["precipitation"] if weather else 0.0
    weather_desc = weather["weather_description"] if weather else "Non disponible"
    humidity = weather["humidity"] if weather else 0
    clouds = weather["clouds"] if weather else 0
    wind_direction = weather["wind_direction"] if weather else 0
    
    # Calculs
    safety, safety_level, color = calculate_safety_level(wave, current)
    fish, fish_level, fish_factors = calculate_fish_index(temp, current, wave)
    recommendations = generate_recommendations(safety_level, fish_level, wave, current, temp)
    
    danger_score = min(100, int(
        (wave / 4.0) * 40 +
        (current / 1.5) * 30 +
        ((30 - temp) / 15 if temp < 30 else 0) * 30
    ))
    
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
        "wind_direction": wind_direction,
        "visibility": visibility,
        "precipitation": precipitation,
        "weather_desc": weather_desc,
        "humidity": humidity,
        "clouds": clouds,
        "index": fish,
        "fish_level": fish_level,
        "fish_factors": fish_factors,
        "safety": safety,
        "safety_level": safety_level,
        "color": color,
        "danger_score": danger_score,
        "date": now.strftime("%d/%m %H:%M"),
        "timestamp": now.isoformat(),
        "forecast": [],
        "recommendations": recommendations
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


# ============================================================================
# HISTORIQUE
# ============================================================================

def save_to_history(data):
    """Sauvegarde dans l'historique pour graphiques"""
    history_dir = Path("logs/history")
    history_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now()
    date_key = timestamp.strftime("%Y-%m-%d")
    
    history_file = history_dir / f"{date_key}.json"
    
    # Charger historique existant du jour
    daily_history = []
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            daily_history = json.load(f)
    
    # Ajouter nouvelle entrée
    daily_history.append({
        "timestamp": timestamp.isoformat(),
        "zones": data
    })
    
    # Sauvegarder
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(daily_history, f, ensure_ascii=False, indent=2)
    
    log(f"Historique: {date_key} ({len(daily_history)} entrées)", "SUCCESS")
    
    # Nettoyer > 30 jours
    cleanup_old_history(history_dir, 30)


def cleanup_old_history(history_dir, days_to_keep):
    """Supprime l'historique > X jours"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    for file in history_dir.glob("*.json"):
        try:
            file_date = datetime.strptime(file.stem, "%Y-%m-%d")
            if file_date < cutoff_date:
                file.unlink()
                log(f"Nettoyage: {file.name}", "DEBUG")
        except:
            continue


def generate_zone_statistics(zone_name):
    """Génère stats 7 jours pour une zone"""
    history_dir = Path("logs/history")
    
    if not history_dir.exists():
        return None
    
    zone_data = []
    
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        date_key = date.strftime("%Y-%m-%d")
        history_file = history_dir / f"{date_key}.json"
        
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                daily_data = json.load(f)
                
                for entry in daily_data:
                    for zone in entry["zones"]:
                        if zone["zone"] == zone_name:
                            zone_data.append({
                                "timestamp": entry["timestamp"],
                                "date": date_key,
                                "wave": zone["v_now"],
                                "temp": zone["t_now"],
                                "current": zone["c_now"],
                                "wind": zone.get("wind_speed", 0),
                                "safety_level": zone["safety_level"],
                                "fish_level": zone["fish_level"]
                            })
    
    if not zone_data:
        return None
    
    waves = [d["wave"] for d in zone_data]
    temps = [d["temp"] for d in zone_data]
    winds = [d["wind"] for d in zone_data]
    
    stats = {
        "zone": zone_name,
        "period": "7 jours",
        "data_points": len(zone_data),
        "history": zone_data[-168:],
        "statistics": {
            "waves": {
                "min": round(min(waves), 2),
                "max": round(max(waves), 2),
                "avg": round(np.mean(waves), 2),
                "trend": calculate_trend(waves)
            },
            "temperature": {
                "min": round(min(temps), 1),
                "max": round(max(temps), 1),
                "avg": round(np.mean(temps), 1),
                "trend": calculate_trend(temps)
            },
            "wind": {
                "min": round(min(winds), 1),
                "max": round(max(winds), 1),
                "avg": round(np.mean(winds), 1),
                "trend": calculate_trend(winds)
            }
        },
        "safety_summary": {
            "safe": len([d for d in zone_data if d["safety_level"] == "safe"]),
            "caution": len([d for d in zone_data if d["safety_level"] == "caution"]),
            "warning": len([d for d in zone_data if d["safety_level"] == "warning"]),
            "danger": len([d for d in zone_data if d["safety_level"] == "danger"])
        },
        "best_day": find_best_day(zone_data),
        "worst_day": find_worst_day(zone_data)
    }
    
    return stats


def calculate_trend(values):
    """Calcule la tendance"""
    if len(values) < 2:
        return "stable"
    
    x = np.arange(len(values))
    slope = np.polyfit(x, values, 1)[0]
    
    if slope > 0.1:
        return "hausse"
    elif slope < -0.1:
        return "baisse"
    else:
        return "stable"


def find_best_day(zone_data):
    """Trouve le meilleur jour"""
    best = None
    best_score = -1
    
    for data in zone_data:
        score = 0
        if data["safety_level"] == "safe":
            score += 10
        if data["fish_level"] == "excellent":
            score += 10
        elif data["fish_level"] == "good":
            score += 5
        
        score -= data["wave"] * 2
        score -= abs(data["temp"] - 21) * 0.5
        
        if score > best_score:
            best_score = score
            best = data
    
    return {
        "date": best["date"] if best else None,
        "wave": best["wave"] if best else None,
        "temp": best["temp"] if best else None,
        "safety": best["safety_level"] if best else None
    }


def find_worst_day(zone_data):
    """Trouve le pire jour"""
    worst = None
    worst_score = 1000
    
    for data in zone_data:
        score = 0
        if data["safety_level"] == "danger":
            score += 10
        elif data["safety_level"] == "warning":
            score += 5
        
        score += data["wave"] * 3
        
        if score < worst_score:
            worst_score = score
            worst = data
    
    return {
        "date": worst["date"] if worst else None,
        "wave": worst["wave"] if worst else None,
        "safety": worst["safety_level"] if worst else None
    }


def generate_all_stats():
    """Génère stats pour toutes les zones"""
    stats_dir = Path("logs/stats")
    stats_dir.mkdir(parents=True, exist_ok=True)
    
    all_stats = {}
    
    for zone_name in ZONES.keys():
        stats = generate_zone_statistics(zone_name)
        if stats:
            all_stats[zone_name] = stats
            
            zone_file = stats_dir / f"{zone_name.lower().replace(' ', '_').replace('-', '_')}.json"
            with open(zone_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
    
    with open(stats_dir / "all_zones.json", "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    
    log(f"Stats générées: {len(all_stats)} zones", "SUCCESS")
    return all_stats


# ============================================================================
# SAUVEGARDE ET NOTIFICATIONS
# ============================================================================

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
    """Envoie alerte Telegram (notifications simples)"""
    if not TG_TOKEN or not TG_ID:
        return
    
    regions = {}
    for zone in data:
        region = zone["region"]
        if region not in regions:
            regions[region] = []
        regions[region].append(zone)
    
    message = "🌊 *PECHEURCONNECT v2.1*\n"
    message += f"📊 {len(data)} zones | {len(regions)} régions\n\n"
    
    for region, zones in regions.items():
        message += f"📍 *{region}*\n"
        for z in zones:
            message += f"• {z['zone']}: {z['safety']}\n"
        message += "\n"
    
    message += f"🕐 {data[0]['date']} UTC\n"
    
    # Ajouter info bot interactif si configuré
    if TELEGRAM_BOT_TOKEN:
        message += "\n🤖 *Bot interactif disponible!*\n"
        message += "Tapez /start pour commencer\n"
        message += "Tapez /conditions pour voir toutes les zones"
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
        log("Telegram envoyé", "SUCCESS")
    except:
        pass


def send_bot_broadcast(data):
    """Diffuse les nouvelles données via le bot (optionnel)"""
    if not TELEGRAM_BOT_TOKEN or not TG_ID:
        return
    
    # Créer un résumé court pour broadcast
    safe_count = len([z for z in data if z["safety_level"] == "safe"])
    danger_count = len([z for z in data if z["safety_level"] in ["danger", "warning"]])
    
    # Trouver les 3 meilleures zones
    best_zones = sorted(data, key=lambda x: x["v_now"])[:3]
    
    message = "🌊 *MISE À JOUR MÉTÉO MARINE* 🌊\n\n"
    message += f"✅ Zones sûres: {safe_count}/{len(data)}\n"
    
    if danger_count > 0:
        message += f"⚠️ Zones à risque: {danger_count}\n"
    
    message += "\n🏆 *MEILLEURES ZONES:*\n"
    for i, zone in enumerate(best_zones, 1):
        message += f"{i}. {zone['zone']}: {zone['v_now']}m\n"
    
    message += f"\n📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    message += "\nTapez /conditions pour plus de détails"
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TG_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
        log("Broadcast bot envoyé", "SUCCESS")
    except Exception as e:
        log(f"Erreur broadcast: {str(e)[:50]}", "WARNING")


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main():
    """Point d'entrée principal"""
    start = datetime.now()
    
    log("=" * 60)
    log("PECHEURCONNECT v2.1 - AVEC HISTORIQUE + BOT")
    log("18 zones | Météo | Historique 7 jours | Bot Telegram")
    log("=" * 60)
    
    data = fetch_data()
    
    if not data:
        log("Échec collecte", "ERROR")
        exit(1)
    
    if not save_data(data):
        log("Échec sauvegarde", "ERROR")
        exit(1)
    
    # Sauvegarder historique
    save_to_history(data)
    
    # Générer statistiques
    generate_all_stats()
    
    # Envoyer notifications
    send_telegram(data)  # Notification simple
    
    # Broadcast via bot interactif (si configuré)
    if TELEGRAM_BOT_TOKEN:
        send_bot_broadcast(data)
    
    duration = (datetime.now() - start).total_seconds()
    log(f"Terminé en {duration:.2f}s", "SUCCESS")
    
    # Info sur le bot
    if TELEGRAM_BOT_TOKEN:
        log("=" * 60)
        log("🤖 BOT TELEGRAM INTERACTIF ACTIVÉ", "SUCCESS")
        log("Les pêcheurs peuvent consulter les données à tout moment!", "INFO")
        log("Commandes: /start, /conditions, /zone, /alertes, etc.", "INFO")
    else:
        log("=" * 60)
        log("💡 Bot Telegram non configuré", "INFO")
        log("Ajoutez TELEGRAM_BOT_TOKEN dans .env pour l'activer", "INFO")
    
    log("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Erreur fatale: {str(e)}", "ERROR")
        exit(1)
