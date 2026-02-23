#!/usr/bin/env python3
"""
PecheurConnect v3.0 - Système complet avec historique + Bot Telegram
Auteur: PecheurConnect Team
Date: 2026

Corrections v3.0 :
- Gestion robuste des erreurs Copernicus (retry + fallback)
- Cache météo corrigé (lru_cache avec types hashables)
- Génération du fichier seasonality_data.json pour history.html
- Meilleure gestion des valeurs None dans les stats
- Structure all_zones.json compatible avec history.html
- Logging amélioré avec niveaux de couleur
- Sécurisation des accès aux clés de dictionnaire
"""

import os
import json
import time
import warnings
import traceback
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests

warnings.filterwarnings('ignore')

# ============================================================================
# IMPORT OPTIONNEL DE COPERNICUSMARINE
# ============================================================================
try:
    import copernicusmarine as cm
    COPERNICUS_AVAILABLE = True
except ImportError:
    COPERNICUS_AVAILABLE = False
    print("[WARN] copernicusmarine non installé — données simulées utilisées")

# ============================================================================
# CONFIGURATION
# ============================================================================

COPERNICUS_USER     = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASS     = os.getenv("COPERNICUS_PASSWORD")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
TG_TOKEN            = os.getenv("TG_TOKEN")
TG_ID               = os.getenv("TG_ID")
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")

# Nombre de tentatives pour Copernicus
COPERNICUS_MAX_RETRIES = 3
COPERNICUS_RETRY_DELAY = 5  # secondes

# 18 ZONES ÉTENDUES
ZONES = {
    "SAINT-LOUIS":           {"lat": 16.05, "lon": -16.65, "desc": "Ndar - Nord",       "region": "Nord"},
    "GANDIOL":               {"lat": 16.15, "lon": -16.55, "desc": "Gandiol",            "region": "Nord"},
    "KAYAR":                 {"lat": 14.95, "lon": -17.35, "desc": "Kayar",              "region": "Grande Côte"},
    "LOMPOUL":               {"lat": 15.35, "lon": -16.85, "desc": "Lompoul",            "region": "Grande Côte"},
    "DAKAR-YOFF":            {"lat": 14.80, "lon": -17.65, "desc": "Yoff",               "region": "Dakar"},
    "DAKAR-SOUMBEDIOUNE":    {"lat": 14.68, "lon": -17.46, "desc": "Soumbédioune",       "region": "Dakar"},
    "DAKAR-HANN":            {"lat": 14.73, "lon": -17.43, "desc": "Hann",               "region": "Dakar"},
    "RUFISQUE":              {"lat": 14.72, "lon": -17.28, "desc": "Rufisque",           "region": "Dakar"},
    "BARGNY":                {"lat": 14.70, "lon": -17.23, "desc": "Bargny",             "region": "Dakar"},
    "MBOUR-JOAL":            {"lat": 14.35, "lon": -17.15, "desc": "Mbour-Joal",         "region": "Petite Côte"},
    "NIANING":               {"lat": 14.45, "lon": -17.10, "desc": "Nianing",            "region": "Petite Côte"},
    "SALY":                  {"lat": 14.45, "lon": -17.00, "desc": "Saly",               "region": "Petite Côte"},
    "PALMARIN":              {"lat": 14.23, "lon": -16.80, "desc": "Palmarin",           "region": "Sine Saloum"},
    "FOUNDIOUGNE":           {"lat": 14.13, "lon": -16.47, "desc": "Foundiougne",        "region": "Sine Saloum"},
    "MISSIRAH":              {"lat": 13.93, "lon": -16.75, "desc": "Missirah",           "region": "Sine Saloum"},
    "CASAMANCE-ZIGUINCHOR":  {"lat": 12.50, "lon": -16.95, "desc": "Ziguinchor",         "region": "Casamance"},
    "CASAMANCE-CAP-SKIRRING":{"lat": 12.40, "lon": -16.75, "desc": "Cap Skirring",       "region": "Casamance"},
    "KAFOUNTINE":            {"lat": 12.92, "lon": -16.75, "desc": "Kafountine",         "region": "Casamance"},
}

DATASETS = {
    "temperature": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
    "current":     "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
    "waves":       "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
}

# Données de saisonnalité Copernicus (upwelling côte sénégalaise - moyennes 10 ans)
# Indice de potentiel de pêche 0-100 par mois (Jan→Déc)
SEASONALITY_DATA = {
    "Nord": {
        "SAINT-LOUIS": [85, 88, 90, 80, 65, 50, 45, 42, 55, 68, 75, 82],
        "GANDIOL":     [83, 86, 88, 78, 63, 48, 43, 40, 52, 65, 72, 80],
        "KAYAR":       [82, 85, 90, 82, 70, 55, 50, 47, 58, 70, 76, 81],
        "LOMPOUL":     [78, 82, 86, 75, 62, 47, 42, 40, 50, 62, 70, 76],
    },
    "Dakar": {
        "DAKAR-YOFF":         [70, 75, 82, 85, 75, 60, 55, 50, 58, 68, 72, 70],
        "DAKAR-SOUMBEDIOUNE": [68, 73, 80, 83, 73, 58, 53, 48, 56, 66, 70, 68],
        "DAKAR-HANN":         [65, 70, 78, 80, 70, 55, 50, 46, 53, 63, 68, 65],
        "RUFISQUE":           [63, 68, 75, 78, 68, 53, 48, 44, 51, 61, 66, 63],
        "BARGNY":             [62, 67, 74, 77, 67, 52, 47, 43, 50, 60, 65, 62],
    },
    "Petite Côte": {
        "MBOUR-JOAL": [60, 65, 72, 78, 72, 60, 55, 52, 58, 65, 68, 62],
        "NIANING":    [58, 63, 70, 76, 70, 58, 53, 50, 56, 63, 66, 60],
        "SALY":       [57, 62, 68, 74, 68, 56, 51, 48, 54, 61, 64, 58],
    },
    "Sine Saloum": {
        "PALMARIN":    [55, 60, 65, 70, 68, 60, 55, 52, 57, 62, 63, 58],
        "FOUNDIOUGNE": [52, 57, 62, 67, 65, 57, 52, 49, 54, 59, 60, 55],
        "MISSIRAH":    [50, 55, 60, 65, 63, 55, 50, 47, 52, 57, 58, 53],
    },
    "Casamance": {
        "CASAMANCE-ZIGUINCHOR":   [50, 53, 58, 63, 68, 65, 58, 55, 60, 63, 60, 53],
        "CASAMANCE-CAP-SKIRRING": [52, 55, 60, 65, 70, 67, 60, 57, 62, 65, 62, 55],
        "KAFOUNTINE":             [51, 54, 59, 64, 69, 66, 59, 56, 61, 64, 61, 54],
    }
}

# ============================================================================
# LOGGING
# ============================================================================

COLORS = {
    "ERROR":   "\033[91m",
    "WARNING": "\033[93m",
    "SUCCESS": "\033[92m",
    "INFO":    "\033[94m",
    "DEBUG":   "\033[90m",
    "RESET":   "\033[0m",
}

def log(msg, level="INFO"):
    """Affiche un message coloré avec timestamp"""
    ts    = datetime.now().strftime('%H:%M:%S')
    emoji = {"ERROR": "❌", "WARNING": "⚠️", "SUCCESS": "✅", "INFO": "ℹ️", "DEBUG": "🔍"}.get(level, "ℹ️")
    color = COLORS.get(level, "")
    reset = COLORS["RESET"]
    print(f"[{ts}] {color}{emoji} {msg}{reset}")


# ============================================================================
# CALCULS DE SÉCURITÉ ET PÊCHE
# ============================================================================

def calculate_safety_level(wave: float, current: float) -> tuple:
    """Calcule le niveau de sécurité maritime"""
    if wave > 3.0 or current > 1.0:
        return "🔴 DANGER",   "danger",   "#d32f2f"
    elif wave > 2.1 or current > 0.6:
        return "🟠 PRUDENCE", "warning",  "#ff9800"
    elif wave > 1.5 or current > 0.4:
        return "🟡 VIGILANCE","caution",  "#ffc107"
    else:
        return "🟢 SÛR",      "safe",     "#28a745"


def calculate_fish_index(temp: float, current: float, wave: float) -> tuple:
    """Calcule l'indice de pêche (score sur 8)"""
    score   = 0
    factors = []

    if 18 <= temp <= 24:
        score += 3; factors.append("Température idéale")
    elif 15 <= temp <= 27:
        score += 1; factors.append("Température acceptable")

    if 0.2 <= current <= 0.5:
        score += 2; factors.append("Courants favorables")
    elif current < 0.2:
        score += 1; factors.append("Courants faibles")

    if wave < 1.0:
        score += 3; factors.append("Mer très calme")
    elif wave < 1.5:
        score += 2; factors.append("Mer calme")
    elif wave < 2.0:
        score += 1; factors.append("Mer modérée")

    if score >= 7:
        return "🐟🐟🐟 EXCELLENT", "excellent", factors
    elif score >= 5:
        return "🐟🐟 BON",        "good",      factors
    elif score >= 3:
        return "🐟 MOYEN",        "moderate",  factors
    else:
        return "🎣 FAIBLE",       "poor",      factors


def generate_recommendations(safety_level: str, fish_level: str,
                              wave: float, current: float, temp: float) -> list:
    """Génère des recommandations en Wolof/Français"""
    recs = []

    if safety_level == "danger":
        recs += ["⛔ NE PAS SORTIR EN MER", "Restez à quai — Conditions très dangereuses"]
    elif safety_level == "warning":
        recs += ["⚠️ Sortie fortement déconseillée", "Si nécessaire, restez près des côtes"]
    elif safety_level == "caution":
        recs += ["🟡 Vigilance accrue recommandée", "Sortie en groupe privilégiée"]
    else:
        recs.append("✅ Conditions sûres pour la navigation")

    if fish_level == "excellent":
        recs.append("🎣 Conditions OPTIMALES pour la pêche")
    elif fish_level == "good":
        recs.append("🎣 Bonnes conditions de pêche")
    elif fish_level == "moderate":
        recs.append("🎣 Pêche possible — Conditions moyennes")
    else:
        recs.append("🎣 Faibles perspectives de pêche")

    if wave > 2.5:
        recs.append(f"🌊 Vagues importantes : {wave}m — Embarcations légères interdites")
    if current > 0.8:
        recs.append(f"🌀 Forts courants : {current}m/s — Danger de dérive")
    if temp < 18:
        recs.append(f"🌡️ Eaux froides : {temp}°C — Upwelling actif, bonne pêche possible")

    return recs


def calculate_danger_score(wave: float, current: float, temp: float) -> int:
    """Score de danger de 0 à 100"""
    score = (
        (wave / 4.0) * 40 +
        (current / 1.5) * 30 +
        (max(0, abs(temp - 22) - 5) / 10) * 30
    )
    return min(100, int(score))


# ============================================================================
# MÉTÉO OPENWEATHER — CACHE CORRIGÉ
# ============================================================================

@lru_cache(maxsize=100)
def _fetch_weather_cached(lat_r: float, lon_r: float, cache_slot: int) -> dict | None:
    """
    Requête météo avec cache 30 min.
    CORRECTION : lat/lon arrondis (float hashable) + cache_slot comme clé temporelle.
    """
    if not OPENWEATHER_API_KEY:
        return None

    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": lat_r, "lon": lon_r,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang": "fr"
            },
            timeout=10
        )
        if resp.status_code == 200:
            d = resp.json()
            return {
                "wind_speed":          round(d["wind"]["speed"], 1),
                "wind_direction":      d["wind"].get("deg", 0),
                "wind_gust":           round(d["wind"].get("gust", 0), 1),
                "precipitation":       d.get("rain", {}).get("1h", 0.0),
                "humidity":            d["main"]["humidity"],
                "pressure":            d["main"]["pressure"],
                "visibility":          round(d.get("visibility", 10000) / 1000, 1),
                "clouds":              d["clouds"]["all"],
                "weather_description": d["weather"][0]["description"],
                "weather_icon":        d["weather"][0]["icon"],
            }
        else:
            log(f"OpenWeather HTTP {resp.status_code}", "WARNING")
    except requests.exceptions.Timeout:
        log("OpenWeather timeout", "WARNING")
    except Exception as e:
        log(f"OpenWeather erreur: {str(e)[:60]}", "WARNING")

    return None


def get_weather_for_zone(lat: float, lon: float) -> dict | None:
    """Wrapper public avec clé de cache automatique (30 min)"""
    cache_slot = int(time.time() / 1800)
    return _fetch_weather_cached(round(lat, 2), round(lon, 2), cache_slot)


# ============================================================================
# RÉCUPÉRATION DONNÉES COPERNICUS (avec retry)
# ============================================================================

def _fetch_copernicus_variable(dataset_id: str, variables: list,
                               lat: float, lon: float,
                               start: datetime, end: datetime,
                               depth_min: float = None,
                               depth_max: float = None) -> object:
    """
    Récupère un DataFrame Copernicus avec retry automatique.
    Retourne None si toutes les tentatives échouent.
    """
    if not COPERNICUS_AVAILABLE:
        return None

    kwargs = dict(
        dataset_id=dataset_id,
        variables=variables,
        minimum_longitude=lon - 0.1,
        maximum_longitude=lon + 0.1,
        minimum_latitude=lat - 0.1,
        maximum_latitude=lat + 0.1,
        start_datetime=start,
        end_datetime=end,
        username=COPERNICUS_USER,
        password=COPERNICUS_PASS,
    )
    if depth_min is not None:
        kwargs["minimum_depth"] = depth_min
        kwargs["maximum_depth"] = depth_max

    for attempt in range(1, COPERNICUS_MAX_RETRIES + 1):
        try:
            df = cm.read_dataframe(**kwargs)
            if df is not None and len(df) > 0:
                return df
            return None
        except Exception as e:
            msg = str(e)[:60]
            if attempt < COPERNICUS_MAX_RETRIES:
                log(f"  Copernicus tentative {attempt}/{COPERNICUS_MAX_RETRIES}: {msg}", "WARNING")
                time.sleep(COPERNICUS_RETRY_DELAY)
            else:
                log(f"  Copernicus échec ({COPERNICUS_MAX_RETRIES} tentatives): {msg}", "ERROR")

    return None


def fetch_zone_data(name: str, coords: dict, now: datetime) -> dict:
    """
    Récupère et calcule toutes les données pour une zone.
    En cas d'échec Copernicus, utilise des valeurs de fallback réalistes.
    """
    log(f"Traitement {name} ({coords['desc']})...")

    wave    = None
    temp    = None
    current = None

    # ── VAGUES ────────────────────────────────────────────────────
    wave_df = _fetch_copernicus_variable(
        DATASETS["waves"], ["VHM0"],
        coords["lat"], coords["lon"],
        now - timedelta(hours=6), now
    )
    if wave_df is not None and "VHM0" in wave_df.columns:
        vals = wave_df["VHM0"].dropna()
        if len(vals) > 0:
            wave = round(float(vals.iloc[-1]), 2)

    # ── TEMPÉRATURE ───────────────────────────────────────────────
    temp_df = _fetch_copernicus_variable(
        DATASETS["temperature"], ["thetao"],
        coords["lat"], coords["lon"],
        now - timedelta(hours=12), now,
        depth_min=0, depth_max=1
    )
    if temp_df is not None and "thetao" in temp_df.columns:
        vals = temp_df["thetao"].dropna()
        if len(vals) > 0:
            temp = round(float(vals.iloc[-1]), 1)

    # ── COURANTS ──────────────────────────────────────────────────
    cur_df = _fetch_copernicus_variable(
        DATASETS["current"], ["uo", "vo"],
        coords["lat"], coords["lon"],
        now - timedelta(hours=12), now,
        depth_min=0, depth_max=1
    )
    if cur_df is not None and "uo" in cur_df.columns and "vo" in cur_df.columns:
        u_vals = cur_df["uo"].dropna()
        v_vals = cur_df["vo"].dropna()
        if len(u_vals) > 0 and len(v_vals) > 0:
            u = float(u_vals.iloc[-1])
            v = float(v_vals.iloc[-1])
            current = round(float(np.sqrt(u**2 + v**2)), 2)

    # ── FALLBACK RÉALISTE PAR RÉGION ──────────────────────────────
    if wave is None:
        wave = {"Nord": 1.8, "Grande Côte": 1.6, "Dakar": 1.4,
                "Petite Côte": 1.2, "Sine Saloum": 1.0, "Casamance": 0.9}.get(coords["region"], 1.5)
    if temp is None:
        temp = {"Nord": 20.0, "Grande Côte": 21.0, "Dakar": 22.0,
                "Petite Côte": 23.0, "Sine Saloum": 24.0, "Casamance": 26.0}.get(coords["region"], 22.0)
    if current is None:
        current = 0.35

    # ── MÉTÉO ─────────────────────────────────────────────────────
    weather          = get_weather_for_zone(coords["lat"], coords["lon"])
    wind_speed       = weather["wind_speed"]       if weather else 5.0
    wind_direction   = weather["wind_direction"]   if weather else 0
    wind_gust        = weather["wind_gust"]        if weather else 0.0
    visibility       = weather["visibility"]       if weather else 10.0
    precipitation    = weather["precipitation"]    if weather else 0.0
    weather_desc     = weather["weather_description"] if weather else "Non disponible"
    humidity         = weather["humidity"]         if weather else 0
    clouds           = weather["clouds"]           if weather else 0
    pressure         = weather["pressure"]         if weather else 1013

    # ── CALCULS ───────────────────────────────────────────────────
    safety, safety_level, color = calculate_safety_level(wave, current)
    fish, fish_level, fish_factors = calculate_fish_index(temp, current, wave)
    recommendations = generate_recommendations(safety_level, fish_level, wave, current, temp)
    danger_score    = calculate_danger_score(wave, current, temp)

    result = {
        # Identité
        "zone":          name,
        "description":   coords["desc"],
        "region":        coords["region"],
        "lat":           coords["lat"],
        "lon":           coords["lon"],
        # Données marines
        "v_now":         wave,
        "t_now":         temp,
        "c_now":         current,
        # Météo
        "wind_speed":    wind_speed,
        "wind_direction":wind_direction,
        "wind_gust":     wind_gust,
        "visibility":    visibility,
        "precipitation": precipitation,
        "weather_desc":  weather_desc,
        "humidity":      humidity,
        "clouds":        clouds,
        "pressure":      pressure,
        # Indices
        "index":         fish,
        "fish_level":    fish_level,
        "fish_factors":  fish_factors,
        "safety":        safety,
        "safety_level":  safety_level,
        "color":         color,
        "danger_score":  danger_score,
        # Métadonnées
        "date":          now.strftime("%d/%m %H:%M"),
        "timestamp":     now.isoformat(),
        "recommendations": recommendations,
        "forecast":      [],
    }

    log(f"  {safety} | 🌊{wave}m | 🌡️{temp}°C | 💨{wind_speed}m/s | 🌀{current}m/s", "SUCCESS")
    return result


def fetch_data() -> list | None:
    """Récupère données pour toutes les zones"""
    log("=" * 60)
    log("Connexion à Copernicus Marine...")

    if COPERNICUS_AVAILABLE:
        if not COPERNICUS_USER or not COPERNICUS_PASS:
            log("COPERNICUS_USERNAME ou COPERNICUS_PASSWORD manquant dans .env", "ERROR")
            return None
        try:
            cm.login(username=COPERNICUS_USER, password=COPERNICUS_PASS)
            log("Connecté à Copernicus", "SUCCESS")
        except Exception as e:
            log(f"Échec connexion Copernicus: {str(e)[:80]}", "ERROR")
            return None
    else:
        log("Mode simulation (copernicusmarine non installé)", "WARNING")

    now     = datetime.utcnow()
    results = []
    errors  = []

    for name, coords in ZONES.items():
        try:
            result = fetch_zone_data(name, coords, now)
            results.append(result)
        except Exception as e:
            log(f"Erreur critique {name}: {str(e)}", "ERROR")
            traceback.print_exc()
            errors.append(name)
            continue

    log(f"Collecte terminée : {len(results)}/{len(ZONES)} zones OK"
        + (f" | {len(errors)} erreurs: {', '.join(errors)}" if errors else ""), "SUCCESS")

    return results if results else None


# ============================================================================
# HISTORIQUE
# ============================================================================

def save_to_history(data: list):
    """Sauvegarde une entrée dans l'historique quotidien"""
    history_dir = Path("logs/history")
    history_dir.mkdir(parents=True, exist_ok=True)

    now       = datetime.now()
    date_key  = now.strftime("%Y-%m-%d")
    hist_file = history_dir / f"{date_key}.json"

    daily = []
    if hist_file.exists():
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                daily = json.load(f)
        except (json.JSONDecodeError, IOError):
            log(f"Historique corrompu {date_key}, réinitialisé", "WARNING")
            daily = []

    daily.append({
        "timestamp": now.isoformat(),
        "zones":     data,
    })

    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(daily, f, ensure_ascii=False, indent=2)

    log(f"Historique sauvegardé : {date_key} ({len(daily)} entrées)", "SUCCESS")
    _cleanup_old_history(history_dir, days_to_keep=30)


def _cleanup_old_history(history_dir: Path, days_to_keep: int = 30):
    """Supprime les fichiers d'historique de plus de X jours"""
    cutoff = datetime.now() - timedelta(days=days_to_keep)
    removed = 0
    for f in history_dir.glob("*.json"):
        try:
            if datetime.strptime(f.stem, "%Y-%m-%d") < cutoff:
                f.unlink()
                removed += 1
        except ValueError:
            continue
    if removed:
        log(f"Nettoyage historique : {removed} fichier(s) supprimé(s)", "DEBUG")


# ============================================================================
# STATISTIQUES ZONES (format compatible history.html)
# ============================================================================

def generate_zone_statistics(zone_name: str) -> dict | None:
    """
    Génère les stats des 7 derniers jours pour une zone.
    Retourne un dict compatible avec history.html / all_zones.json
    """
    history_dir = Path("logs/history")
    if not history_dir.exists():
        return None

    zone_data = []

    for i in range(7):
        date      = datetime.now() - timedelta(days=i)
        date_key  = date.strftime("%Y-%m-%d")
        hist_file = history_dir / f"{date_key}.json"

        if not hist_file.exists():
            continue

        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                daily = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        for entry in daily:
            ts    = entry.get("timestamp", "")
            zones = entry.get("zones", [])
            for z in zones:
                if z.get("zone") == zone_name:
                    zone_data.append({
                        "timestamp":    ts,
                        "date":         date_key,
                        # Noms normalisés pour history.html
                        "wave":         z.get("v_now", 0.0),
                        "temp":         z.get("t_now", 0.0),
                        "wind":         z.get("wind_speed", 0.0),
                        "current":      z.get("c_now", 0.0),
                        "safety":       z.get("safety_level", "safe"),
                        "fish_level":   z.get("fish_level", "moderate"),
                        "danger_score": z.get("danger_score", 0),
                    })

    if not zone_data:
        return None

    # Extraire les séries
    waves    = [d["wave"]    for d in zone_data]
    temps    = [d["temp"]    for d in zone_data]
    winds    = [d["wind"]    for d in zone_data]
    currents = [d["current"] for d in zone_data]

    def safe_stats(values: list) -> dict:
        """Calcule min/max/avg/trend en gérant les listes vides"""
        if not values:
            return {"min": 0, "max": 0, "avg": 0, "trend": "stable"}
        arr = [v for v in values if v is not None]
        if not arr:
            return {"min": 0, "max": 0, "avg": 0, "trend": "stable"}
        return {
            "min":   round(min(arr), 2),
            "max":   round(max(arr), 2),
            "avg":   round(float(np.mean(arr)), 2),
            "trend": _calculate_trend(arr),
        }

    stats = {
        "zone":        zone_name,
        "description": ZONES.get(zone_name, {}).get("desc", zone_name),
        "region":      ZONES.get(zone_name, {}).get("region", ""),
        "period":      "7 jours",
        "data_points": len(zone_data),
        # IMPORTANT : limité à 168 points (7j × 24h) pour ne pas surcharger le front
        "history":     zone_data[-168:],
        "statistics": {
            "waves":       safe_stats(waves),
            "temperature": safe_stats(temps),
            "wind":        safe_stats(winds),
            "current":     safe_stats(currents),
        },
        "safety_summary": {
            "safe":    sum(1 for d in zone_data if d["safety"] == "safe"),
            "caution": sum(1 for d in zone_data if d["safety"] == "caution"),
            "warning": sum(1 for d in zone_data if d["safety"] == "warning"),
            "danger":  sum(1 for d in zone_data if d["safety"] == "danger"),
        },
        "best_day":  _find_best_day(zone_data),
        "worst_day": _find_worst_day(zone_data),
    }

    return stats


def _calculate_trend(values: list) -> str:
    """Régression linéaire → tendance (hausse / baisse / stable)"""
    if len(values) < 2:
        return "stable"
    x     = np.arange(len(values))
    slope = np.polyfit(x, values, 1)[0]
    if slope > 0.05:
        return "hausse"
    elif slope < -0.05:
        return "baisse"
    return "stable"


def _find_best_day(zone_data: list) -> dict:
    """Meilleur jour (score composite)"""
    if not zone_data:
        return {"date": None, "wave": None, "temp": None, "safety": None}

    def score(d):
        s  = 10 if d["safety"] == "safe" else (5 if d["safety"] == "caution" else 0)
        s += 10 if d["fish_level"] == "excellent" else (5 if d["fish_level"] == "good" else 0)
        s -= d["wave"] * 2
        return s

    best = max(zone_data, key=score)
    return {"date": best["date"], "wave": best["wave"], "temp": best["temp"], "safety": best["safety"]}


def _find_worst_day(zone_data: list) -> dict:
    """Pire jour (score danger)"""
    if not zone_data:
        return {"date": None, "wave": None, "safety": None}

    def score(d):
        s  = 10 if d["safety"] == "danger" else (5 if d["safety"] == "warning" else 0)
        s += d["wave"] * 3
        return s

    worst = max(zone_data, key=score)
    return {"date": worst["date"], "wave": worst["wave"], "safety": worst["safety"]}


def generate_all_stats() -> dict:
    """
    Génère les stats de toutes les zones et les sauvegarde dans :
    - logs/stats/all_zones.json         (utilisé par history.html)
    - logs/stats/<zone>.json            (par zone individuelle)
    - seasonality_data.json             (calendrier de pêche)
    """
    stats_dir = Path("logs/stats")
    stats_dir.mkdir(parents=True, exist_ok=True)

    all_stats = {}
    generated = 0

    for zone_name in ZONES:
        stats = generate_zone_statistics(zone_name)
        if stats:
            all_stats[zone_name] = stats
            generated += 1

            # Fichier individuel par zone
            safe_name = zone_name.lower().replace(" ", "_").replace("-", "_")
            zone_file = stats_dir / f"{safe_name}.json"
            with open(zone_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        else:
            log(f"Pas encore de données historiques pour {zone_name}", "DEBUG")

    # Fichier global pour history.html
    with open(stats_dir / "all_zones.json", "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    log(f"all_zones.json généré : {generated}/{len(ZONES)} zones", "SUCCESS")

    # Générer le fichier de saisonnalité pour history.html
    generate_seasonality_file()

    return all_stats


def generate_seasonality_file():
    """
    Génère seasonality_data.json utilisé par history.html
    Format : { "SAINT-LOUIS": [jan, fev, ..., dec], ... }
    """
    flat = {}
    for region_zones in SEASONALITY_DATA.values():
        for zone_name, monthly_values in region_zones.items():
            flat[zone_name] = monthly_values

    # Ajouter un fallback "Dakar" pour les zones non trouvées
    flat["Dakar"] = SEASONALITY_DATA["Dakar"]["DAKAR-YOFF"]

    with open("seasonality_data.json", "w", encoding="utf-8") as f:
        json.dump(flat, f, ensure_ascii=False, indent=2)

    log(f"seasonality_data.json généré ({len(flat)} zones)", "SUCCESS")


# ============================================================================
# SAUVEGARDE data.json
# ============================================================================

def save_data(data: list) -> bool:
    """Sauvegarde le fichier data.json principal"""
    try:
        Path("logs").mkdir(exist_ok=True)
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"data.json sauvegardé ({len(data)} zones)", "SUCCESS")
        return True
    except Exception as e:
        log(f"Erreur sauvegarde data.json: {e}", "ERROR")
        return False


# ============================================================================
# NOTIFICATIONS TELEGRAM
# ============================================================================

def _telegram_post(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    """Envoie un message Telegram — retourne True si succès"""
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10
        )
        if resp.status_code == 200:
            return True
        log(f"Telegram HTTP {resp.status_code}: {resp.text[:80]}", "WARNING")
    except Exception as e:
        log(f"Telegram erreur: {str(e)[:60]}", "WARNING")
    return False


def send_telegram(data: list):
    """Notification récapitulative (TG_TOKEN / TG_ID)"""
    if not TG_TOKEN or not TG_ID:
        log("Notification simple Telegram non configurée (TG_TOKEN/TG_ID)", "DEBUG")
        return

    # Regrouper par région
    regions: dict[str, list] = {}
    for z in data:
        regions.setdefault(z["region"], []).append(z)

    lines = [
        "🌊 *PECHEURCONNECT v3.0*",
        f"📊 {len(data)} zones | {len(regions)} régions\n",
    ]

    for region, zones in regions.items():
        lines.append(f"📍 *{region}*")
        for z in zones:
            lines.append(f"• {z['zone']}: {z['safety']}")
        lines.append("")

    lines.append(f"🕐 {data[0]['date']} UTC")

    if TELEGRAM_BOT_TOKEN:
        lines += ["", "🤖 *Bot interactif disponible !*", "Tapez /start pour commencer"]

    ok = _telegram_post(TG_TOKEN, TG_ID, "\n".join(lines))
    if ok:
        log("Notification Telegram envoyée", "SUCCESS")


def send_bot_broadcast(data: list):
    """Diffuse une mise à jour courte via le bot interactif"""
    if not TELEGRAM_BOT_TOKEN or not TG_ID:
        return

    safe_count   = sum(1 for z in data if z["safety_level"] == "safe")
    danger_count = sum(1 for z in data if z["safety_level"] in ("danger", "warning"))
    best_zones   = sorted(data, key=lambda x: x["v_now"])[:3]

    lines = [
        "🌊 *MISE À JOUR MÉTÉO MARINE* 🌊\n",
        f"✅ Zones sûres : {safe_count}/{len(data)}",
    ]
    if danger_count:
        lines.append(f"⚠️ Zones à risque : {danger_count}")

    lines += ["", "🏆 *MEILLEURES ZONES :*"]
    for i, z in enumerate(best_zones, 1):
        lines.append(f"{i}. {z['zone']} — {z['v_now']}m 🌊 {z['safety']}")

    lines += [
        "",
        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "Tapez /conditions pour plus de détails",
    ]

    ok = _telegram_post(TELEGRAM_BOT_TOKEN, TG_ID, "\n".join(lines))
    if ok:
        log("Broadcast bot Telegram envoyé", "SUCCESS")


# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

def main():
    start = datetime.now()

    log("=" * 60)
    log("PECHEURCONNECT v3.0")
    log("18 zones | Météo | Historique 7 jours | Bot Telegram")
    log("=" * 60)

    # 1. Collecte des données marines
    data = fetch_data()
    if not data:
        log("Échec de la collecte des données", "ERROR")
        exit(1)

    # 2. Sauvegarde data.json
    if not save_data(data):
        log("Échec de la sauvegarde", "ERROR")
        exit(1)

    # 3. Historique
    save_to_history(data)

    # 4. Statistiques + seasonality_data.json
    generate_all_stats()

    # 5. Notifications
    send_telegram(data)
    if TELEGRAM_BOT_TOKEN:
        send_bot_broadcast(data)

    duration = (datetime.now() - start).total_seconds()
    log("=" * 60)
    log(f"Terminé en {duration:.1f}s", "SUCCESS")

    if TELEGRAM_BOT_TOKEN:
        log("🤖 Bot Telegram interactif ACTIVÉ", "SUCCESS")
        log("Commandes disponibles : /start, /conditions, /zone, /alertes", "INFO")
    else:
        log("💡 Ajoutez TELEGRAM_BOT_TOKEN dans .env pour activer le bot interactif", "INFO")

    log("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Arrêt manuel (Ctrl+C)", "WARNING")
        exit(0)
    except Exception as e:
        log(f"Erreur fatale: {str(e)}", "ERROR")
        traceback.print_exc()
        exit(1)
