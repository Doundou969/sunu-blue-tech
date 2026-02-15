#!/usr/bin/env python3
"""
PecheurConnect - Système de Sécurité Maritime pour le Sénégal
Collecte automatique des données océanographiques depuis Copernicus Marine
"""

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

# ============================================================================
# CONFIGURATION
# ============================================================================

# Variables d'environnement
COPERNICUS_USER = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

# Zones de pêche au Sénégal
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65, "desc": "Ndar - Nord"},
    "KAYAR": {"lat": 14.95, "lon": -17.35, "desc": "Kayar - Centre-Nord"},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65, "desc": "Dakar - Capitale"},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15, "desc": "Petite Côte"},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95, "desc": "Ziguinchor - Sud"}
}

# Seuils de sécurité
THRESHOLDS = {
    "DANGER": {"wave": 3.0, "current": 1.0},
    "WARNING": {"wave": 2.1, "current": 0.6},
    "CAUTION": {"wave": 1.5, "current": 0.4}
}

# Datasets Copernicus Marine
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
    emoji = {
        "ERROR": "❌",
        "WARNING": "⚠️",
        "SUCCESS": "✅",
        "INFO": "ℹ️"
    }
    print(f"[{timestamp}] {emoji.get(level, 'ℹ️')} {msg}")


def calculate_safety_level(wave, current):
    """Calcule le niveau de sécurité maritime"""
    if wave > THRESHOLDS["DANGER"]["wave"] or current > THRESHOLDS["DANGER"]["current"]:
        return "🔴 DANGER", "danger", "#d32f2f"
    elif wave > THRESHOLDS["WARNING"]["wave"] or current > THRESHOLDS["WARNING"]["current"]:
        return "🟠 PRUDENCE", "warning", "#ff9800"
    elif wave > THRESHOLDS["CAUTION"]["wave"] or current > THRESHOLDS["CAUTION"]["current"]:
        return "🟡 VIGILANCE", "caution", "#ffc107"
    else:
        return "🟢 SÛR", "safe", "#28a745"


def calculate_fish_index(temp, current, wave):
    """Calcule l'indice de pêche selon conditions océanographiques"""
    score = 0
    factors = []
    
    # Température optimale (18-24°C)
    if 18 <= temp <= 24:
        score += 3
        factors.append("🌡️ Température idéale")
    elif 15 <= temp <= 27:
        score += 1
        factors.append("🌡️ Température acceptable")
    else:
        factors.append("🌡️ Température non optimale")
    
    # Courants modérés (0.2-0.5 m/s)
    if 0.2 <= current <= 0.5:
        score += 2
        factors.append("🧭 Courants favorables")
    elif current < 0.2:
        score += 1
        factors.append("🧭 Courants faibles")
    else:
        factors.append("🧭 Courants forts")
    
    # Mer calme (< 2m)
    if wave < 1.0:
        score += 3
        factors.append("🌊 Mer très calme")
    elif wave < 1.5:
        score += 2
        factors.append("🌊 Mer calme")
    elif wave < 2.0:
        score += 1
        factors.append("🌊 Mer modérée")
    else:
        factors.append("🌊 Mer agitée")
    
    # Déterminer le niveau
    if score >= 7:
        return "🐟🐟🐟 EXCELLENT", "excellent", factors
    elif score >= 5:
        return "🐟🐟 BON", "good", factors
    elif score >= 3:
        return "🐟 MOYEN", "moderate", factors
    else:
        return "🎣 FAIBLE", "poor", factors


def generate_recommendations(safety_level, fish_level, wave, current, temp):
    """Génère des recommandations intelligentes pour les pêcheurs"""
    recommendations = []
    
    # Recommandations de sécurité
    if safety_level == "danger":
        recommendations.extend([
            "⛔ NE PAS SORTIR EN MER",
            "🏠 Restez à quai - Conditions dangereuses",
            "📻 Surveillez les bulletins météo"
        ])
    elif safety_level == "warning":
        recommendations.extend([
            "⚠️ Sortie fortement déconseillée",
            "📱 Si sortie nécessaire, restez près des côtes",
            "🦺 Équipement de sécurité OBLIGATOIRE",
            "👥 Ne partez JAMAIS seul"
        ])
    elif safety_level == "caution":
        recommendations.extend([
            "⚠️ Vigilance accrue recommandée",
            "👥 Privilégiez les sorties en groupe",
            "📱 Gardez le contact avec la côte"
        ])
    else:
        recommendations.append("✅ Conditions sûres pour la navigation")
    
    # Recommandations de pêche
    if fish_level == "excellent":
        recommendations.extend([
            "🎣 Conditions OPTIMALES pour la pêche",
            "🐟 Forte probabilité de bonnes prises"
        ])
    elif fish_level == "good":
        recommendations.extend([
            "🎣 Bonnes conditions de pêche",
            "🐟 Activité des poissons favorable"
        ])
    elif fish_level == "moderate":
        recommendations.append("🎣 Pêche possible - Conditions moyennes")
    else:
        recommendations.append("🎣 Conditions peu favorables")
    
    # Recommandations spécifiques
    if wave > 2.5:
        recommendations.append("🌊 Vagues importantes - Risque de chavirement")
    if current > 0.7:
        recommendations.append("🧭 Courants forts - Attention à la dérive")
    if temp < 18:
        recommendations.append("❄️ Eau froide - Poissons en profondeur")
    elif temp > 26:
        recommendations.append("🌡️ Eau chaude - Poissons près de la surface")
    
    return recommendations


def extract_valid_data(data_array):
    """Extrait les données valides (non-NaN) d'un array numpy"""
    if data_array is None or len(data_array) == 0:
        return None
    
    valid_data = data_array[~np.isnan(data_array)]
    if len(valid_data) > 0:
        return float(np.mean(valid_data))
    return None


# ============================================================================
# RÉCUPÉRATION DES DONNÉES MARINES
# ============================================================================

def fetch_data():
    """Récupère les données océanographiques depuis Copernicus Marine"""
    log("🔐 Connexion à Copernicus Marine Service...")
    
    if not COPERNICUS_USER or not COPERNICUS_PASS:
        log("Identifiants Copernicus manquants", "ERROR")
        return None
    
    try:
        # Connexion
        cm.login(username=COPERNICUS_USER, password=COPERNICUS_PASS)
        log("Connexion réussie", "SUCCESS")
        
        log("📡 Chargement des datasets...")
        now = datetime.utcnow()
        results = []
        errors = 0
        
        for name, coords in ZONES.items():
            try:
                log(f"Traitement de {name}...")
                
                # ============================================
                # TEMPÉRATURE DE SURFACE
                # ============================================
                temp = 22.0  # Valeur par défaut
                try:
                    temp_data = cm.subset(
                        dataset_id=DATASETS["temperature"],
                        variables=["thetao"],
                        minimum_longitude=coords["lon"] - 0.05,
                        maximum_longitude=coords["lon"] + 0.05,
                        minimum_latitude=coords["lat"] - 0.05,
                        maximum_latitude=coords["lat"] + 0.05,
                        minimum_depth=0,
                        maximum_depth=1,
                        start_datetime=now - timedelta(hours=6),
                        end_datetime=now,
                        username=COPERNICUS_USER,
                        password=COPERNICUS_PASS
                    )
                    
                    if temp_data and 'thetao' in temp_data.variables:
                        temp_values = temp_data['thetao'].values
                        temp_result = extract_valid_data(temp_values)
                        if temp_result:
                            temp = round(temp_result, 1)
                except Exception as e:
                    log(f"  Température par défaut: {str(e)[:40]}", "WARNING")
                
                # ============================================
                # COURANTS MARINS
                # ============================================
                current = 0.3  # Valeur par défaut
                current_direction = 0.0
                try:
                    current_data = cm.subset(
                        dataset_id=DATASETS["current"],
                        variables=["uo", "vo"],
                        minimum_longitude=coords["lon"] - 0.05,
                        maximum_longitude=coords["lon"] + 0.05,
                        minimum_latitude=coords["lat"] - 0.05,
                        maximum_latitude=coords["lat"] + 0.05,
                        minimum_depth=0,
                        maximum_depth=1,
                        start_datetime=now - timedelta(hours=6),
                        end_datetime=now,
                        username=COPERNICUS_USER,
                        password=COPERNICUS_PASS
                    )
                    
                    if current_data and 'uo' in current_data.variables and 'vo' in current_data.variables:
                        u_values = current_data['uo'].values
                        v_values = current_data['vo'].values
                        
                        u = extract_valid_data(u_values)
                        v = extract_valid_data(v_values)
                        
                        if u is not None and v is not None:
                            current = round(float(np.sqrt(u**2 + v**2)), 2)
                            current_direction = round(float(np.degrees(np.arctan2(v, u))), 1)
                except Exception as e:
                    log(f"  Courant par défaut: {str(e)[:40]}", "WARNING")
                
                # ============================================
                # VAGUES
                # ============================================
                wave = 1.5  # Valeur par défaut
                try:
                    wave_data = cm.subset(
                        dataset_id=DATASETS["waves"],
                        variables=["VHM0"],
                        minimum_longitude=coords["lon"] - 0.05,
                        maximum_longitude=coords["lon"] + 0.05,
                        minimum_latitude=coords["lat"] - 0.05,
                        maximum_latitude=coords["lat"] + 0.05,
                        start_datetime=now - timedelta(hours=3),
                        end_datetime=now,
                        username=COPERNICUS_USER,
                        password=COPERNICUS_PASS
                    )
                    
                    if wave_data and 'VHM0' in wave_data.variables:
                        wave_values = wave_data['VHM0'].values
                        wave_result = extract_valid_data(wave_values)
                        if wave_result:
                            wave = round(wave_result, 2)
                except Exception as e:
                    log(f"  Vagues par défaut: {str(e)[:40]}", "WARNING")
                
                # ============================================
                # PRÉVISIONS 24H
                # ============================================
                forecast = []
                try:
                    forecast_data = cm.subset(
                        dataset_id=DATASETS["waves"],
                        variables=["VHM0"],
                        minimum_longitude=coords["lon"] - 0.05,
                        maximum_longitude=coords["lon"] + 0.05,
                        minimum_latitude=coords["lat"] - 0.05,
                        maximum_latitude=coords["lat"] + 0.05,
                        start_datetime=now,
                        end_datetime=now + timedelta(hours=24),
                        username=COPERNICUS_USER,
                        password=COPERNICUS_PASS
                    )
                    
                    if forecast_data and 'VHM0' in forecast_data.variables and 'time' in forecast_data.variables:
                        times = forecast_data['time'].values[:8]
                        waves = forecast_data['VHM0'].values[:8]
                        
                        for i, t in enumerate(times):
                            if i < len(waves):
                                wave_vals = waves[i]
                                forecast_wave = extract_valid_data(wave_vals)
                                if forecast_wave:
                                    forecast.append({
                                        "time": pd.to_datetime(t).strftime("%H:%M"),
                                        "wave": round(forecast_wave, 2),
                                        "timestamp": pd.to_datetime(t).isoformat()
                                    })
                except Exception as e:
                    log(f"  Prévisions indisponibles: {str(e)[:40]}", "WARNING")
                
                # ============================================
                # CALCULS ET ANALYSES
                # ============================================
                
                # Niveau de sécurité
                safety, safety_level, color = calculate_safety_level(wave, current)
                
                # Indice de pêche
                fish, fish_level, fish_factors = calculate_fish_index(temp, current, wave)
                
                # Recommandations
                recommendations = generate_recommendations(
                    safety_level, fish_level, wave, current, temp
                )
                
                # Score de danger (0-100)
                danger_score = min(100, int(
                    (wave / 4.0) * 40 +
                    (current / 1.5) * 30 +
                    ((30 - temp) / 15 if temp < 30 else 0) * 30
                ))
                
                # ============================================
                # CONSTRUCTION DU RÉSULTAT
                # ============================================
                results.append({
                    "zone": name,
                    "description": coords["desc"],
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "v_now": wave,
                    "t_now": temp,
                    "c_now": current,
                    "current_direction": current_direction,
                    "index": fish,
                    "fish_level": fish_level,
                    "fish_factors": fish_factors,
                    "safety": safety,
                    "safety_level": safety_level,
                    "color": color,
                    "danger_score": danger_score,
                    "date": now.strftime("%d/%m %H:%M"),
                    "timestamp": now.isoformat(),
                    "forecast": forecast,
                    "recommendations": recommendations
                })
                
                log(f"  {safety} | 🌊{wave}m | 🌡️{temp}°C | 🐟{fish}", "SUCCESS")
                
            except Exception as e:
                log(f"  Erreur complète zone {name}: {str(e)}", "ERROR")
                errors += 1
                continue
        
        if len(results) == 0:
            log("Aucune donnée collectée", "ERROR")
            return None
        
        log(f"Collecte terminée: {len(results)}/{len(ZONES)} zones | {errors} erreur(s)", "SUCCESS")
        return results
        
    except Exception as e:
        log(f"Erreur critique: {str(e)}", "ERROR")
        return None


# ============================================================================
# SAUVEGARDE ET NOTIFICATIONS
# ============================================================================

def save_data(data):
    """Sauvegarde les données JSON avec backup"""
    try:
        # Créer le dossier logs
        Path("logs").mkdir(exist_ok=True)
        Path("logs/backups").mkdir(exist_ok=True)
        
        # Sauvegarder data.json
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log(f"data.json sauvegardé ({len(data)} zones)", "SUCCESS")
        
        # Backup horodaté
        backup_file = Path("logs/backups") / f"data_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Nettoyer anciens backups (garder 30 derniers)
        backups = sorted(Path("logs/backups").glob("data_*.json"))
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                old_backup.unlink()
        
        log(f"Backup: {backup_file.name}", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"Erreur sauvegarde: {str(e)}", "ERROR")
        return False


def generate_statistics(data):
    """Génère des statistiques sur les données collectées"""
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
        "averages": {
            "wave_height": round(np.mean([z['v_now'] for z in data]), 2),
            "temperature": round(np.mean([z['t_now'] for z in data]), 1),
            "current_speed": round(np.mean([z['c_now'] for z in data]), 2),
            "danger_score": round(np.mean([z['danger_score'] for z in data]), 1)
        },
        "extremes": {
            "max_wave": {
                "value": max([z['v_now'] for z in data]),
                "zone": [z['zone'] for z in data if z['v_now'] == max([z['v_now'] for z in data])][0]
            },
            "min_temp": {
                "value": min([z['t_now'] for z in data]),
                "zone": [z['zone'] for z in data if z['t_now'] == min([z['t_now'] for z in data])][0]
            },
            "max_current": {
                "value": max([z['c_now'] for z in data]),
                "zone": [z['zone'] for z in data if z['c_now'] == max([z['c_now'] for z in data])][0]
            }
        }
    }
    
    # Sauvegarder les statistiques
    stats_file = Path("logs/statistics.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # Afficher résumé
    log("📊 Statistiques:", "INFO")
    log(f"  Sécurité: {stats['safety_breakdown']['safe']}✅ {stats['safety_breakdown']['caution']}🟡 {stats['safety_breakdown']['warning']}🟠 {stats['safety_breakdown']['danger']}🔴", "INFO")
    log(f"  Pêche: {stats['fish_breakdown']['excellent']}🐟🐟🐟 {stats['fish_breakdown']['good']}🐟🐟 {stats['fish_breakdown']['moderate']}🐟", "INFO")
    log(f"  Moyennes: Vagues {stats['averages']['wave_height']}m | Temp {stats['averages']['temperature']}°C", "INFO")
    
    return stats


def send_telegram(data):
    """Envoie une alerte Telegram formatée"""
    if not TG_TOKEN or not TG_ID:
        log("Telegram non configuré", "WARNING")
        return
    
    # Analyser la situation
    danger_zones = [z for z in data if z['safety_level'] == "danger"]
    warning_zones = [z for z in data if z['safety_level'] == "warning"]
    caution_zones = [z for z in data if z['safety_level'] == "caution"]
    safe_zones = [z for z in data if z['safety_level'] == "safe"]
    
    # Construction du message
    if danger_zones:
        message = "🚨 *ALERTE DANGER - PECHEURCONNECT* 🚨\n\n"
        message += f"⛔ {len(danger_zones)} zone(s) DANGEREUSE(S)\n"
        message += "⚠️ NE PAS SORTIR EN MER\n\n"
    elif warning_zones:
        message = "⚠️ *ALERTE PRUDENCE - PECHEURCONNECT*\n\n"
        message += f"🟠 {len(warning_zones)} zone(s) nécessitent PRUDENCE\n\n"
    else:
        message = "🌊 *PECHEURCONNECT - RAPPORT QUOTIDIEN*\n\n"
    
    # Résumé global
    message += f"📊 *Résumé:* {len(safe_zones)}✅ {len(caution_zones)}🟡 {len(warning_zones)}🟠 {len(danger_zones)}🔴\n\n"
    
    # Zones prioritaires (danger + warning + caution)
    priority_zones = danger_zones + warning_zones + caution_zones
    if priority_zones:
        message += "⚠️ *ZONES À SURVEILLER*\n\n"
        for z in priority_zones:
            message += f"━━━━━━━━━━━━━━━\n"
            message += f"📍 *{z['zone']}* ({z['description']})\n"
            message += f"{z['safety']} | Pêche: {z['index']}\n"
            message += f"🌊 {z['v_now']}m | 🌡️ {z['t_now']}°C | 🧭 {z['c_now']}m/s\n"
            
            # Prévision tendance
            if z.get('forecast') and len(z['forecast']) >= 2:
                next_wave = z['forecast'][1]['wave']
                trend = "↗️" if next_wave > z['v_now'] else "↘️"
                message += f"📈 Tendance: {trend} {next_wave}m à {z['forecast'][1]['time']}\n"
            
            # Recommandation principale
            if z.get('recommendations'):
                message += f"💡 {z['recommendations'][0]}\n"
            
            message += "\n"
    
    # Zones sûres (résumé compact)
    if safe_zones:
        message += f"✅ *ZONES SÛRES* ({len(safe_zones)})\n"
        for z in safe_zones:
            message += f"• {z['zone']}: 🌊{z['v_now']}m | 🐟{z['index'].split()[0]}\n"
        message += "\n"
    
    # Footer
    message += f"🕐 Mise à jour: {data[0]['date']} UTC\n"
    message += "🌐 https://doundou969.github.io/sunu-blue-tech/\n"
    message += "\n_PecheurConnect - Sécurité Maritime 🇸🇳_"
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={
                "chat_id": TG_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            },
            timeout=10
        )
        
        if response.status_code == 200:
            log("Alerte Telegram envoyée", "SUCCESS")
        else:
            log(f"Erreur Telegram: {response.status_code}", "ERROR")
            
    except Exception as e:
        log(f"Erreur Telegram: {str(e)}", "ERROR")


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main():
    """Point d'entrée principal du script"""
    start_time = datetime.now()
    
    # Banner
    log("=" * 60, "INFO")
    log("🇸🇳 PECHEURCONNECT - Système de Sécurité Maritime", "INFO")
    log(f"Démarré le {start_time.strftime('%d/%m/%Y à %H:%M:%S UTC')}", "INFO")
    log("=" * 60, "INFO")
    
    # Récupération des données
    data = fetch_data()
    
    if not data:
        log("Échec de la collecte de données", "ERROR")
        exit(1)
    
    # Sauvegarde
    if not save_data(data):
        log("Échec de la sauvegarde", "ERROR")
        exit(1)
    
    # Statistiques
    stats = generate_statistics(data)
    
    # Notification Telegram
    log("📱 Envoi de l'alerte Telegram...", "INFO")
    send_telegram(data)
    
    # Durée d'exécution
    duration = (datetime.now() - start_time).total_seconds()
    
    # Résumé final
    log("=" * 60, "INFO")
    log(f"✅ Mise à jour terminée avec succès", "SUCCESS")
    log(f"Durée: {duration:.2f}s | Zones: {len(data)}/{len(ZONES)}", "INFO")
    log("=" * 60, "INFO")


# ============================================================================
# EXÉCUTION
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nScript interrompu par l'utilisateur", "WARNING")
        exit(0)
    except Exception as e:
        log(f"\nErreur fatale: {str(e)}", "ERROR")
        exit(1)
