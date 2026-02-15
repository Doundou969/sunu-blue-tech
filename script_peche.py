#!/usr/bin/env python3
"""
PecheurConnect - Version avec debug et approche alternative
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

# Configuration
COPERNICUS_USER = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65, "desc": "Ndar - Nord"},
    "KAYAR": {"lat": 14.95, "lon": -17.35, "desc": "Kayar - Centre-Nord"},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65, "desc": "Dakar - Capitale"},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15, "desc": "Petite Côte"},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95, "desc": "Ziguinchor - Sud"}
}

DATASETS = {
    "temperature": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
    "current": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
    "waves": "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
}

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    emoji = {"ERROR": "❌", "WARNING": "⚠️", "SUCCESS": "✅", "INFO": "ℹ️", "DEBUG": "🔍"}
    print(f"[{timestamp}] {emoji.get(level, 'ℹ️')} {msg}")


def calculate_safety_level(wave, current):
    if wave > 3.0 or current > 1.0:
        return "🔴 DANGER", "danger", "#d32f2f"
    elif wave > 2.1 or current > 0.6:
        return "🟠 PRUDENCE", "warning", "#ff9800"
    elif wave > 1.5 or current > 0.4:
        return "🟡 VIGILANCE", "caution", "#ffc107"
    else:
        return "🟢 SÛR", "safe", "#28a745"


def calculate_fish_index(temp, current, wave):
    score = 0
    factors = []
    
    if 18 <= temp <= 24:
        score += 3
        factors.append("🌡️ Température idéale")
    elif 15 <= temp <= 27:
        score += 1
        factors.append("🌡️ Température acceptable")
    
    if 0.2 <= current <= 0.5:
        score += 2
        factors.append("🧭 Courants favorables")
    elif current < 0.2:
        score += 1
        factors.append("🧭 Courants faibles")
    
    if wave < 1.0:
        score += 3
        factors.append("🌊 Mer très calme")
    elif wave < 1.5:
        score += 2
        factors.append("🌊 Mer calme")
    elif wave < 2.0:
        score += 1
        factors.append("🌊 Mer modérée")
    
    if score >= 7:
        return "🐟🐟🐟 EXCELLENT", "excellent", factors
    elif score >= 5:
        return "🐟🐟 BON", "good", factors
    elif score >= 3:
        return "🐟 MOYEN", "moderate", factors
    else:
        return "🎣 FAIBLE", "poor", factors


def generate_recommendations(safety_level, fish_level, wave, current, temp):
    recommendations = []
    
    if safety_level == "danger":
        recommendations.extend([
            "⛔ NE PAS SORTIR EN MER",
            "🏠 Restez à quai - Conditions dangereuses"
        ])
    elif safety_level == "warning":
        recommendations.extend([
            "⚠️ Sortie fortement déconseillée",
            "📱 Si nécessaire, restez près des côtes"
        ])
    elif safety_level == "caution":
        recommendations.extend([
            "⚠️ Vigilance accrue recommandée",
            "👥 Sortie en groupe privilégiée"
        ])
    else:
        recommendations.append("✅ Conditions sûres pour la navigation")
    
    if fish_level == "excellent":
        recommendations.append("🎣 Conditions OPTIMALES pour la pêche")
    elif fish_level == "good":
        recommendations.append("🎣 Bonnes conditions de pêche")
    elif fish_level == "moderate":
        recommendations.append("🎣 Pêche possible - Conditions moyennes")
    
    return recommendations


def fetch_zone_data_alternative(name, coords, now):
    """
    Méthode alternative : utiliser read_dataframe au lieu de subset
    """
    log(f"🔍 Tentative alternative pour {name}...", "DEBUG")
    
    try:
        # Essayer avec read_dataframe pour les vagues
        wave = None
        try:
            log(f"  Téléchargement vagues {name}...", "DEBUG")
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
                    log(f"  ✅ Vagues: {wave}m (read_dataframe)", "DEBUG")
        except Exception as e:
            log(f"  ⚠️ Erreur vagues read_dataframe: {str(e)[:50]}", "WARNING")
        
        # Température
        temp = None
        try:
            log(f"  Téléchargement température {name}...", "DEBUG")
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
                    log(f"  ✅ Température: {temp}°C (read_dataframe)", "DEBUG")
        except Exception as e:
            log(f"  ⚠️ Erreur température read_dataframe: {str(e)[:50]}", "WARNING")
        
        # Courants
        current = None
        try:
            log(f"  Téléchargement courants {name}...", "DEBUG")
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
                    log(f"  ✅ Courant: {current}m/s (read_dataframe)", "DEBUG")
        except Exception as e:
            log(f"  ⚠️ Erreur courants read_dataframe: {str(e)[:50]}", "WARNING")
        
        return wave, temp, current
        
    except Exception as e:
        log(f"  ❌ Erreur totale alternative {name}: {str(e)}", "ERROR")
        return None, None, None


def fetch_data():
    log("🔐 Connexion à Copernicus Marine Service...")
    
    if not COPERNICUS_USER or not COPERNICUS_PASS:
        log("Identifiants Copernicus manquants", "ERROR")
        return None
    
    try:
        cm.login(username=COPERNICUS_USER, password=COPERNICUS_PASS)
        log("Connexion réussie", "SUCCESS")
        
        log("📡 Collecte des données avec méthode alternative...")
        now = datetime.utcnow()
        results = []
        
        for name, coords in ZONES.items():
            try:
                log(f"📍 {name} ({coords['lat']}, {coords['lon']})...")
                
                # Utiliser la méthode alternative
                wave, temp, current = fetch_zone_data_alternative(name, coords, now)
                
                # Valeurs par défaut SI et SEULEMENT SI échec total
                if wave is None:
                    wave = 1.5
                    log(f"  ⚠️ Vagues par défaut: {wave}m", "WARNING")
                
                if temp is None:
                    temp = 22.0
                    log(f"  ⚠️ Température par défaut: {temp}°C", "WARNING")
                
                if current is None:
                    current = 0.3
                    log(f"  ⚠️ Courant par défaut: {current}m/s", "WARNING")
                
                # Vérifier si toutes les valeurs sont par défaut
                if wave == 1.5 and temp == 22.0 and current == 0.3:
                    log(f"  🚨 ATTENTION: {name} utilise TOUTES les valeurs par défaut!", "WARNING")
                
                # Prévisions (simplifié)
                forecast = []
                
                # Calculs
                safety, safety_level, color = calculate_safety_level(wave, current)
                fish, fish_level, fish_factors = calculate_fish_index(temp, current, wave)
                recommendations = generate_recommendations(safety_level, fish_level, wave, current, temp)
                
                danger_score = min(100, int(
                    (wave / 4.0) * 40 +
                    (current / 1.5) * 30 +
                    ((30 - temp) / 15 if temp < 30 else 0) * 30
                ))
                
                results.append({
                    "zone": name,
                    "description": coords["desc"],
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "v_now": wave,
                    "t_now": temp,
                    "c_now": current,
                    "current_direction": 0.0,
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
                    "recommendations": recommendations,
                    "data_source": "real" if (wave != 1.5 or temp != 22.0 or current != 0.3) else "default"
                })
                
                log(f"  {safety} | 🌊{wave}m | 🌡️{temp}°C | 🐟{fish}", "SUCCESS")
                
            except Exception as e:
                log(f"Erreur zone {name}: {str(e)}", "ERROR")
                continue
        
        if len(results) == 0:
            log("Aucune donnée collectée", "ERROR")
            return None
        
        # Statistiques sur les sources de données
        real_data = len([r for r in results if r.get("data_source") == "real"])
        default_data = len([r for r in results if r.get("data_source") == "default"])
        
        log(f"📊 Sources: {real_data} réelles | {default_data} par défaut", "INFO")
        
        if default_data == len(results):
            log("🚨 ALERTE: TOUTES les zones utilisent des données par défaut!", "WARNING")
        
        return results
        
    except Exception as e:
        log(f"Erreur critique: {str(e)}", "ERROR")
        return None


def save_data(data):
    try:
        Path("logs").mkdir(exist_ok=True)
        Path("logs/backups").mkdir(exist_ok=True)
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log(f"data.json sauvegardé ({len(data)} zones)", "SUCCESS")
        
        backup_file = Path("logs/backups") / f"data_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        backups = sorted(Path("logs/backups").glob("data_*.json"))
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                old_backup.unlink()
        
        return True
        
    except Exception as e:
        log(f"Erreur sauvegarde: {str(e)}", "ERROR")
        return False


def send_telegram(data):
    if not TG_TOKEN or not TG_ID:
        log("Telegram non configuré", "WARNING")
        return
    
    # Vérifier si données par défaut
    default_count = len([z for z in data if z.get("data_source") == "default"])
    
    message = "🌊 *PECHEURCONNECT - RAPPORT*\n\n"
    
    if default_count == len(data):
        message += "⚠️ _Données Copernicus indisponibles_\n"
        message += "_Valeurs estimées affichées_\n\n"
    
    for z in data:
        source_emoji = "📡" if z.get("data_source") == "real" else "📊"
        message += f"{source_emoji} *{z['zone']}*\n"
        message += f"{z['safety']} | {z['index']}\n"
        message += f"🌊 {z['v_now']}m | 🌡️ {z['t_now']}°C\n\n"
    
    message += f"🕐 {data[0]['date']} UTC"
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
        log("Telegram envoyé", "SUCCESS")
    except Exception as e:
        log(f"Erreur Telegram: {str(e)}", "ERROR")


def main():
    start_time = datetime.now()
    
    log("=" * 60, "INFO")
    log("🇸🇳 PECHEURCONNECT - VERSION DEBUG", "INFO")
    log("=" * 60, "INFO")
    
    data = fetch_data()
    
    if not data:
        log("Échec collecte", "ERROR")
        exit(1)
    
    if not save_data(data):
        log("Échec sauvegarde", "ERROR")
        exit(1)
    
    send_telegram(data)
    
    duration = (datetime.now() - start_time).total_seconds()
    log("=" * 60, "INFO")
    log(f"✅ Terminé en {duration:.2f}s", "SUCCESS")
    log("=" * 60, "INFO")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrompu", "WARNING")
        exit(0)
    except Exception as e:
        log(f"Erreur fatale: {str(e)}", "ERROR")
        exit(1)
```

---

## 🔍 Ce script va :

1. ✅ **Afficher des logs DEBUG détaillés** pour chaque zone
2. ✅ **Utiliser `read_dataframe`** au lieu de `subset`
3. ✅ **Indiquer la source des données** (réelle vs défaut)
4. ✅ **Alerter si toutes les données sont par défaut**

---

## 📊 Dans les logs GitHub Actions, vous verrez :
```
[12:34:56] 📍 SAINT-LOUIS (16.05, -16.65)...
[12:34:57] 🔍 Tentative alternative pour SAINT-LOUIS...
[12:34:58]   Téléchargement vagues SAINT-LOUIS...
[12:35:02]   ✅ Vagues: 2.3m (read_dataframe)
[12:35:03]   Téléchargement température SAINT-LOUIS...
[12:35:07]   ✅ Température: 21.5°C (read_dataframe)
```

Ou si ça échoue :
```
[12:35:10]   ⚠️ Erreur vagues read_dataframe: ...
[12:35:11]   ⚠️ Vagues par défaut: 1.5m
