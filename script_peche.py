import os
import json
import asyncio
import numpy as np
import pandas as pd
import copernicusmarine as cm
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from pathlib import Path

load_dotenv()

# Configuration des zones de pêche au Sénégal
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65},
    "KAYAR": {"lat": 14.95, "lon": -17.35},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95}
}

# Seuils de sécurité
THRESHOLDS = {
    "DANGER": {"wave": 3.0, "current": 1.0},
    "WARNING": {"wave": 2.1, "current": 0.6},
    "CAUTION": {"wave": 1.5, "current": 0.4}
}

class PecheurConnectLogger:
    """Gestionnaire de logs pour PecheurConnect"""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"log_{datetime.now().strftime('%Y%m')}.txt"
    
    def log(self, message, level="INFO"):
        """Enregistre un message dans le fichier de log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        print(f"{log_entry.strip()}")
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def log_execution(self, success, zones_count, errors_count):
        """Enregistre le résumé d'une exécution"""
        status = "SUCCESS" if success else "FAILURE"
        summary = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "zones_processed": zones_count,
            "errors": errors_count
        }
        
        history_file = self.log_dir / "execution_history.json"
        
        # Charger l'historique existant
        history = []
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        
        # Ajouter la nouvelle exécution
        history.append(summary)
        
        # Garder seulement les 100 dernières exécutions
        history = history[-100:]
        
        # Sauvegarder
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

logger = PecheurConnectLogger()

def calculate_safety_level(v_now, c_now):
    """Calcule le niveau de sécurité basé sur les vagues et courants"""
    if v_now > THRESHOLDS["DANGER"]["wave"] or c_now > THRESHOLDS["DANGER"]["current"]:
        return "🔴 DANGER", "danger", "#d32f2f"
    elif v_now > THRESHOLDS["WARNING"]["wave"] or c_now > THRESHOLDS["WARNING"]["current"]:
        return "🟠 PRUDENCE", "warning", "#ff9800"
    elif v_now > THRESHOLDS["CAUTION"]["wave"] or c_now > THRESHOLDS["CAUTION"]["current"]:
        return "🟡 VIGILANCE", "caution", "#ffc107"
    else:
        return "🟢 SÛR", "safe", "#28a745"

def calculate_fish_index(t_now, c_now, v_now):
    """Calcule l'index de pêche basé sur plusieurs facteurs"""
    score = 0
    
    # Température optimale : 18-24°C
    if 18 <= t_now <= 24:
        score += 3
    elif 15 <= t_now <= 27:
        score += 1
    
    # Courants modérés favorables (0.2-0.5 m/s)
    if 0.2 <= c_now <= 0.5:
        score += 2
    elif c_now < 0.2:
        score += 1
    
    # Mer calme
    if v_now < 1.5:
        score += 2
    elif v_now < 2.0:
        score += 1
    
    # Déterminer le niveau
    if score >= 6:
        return "🐟🐟🐟 EXCELLENT", "excellent"
    elif score >= 4:
        return "🐟🐟 BON", "good"
    elif score >= 2:
        return "🐟 MOYEN", "moderate"
    else:
        return "🎣 FAIBLE", "poor"

async def fetch_marine_data():
    """Récupère les données marines pour toutes les zones avec prévisions"""
    results = []
    errors = 0
    now = datetime.utcnow()
    next_24h = now + timedelta(hours=24)
    
    user = os.getenv("COPERNICUS_USERNAME")
    pw = os.getenv("COPERNICUS_PASSWORD")
    
    if not user or not pw:
        logger.log("Identifiants Copernicus manquants", "ERROR")
        return None, len(ZONES)
    
    try:
        logger.log("Connexion à Copernicus Marine Service...")
        cm.login(username=user, password=pw)
        
        logger.log("Chargement des datasets...")
        ds_temp = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
            username=user, password=pw
        )
        ds_cur = cm.open_dataset(
            dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
            username=user, password=pw
        )
        ds_wav = cm.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
            username=user, password=pw
        )
        
        for name, coords in ZONES.items():
            try:
                logger.log(f"Traitement de {name}...")
                
                # === DONNÉES ACTUELLES ===
                
                # Température de surface
                st = ds_temp.sel(
                    latitude=coords["lat"], 
                    longitude=coords["lon"], 
                    time=now, 
                    method="nearest"
                )
                if 'depth' in st.coords: 
                    st = st.isel(depth=0)
                t_now = round(float(st["thetao"].values.flatten()[0]), 1)
                
                # Courants
                sc = ds_cur.sel(
                    latitude=coords["lat"], 
                    longitude=coords["lon"], 
                    time=now, 
                    method="nearest"
                )
                if 'depth' in sc.coords: 
                    sc = sc.isel(depth=0)
                u = float(sc["uo"].values.flatten()[0])
                v = float(sc["vo"].values.flatten()[0])
                c_now = round(float(np.sqrt(u**2 + v**2)), 2)
                
                # Vagues
                sw = ds_wav.sel(
                    latitude=coords["lat"], 
                    longitude=coords["lon"], 
                    time=now, 
                    method="nearest"
                )
                v_now = round(float(sw["VHM0"].values.flatten()[0]), 2)
                
                # === PRÉVISIONS 24H ===
                forecast = []
                try:
                    times = ds_wav.sel(
                        latitude=coords["lat"], 
                        longitude=coords["lon"],
                        time=slice(now, next_24h),
                        method="nearest"
                    )
                    
                    # Prendre 8 points (toutes les 3h sur 24h)
                    time_points = times.time.values[:8]
                    
                    for t in time_points:
                        sw_f = ds_wav.sel(
                            latitude=coords["lat"],
                            longitude=coords["lon"],
                            time=t,
                            method="nearest"
                        )
                        
                        v_forecast = round(float(sw_f["VHM0"].values.flatten()[0]), 2)
                        time_str = pd.to_datetime(t).strftime("%H:%M")
                        
                        forecast.append({
                            "time": time_str,
                            "wave": v_forecast
                        })
                    
                    logger.log(f"  Prévisions: {len(forecast)} points récupérés")
                    
                except Exception as e:
                    logger.log(f"  Prévisions non disponibles pour {name}: {str(e)}", "WARNING")
                    forecast = []
                
                # === CALCULS ===
                
                # Niveau de sécurité
                safety, safety_level, color = calculate_safety_level(v_now, c_now)
                
                # Index de pêche
                fish, fish_level = calculate_fish_index(t_now, c_now, v_now)
                
                # Recommandations
                recommendations = []
                if safety_level == "danger":
                    recommendations.append("⚠️ NE PAS SORTIR EN MER")
                elif safety_level == "warning":
                    recommendations.append("⚠️ Sortie déconseillée - Prudence extrême")
                elif safety_level == "caution":
                    recommendations.append("⚠️ Vigilance accrue recommandée")
                
                if fish_level == "excellent":
                    recommendations.append("🎣 Conditions optimales pour la pêche")
                elif fish_level == "good":
                    recommendations.append("🎣 Bonnes conditions de pêche")
                
                results.append({
                    "zone": name,
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "v_now": v_now,
                    "t_now": t_now,
                    "c_now": c_now,
                    "index": fish,
                    "fish_level": fish_level,
                    "safety": safety,
                    "safety_level": safety_level,
                    "color": color,
                    "date": now.strftime("%d/%m %H:%M"),
                    "timestamp": now.isoformat(),
                    "forecast": forecast,
                    "recommendations": recommendations
                })
                
                logger.log(f"  ✅ {name}: {safety} | Vagues {v_now}m | Pêche {fish}")
                
            except Exception as e:
                logger.log(f"Erreur pour {name}: {str(e)}", "ERROR")
                errors += 1
                continue
        
        logger.log(f"Traitement terminé: {len(results)}/{len(ZONES)} zones")
        return results, errors
        
    except Exception as e:
        logger.log(f"Erreur critique: {str(e)}", "ERROR")
        return None, len(ZONES)

def send_telegram_alert(data):
    """Envoie une alerte Telegram avec formatage amélioré"""
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    
    if not token or not chat_id:
        logger.log("Identifiants Telegram manquants, notification ignorée", "WARNING")
        return
    
    # Analyse de la situation
    danger_zones = [z for z in data if z['safety_level'] == "danger"]
    warning_zones = [z for z in data if z['safety_level'] == "warning"]
    caution_zones = [z for z in data if z['safety_level'] == "caution"]
    safe_zones = [z for z in data if z['safety_level'] == "safe"]
    
    # Construction du message
    if danger_zones:
        message = "🚨 *ALERTE DANGER - PECHEURCONNECT* 🚨\n\n"
        message += f"⛔ {len(danger_zones)} zone(s) DANGEREUSE(S)\n"
        message += f"⚠️ NE PAS SORTIR EN MER\n\n"
    elif warning_zones:
        message = "⚠️ *ALERTE PRUDENCE - PECHEURCONNECT*\n\n"
        message += f"🟠 {len(warning_zones)} zone(s) nécessitent PRUDENCE\n\n"
    else:
        message = "🌊 *PECHEURCONNECT - RAPPORT QUOTIDIEN*\n\n"
    
    # Résumé global
    message += f"📊 *Résumé:* {len(safe_zones)}✅ {len(caution_zones)}🟡 {len(warning_zones)}🟠 {len(danger_zones)}🔴\n\n"
    
    # Détails par zone
    for z in data:
        message += f"━━━━━━━━━━━━━━━\n"
        message += f"📍 *{z['zone']}*\n"
        message += f"{z['safety']} | Pêche: {z['index']}\n"
        message += f"🌊 Vagues: {z['v_now']}m\n"
        message += f"🌡️ Temp: {z['t_now']}°C\n"
        message += f"🧭 Courant: {z['c_now']}m/s\n"
        
        # Prévisions
        if z.get('forecast') and len(z['forecast']) > 0:
            next_vals = z['forecast'][:3]
            forecast_str = " → ".join([f"{f['wave']}m" for f in next_vals])
            message += f"📈 Prévisions: {forecast_str}\n"
        
        message += "\n"
    
    message += f"🕐 Mise à jour: {data[0]['date']} UTC\n"
    message += f"🌐 pecheurconnect.sn"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }, timeout=10)
        
        if response.status_code == 200:
            logger.log("Alerte Telegram envoyée avec succès")
        else:
            logger.log(f"Erreur Telegram: {response.status_code} - {response.text}", "ERROR")
            
    except Exception as e:
        logger.log(f"Erreur envoi Telegram: {str(e)}", "ERROR")

def save_data(data):
    """Sauvegarde les données en JSON avec backup"""
    try:
        # Sauvegarder les données actuelles
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.log(f"data.json sauvegardé ({len(data)} zones)")
        
        # Créer un backup horodaté
        backup_dir = Path("logs/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"data_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Garder seulement les 30 derniers backups
        backups = sorted(backup_dir.glob("data_*.json"))
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                old_backup.unlink()
        
        return True
        
    except Exception as e:
        logger.log(f"Erreur sauvegarde: {str(e)}", "ERROR")
        return False

def generate_statistics(data):
    """Génère des statistiques sur les données"""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "total_zones": len(data),
        "safety_breakdown": {
            "safe": len([z for z in data if z['safety_level'] == "safe"]),
            "caution": len([z for z in data if z['safety_level'] == "caution"]),
            "warning": len([z for z in data if z['safety_level'] == "warning"]),
            "danger": len([z for z in data if z['safety_level'] == "danger"])
        },
        "fish_breakdown": {
            "excellent": len([z for z in data if z['fish_level'] == "excellent"]),
            "good": len([z for z in data if z['fish_level'] == "good"]),
            "moderate": len([z for z in data if z['fish_level'] == "moderate"]),
            "poor": len([z for z in data if z['fish_level'] == "poor"])
        },
        "average_wave": round(np.mean([z['v_now'] for z in data]), 2),
        "max_wave": max([z['v_now'] for z in data]),
        "average_temp": round(np.mean([z['t_now'] for z in data]), 1),
        "average_current": round(np.mean([z['c_now'] for z in data]), 2)
    }
    
    # Sauvegarder les stats
    stats_file = Path("logs/statistics.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    logger.log(f"Statistiques: {stats['safety_breakdown']['danger']} danger(s), {stats['safety_breakdown']['safe']} sûr(s)")
    
    return stats

def main():
    """Point d'entrée principal"""
    logger.log("=" * 60)
    logger.log("🌊 PECHEURCONNECT - Début de la collecte")
    logger.log("=" * 60)
    
    start_time = datetime.now()
    
    # Récupération des données
    data, errors = asyncio.run(fetch_marine_data())
    
    if not data or len(data) == 0:
        logger.log("Aucune donnée collectée - Arrêt", "ERROR")
        logger.log_execution(False, 0, errors)
        exit(1)
    
    # Sauvegarde
    if not save_data(data):
        logger.log("Échec de la sauvegarde", "ERROR")
        logger.log_execution(False, len(data), errors)
        exit(1)
    
    # Statistiques
    stats = generate_statistics(data)
    
    # Notification Telegram
    send_telegram_alert(data)
    
    # Durée d'exécution
    duration = (datetime.now() - start_time).total_seconds()
    logger.log(f"Durée d'exécution: {duration:.2f}s")
    
    # Log d'exécution
    logger.log_execution(True, len(data), errors)
    
    logger.log("=" * 60)
    logger.log("✅ Mise à jour terminée avec succès")
    logger.log("=" * 60)

if __name__ == "__main__":
    main()
