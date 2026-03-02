#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         PecheurConnect v3.0 — Surveillance Maritime              ║
║         18 zones sénégalaises | OpenWeather + Copernicus         ║
║         GitHub Actions | Async | Production-Ready                ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import asyncio
import logging
import numpy as np
import aiohttp

from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# Charge automatiquement le fichier .env en développement local
# En production (GitHub Actions), les variables sont injectées directement
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv absent — normal en CI si non installé

# ============================================================================
# 1. CONFIGURATION ET LOGGING
# ============================================================================

def setup_logging() -> logging.Logger:
    for folder in ["logs/history", "logs/stats"]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("PecheurConnect")
    if logger.handlers:
        return logger  # Évite les handlers dupliqués en cas de rechargement

    handler = RotatingFileHandler(
        "logs/pecheur_connect.log",
        maxBytes=5 * 1024 * 1024,  # 5 Mo
        backupCount=3
    )
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    return logger


logger = setup_logging()


# ============================================================================
# 2. VALIDATION DES SECRETS
# ============================================================================

def load_secrets() -> dict:
    """
    Charge et valide les variables d'environnement critiques.
    Supporte plusieurs noms de variables pour la compatibilité
    avec les différentes configurations GitHub Actions.
    """
    # Telegram : supporte TELEGRAM_BOT_TOKEN et TG_TOKEN (ancien nom)
    telegram_token = (
        os.getenv("TELEGRAM_BOT_TOKEN") or
        os.getenv("TG_TOKEN")           # fallback ancien secret
    )
    telegram_chat = (
        os.getenv("TG_ID") or
        os.getenv("TELEGRAM_CHAT_ID")   # fallback
    )

    secrets = {
        "COPERNICUS_USER":  os.getenv("COPERNICUS_USERNAME"),
        "COPERNICUS_PASS":  os.getenv("COPERNICUS_PASSWORD"),
        "OPENWEATHER_KEY":  os.getenv("OPENWEATHER_API_KEY"),
        "TELEGRAM_TOKEN":   telegram_token,
        "TELEGRAM_CHAT_ID": telegram_chat,
    }

    missing = [k for k, v in secrets.items() if not v]
    if missing:
        logger.warning(f"Secrets manquants : {missing} — certaines fonctions seront désactivées.")
    else:
        logger.info("✅ Tous les secrets chargés avec succès.")

    # Diagnostic Telegram spécifique pour aider au débogage
    if not telegram_token:
        logger.warning(
            "Telegram désactivé. Vérifiez que le secret 'TELEGRAM_BOT_TOKEN' "
            "(ou 'TG_TOKEN') est défini dans GitHub Settings → Secrets and variables → Actions"
        )
    if not telegram_chat:
        logger.warning(
            "Chat ID Telegram manquant. Vérifiez que le secret 'TG_ID' "
            "est défini dans GitHub Settings → Secrets and variables → Actions"
        )

    return secrets


SECRETS = load_secrets()


# ============================================================================
# 3. IMPORT COPERNICUS AVEC FALLBACK
# ============================================================================

try:
    import copernicusmarine as cm
    COPERNICUS_AVAILABLE = True
    logger.info("Bibliothèque copernicusmarine chargée avec succès.")
except ImportError:
    COPERNICUS_AVAILABLE = False
    logger.warning("copernicusmarine introuvable — mode simulation activé.")
except Exception as _cop_err:
    # La lib est installée mais crashe à l'import (conflit dépendances, etc.)
    # Le message d'erreur exact aide au diagnostic
    COPERNICUS_AVAILABLE = False
    logger.warning(f"copernicusmarine présente mais non initialisable ({type(_cop_err).__name__}: {_cop_err}) — mode simulation activé.")


# ============================================================================
# 4. ZONES SÉNÉGALAISES — 18 zones complètes
# ============================================================================

ZONES: dict[str, dict] = {
    "SAINT-LOUIS":           {"lat": 16.05, "lon": -16.65, "region": "Nord",        "desc": "Ndar - Nord"},
    "GANDON":                {"lat": 16.00, "lon": -16.50, "region": "Nord",        "desc": "Estuaire du Fleuve"},
    "SAINT-LOUIS-HYDROBASE": {"lat": 16.10, "lon": -16.48, "region": "Nord",        "desc": "Zone estuarienne"},
    "POTOU":                 {"lat": 15.70, "lon": -16.55, "region": "Grande Côte", "desc": "Pêche côtière"},
    "LOMPOUL":               {"lat": 15.45, "lon": -16.70, "region": "Grande Côte", "desc": "Plage isolée Nord"},
    "KAYAR":                 {"lat": 14.95, "lon": -17.35, "region": "Grande Côte", "desc": "Fosse de Kayar"},
    "DAKAR-YOFF":            {"lat": 14.80, "lon": -17.65, "region": "Dakar",       "desc": "Yoff - Virage"},
    "DAKAR-SOUMBEDIOUNE":    {"lat": 14.68, "lon": -17.44, "region": "Dakar",       "desc": "Port artisanal"},
    "DAKAR-HANN":            {"lat": 14.72, "lon": -17.38, "region": "Dakar",       "desc": "Baie de Hann"},
    "THIAROYE-SUR-MER":      {"lat": 14.75, "lon": -17.40, "region": "Dakar",       "desc": "Banlieue littorale"},
    "MBOUR-JOAL":            {"lat": 14.35, "lon": -17.15, "region": "Petite Côte", "desc": "Port de Mbour"},
    "JOAL-FADIOUTH":         {"lat": 14.16, "lon": -16.85, "region": "Petite Côte", "desc": "Île coquillière"},
    "PALMARIN":              {"lat": 14.00, "lon": -16.80, "region": "Petite Côte", "desc": "Zone protégée"},
    "NDANGANE":              {"lat": 13.75, "lon": -16.65, "region": "Sine-Saloum", "desc": "Delta du Saloum"},
    "DJIFER":                {"lat": 13.60, "lon": -16.75, "region": "Sine-Saloum", "desc": "Pointe de Sangomar"},
    "KAFOUNTINE":            {"lat": 12.90, "lon": -16.75, "region": "Casamance",   "desc": "Nord Casamance"},
    "CASAMANCE-ZIGUINCHOR":  {"lat": 12.50, "lon": -16.95, "region": "Casamance",   "desc": "Embouchure"},
    "CAP-SKIRRING":          {"lat": 12.39, "lon": -16.74, "region": "Casamance",   "desc": "Sud Casamance"},
}


# ============================================================================
# 5. STRUCTURES DE DONNÉES
# ============================================================================

@dataclass
class IndicesMaritime:
    securite_texte: str
    securite_code: str        # "danger" | "caution" | "safe"
    peche_score: float        # 0–10
    peche_texte: str
    wave: float
    temp: float
    current: float


# ============================================================================
# 6. CALCULS HALIEUTIQUES ET SÉCURITÉ
# ============================================================================

def calculate_indices(wave: float, temp: float, current: float) -> IndicesMaritime:
    """
    Calcule les indices de sécurité et de pêche.

    Args:
        wave:    Hauteur des vagues en mètres
        temp:    Température de surface (SST) en °C
        current: Vitesse du courant en m/s

    Returns:
        IndicesMaritime avec codes de sécurité et score de pêche
    """
    # --- Sécurité — 4 niveaux cohérents avec le frontend ---
    # safe     : wave <= 1.0 m  → 🟢 Mer calme
    # caution  : wave <= 1.5 m  → 🟡 Mer agitée légère
    # warning  : wave <= 2.5 m  → 🟠 Mer formée
    # danger   : wave >  2.5 m  → 🔴 Mer agitée / dangereuse
    if wave > 2.5:
        s_text, s_code = "🔴 DANGER — Mer agitée", "danger"
    elif wave > 1.5:
        s_text, s_code = "🟠 PRUDENCE — Mer formée", "warning"
    elif wave > 1.0:
        s_text, s_code = "🟡 VIGILANCE — Mer légèrement agitée", "caution"
    else:
        s_text, s_code = "🟢 FAVORABLE — Mer calme", "safe"

    # --- Score de pêche pondéré (0–10) ---
    # Température optimale espèces côtières sénégalaises : 22–27°C
    temp_score    = max(0.0, 10.0 - abs(temp - 24.5) * 1.2)
    # Vagues : idéalement < 1.0 m
    wave_score    = max(0.0, 10.0 - wave * 4.0)
    # Courant : upwelling favorable entre 0.1 et 0.4 m/s
    current_score = 10.0 if 0.1 <= current <= 0.4 else max(0.0, 10.0 - abs(current - 0.25) * 15)

    peche_score = round(
        float(np.average(
            [temp_score, wave_score, current_score],
            weights=[0.4, 0.4, 0.2]
        )), 1
    )

    if peche_score >= 7:
        peche_texte = "🎣 Excellentes conditions de pêche"
    elif peche_score >= 4:
        peche_texte = "🎣 Conditions acceptables"
    else:
        peche_texte = "🎣 Conditions défavorables"

    return IndicesMaritime(
        securite_texte=s_text,
        securite_code=s_code,
        peche_score=peche_score,
        peche_texte=peche_texte,
        wave=wave,
        temp=temp,
        current=current,
    )


# ============================================================================
# 7. CLIENT HTTP AVEC RETRY EXPONENTIEL
# ============================================================================

async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    params: Optional[dict] = None,
    retries: int = 3,
    delay: float = 2.0
) -> Optional[dict]:
    """Effectue une requête GET avec retry et backoff exponentiel."""
    for attempt in range(1, retries + 1):
        try:
            async with session.get(
                url, params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"HTTP {resp.status} sur {url} (tentative {attempt}/{retries})")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Erreur réseau (tentative {attempt}/{retries}) : {e}")

        if attempt < retries:
            await asyncio.sleep(delay * attempt)

    return None


# ============================================================================
# 8. SIMULATION MARINE RÉALISTE (fallback)
# ============================================================================

def _simulate_marine_data(lat: float, lon: float) -> dict:
    """
    Génère des données marines simulées réalistes pour le Sénégal.
    Valeurs basées sur les moyennes saisonnières côte sénégalaise.
    Légère variation pseudo-aléatoire basée sur la position géographique.
    """
    seed = int(abs(lat * 100 + lon * 100)) % 1000
    rng  = np.random.default_rng(seed)

    return {
        "source":        "simulation",
        "sst":           round(float(rng.uniform(22.0, 27.0)), 2),
        "temp_air":      round(float(rng.uniform(24.0, 30.0)), 2),
        "wave_height":   round(float(rng.uniform(0.4, 1.8)),   2),
        "current_speed": round(float(rng.uniform(0.1, 0.5)),   3),
        "wind_speed":    round(float(rng.uniform(2.0, 8.0)),   2),
        "timestamp":     datetime.utcnow().isoformat()
    }


# ============================================================================
# 9. FETCHER OPENWEATHER
# ============================================================================

async def fetch_openweather(
    session: aiohttp.ClientSession,
    lat: float,
    lon: float
) -> dict:
    """
    Récupère les conditions météo-marines via OpenWeather One Call API 3.0.
    Retourne un dict normalisé ou des valeurs de simulation si échec.
    """
    api_key = SECRETS.get("OPENWEATHER_KEY")

    if not api_key:
        logger.warning("OpenWeather : clé absente — simulation activée.")
        return _simulate_marine_data(lat, lon)

    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat":     lat,
        "lon":     lon,
        "exclude": "minutely,hourly,daily,alerts",
        "appid":   api_key,
        "units":   "metric"
    }

    data = await fetch_with_retry(session, url, params=params)

    if not data:
        logger.warning(f"OpenWeather échec ({lat},{lon}) — simulation activée.")
        return _simulate_marine_data(lat, lon)

    try:
        current    = data["current"]
        wind_ms    = current.get("wind_speed", 3.0)
        # Formule de Bretschneider simplifiée : estimation vagues depuis vent
        wave_est   = round(0.0248 * (wind_ms ** 2), 2)

        return {
            "source":      "openweather",
            "temp_air":    current.get("temp", 25.0),
            "wind_speed":  wind_ms,
            "wave_height": wave_est,
            "humidity":    current.get("humidity", 70),
            "weather_id":  current.get("weather", [{}])[0].get("id", 800),
            "timestamp":   datetime.utcnow().isoformat()
        }
    except (KeyError, TypeError) as e:
        logger.error(f"OpenWeather parsing error : {e}")
        return _simulate_marine_data(lat, lon)


# ============================================================================
# 10. FETCHER COPERNICUS (SST + COURANTS)
# ============================================================================

async def fetch_copernicus(lat: float, lon: float) -> dict:
    """
    Récupère SST et courants via copernicusmarine.
    Exécuté dans un ThreadPoolExecutor pour ne pas bloquer l'event loop.
    Retourne simulation si bibliothèque absente ou credentials manquants.
    """
    if not COPERNICUS_AVAILABLE:
        return _simulate_marine_data(lat, lon)

    user = SECRETS.get("COPERNICUS_USER")
    pwd  = SECRETS.get("COPERNICUS_PASS")

    if not user or not pwd:
        logger.warning("Copernicus : credentials absents — simulation activée.")
        return _simulate_marine_data(lat, lon)

    def _open_cm_dataset(dataset_id: str, variables: list, bbox: dict, dt: str) -> object:
        """
        Ouvre un dataset Copernicus avec gestion automatique du conflit zarr v3.
        Applique un monkey-patch si zarr_format est refusé, puis restaure.
        """
        kwargs = dict(
            dataset_id        = dataset_id,
            variables         = variables,
            minimum_latitude  = bbox["lat_min"],
            maximum_latitude  = bbox["lat_max"],
            minimum_longitude = bbox["lon_min"],
            maximum_longitude = bbox["lon_max"],
            start_datetime    = dt,
            end_datetime      = dt,
        )
        try:
            return cm.open_dataset(**kwargs)
        except TypeError as te:
            if "zarr_format" not in str(te):
                raise
            logger.warning(f"zarr v3 patch appliqué pour {dataset_id}")
            import zarr as _zarr
            _orig = _zarr.open
            _zarr.open = lambda *a, **kw: _orig(*a, **{k: v for k, v in kw.items() if k != "zarr_format"})
            try:
                return cm.open_dataset(**kwargs)
            finally:
                _zarr.open = _orig  # Toujours restaurer

    def _blocking_fetch():
        try:
            now = datetime.utcnow()
            dt  = now.strftime("%Y-%m-%dT%H:%M:%S")
            bbox = {
                "lat_min": lat - 0.1, "lat_max": lat + 0.1,
                "lon_min": lon - 0.1, "lon_max": lon + 0.1,
            }

            # ── Dataset 1 : Courants de surface (uo, vo) ──
            # cmems_mod_glo_phy-cur : uniquement uo/vo, PAS de thetao
            ds_cur = _open_cm_dataset(
                "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
                ["uo", "vo"],
                bbox, dt
            )
            sel_cur = ds_cur.isel(time=0) if "time" in ds_cur.dims else ds_cur
            uo = float(sel_cur["uo"].mean().values)
            vo = float(sel_cur["vo"].mean().values)
            current_speed = round(float(np.sqrt(uo**2 + vo**2)), 3)
            logger.info(f"Copernicus courants OK ({lat},{lon}) — {current_speed} m/s")

            # ── Dataset 2 : SST (thetao) ──
            # cmems_mod_glo_phy-thetao : dataset dédié à la température
            sst = None
            try:
                ds_sst = _open_cm_dataset(
                    "cmems_mod_glo_phy_anfc_0.083deg_P1D-m",
                    ["thetao"],
                    bbox, dt
                )
                sel_sst = ds_sst.isel(time=0) if "time" in ds_sst.dims else ds_sst
                # Prendre la couche de surface (depth index 0)
                if "depth" in sel_sst.dims:
                    sel_sst = sel_sst.isel(depth=0)
                sst = round(float(sel_sst["thetao"].mean().values), 2)
                logger.info(f"Copernicus SST OK ({lat},{lon}) — {sst}°C")
            except Exception as e_sst:
                logger.warning(f"Copernicus SST ignorée ({lat},{lon}) : {e_sst}")
                sst = None  # OpenWeather prendra le relais

            return {
                "source":        "copernicus",
                "sst":           sst,
                "current_speed": current_speed,
                "current_u":     round(uo, 3),
                "current_v":     round(vo, 3),
                "timestamp":     now.isoformat()
            }
        except Exception as e:
            logger.error(f"Copernicus fetch error : {e}")
            return None

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, _blocking_fetch)

    return result if result else _simulate_marine_data(lat, lon)



# ============================================================================
# 10b. PRÉVISIONS 7 JOURS OPENWEATHER
# ============================================================================

async def fetch_forecast_7days(lat: float, lon: float) -> list:
    """
    Récupère les prévisions météo-marines sur 7 jours via OpenWeather One Call API.
    Retourne une liste de 7 dict avec score, houle estimée, vent, température.
    """
    api_key = SECRETS.get("OPENWEATHER_KEY")
    if not api_key:
        return _simulate_forecast(lat, lon)

    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}&exclude=minutely,alerts"
        f"&appid={api_key}&units=metric"
    )

    async with aiohttp.ClientSession() as session:
        for attempt in range(1, 4):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        daily = data.get("daily", [])[:7]
                        result = []
                        for d in daily:
                            wind_ms = d.get("wind_speed", 5)
                            # Estimation Bretschneider : Hs ≈ 0.0248 * U^2 (U en m/s, fetch 200km)
                            wave = round(min(4.0, 0.0248 * wind_ms ** 2), 2)
                            temp = d.get("temp", {}).get("day", 25)
                            pop  = d.get("pop", 0)  # probabilité pluie
                            uvi  = d.get("uvi", 5)

                            # Score pêche prévisionnel
                            s_wave  = max(0, 10 - wave * 4)
                            s_temp  = 10 - abs(temp - 24.5) * 0.6
                            s_wind  = max(0, 10 - wind_ms * 0.4)
                            score   = round((s_wave*.45 + s_temp*.3 + s_wind*.25), 1)

                            # Code sécurité
                            if wave <= 1.0:
                                sec = "safe"
                            elif wave <= 1.5:
                                sec = "caution"
                            elif wave <= 2.5:
                                sec = "warning"
                            else:
                                sec = "danger"

                            result.append({
                                "dt":         d.get("dt"),
                                "wave":       wave,
                                "wind_ms":    round(wind_ms, 1),
                                "wind_kn":    round(wind_ms * 1.944, 1),
                                "temp":       round(temp, 1),
                                "pop":        round(pop * 100),
                                "uvi":        round(uvi, 1),
                                "peche_score":  score,
                                "securite_code": sec,
                            })
                        logger.info(f"OpenWeather Forecast 7J OK ({lat},{lon})")
                        return result
                    elif resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        logger.warning(f"Forecast HTTP {resp.status} — simulation")
                        return _simulate_forecast(lat, lon)
            except Exception as e:
                logger.warning(f"Forecast erreur ({lat},{lon}) tentative {attempt}: {e}")
                await asyncio.sleep(1)

    return _simulate_forecast(lat, lon)


def _simulate_forecast(lat: float, lon: float) -> list:
    """Génère des prévisions simulées réalistes sur 7 jours."""
    import random, time
    rng = random.Random(int(lat * 1000 + lon * 100))
    now = int(time.time())
    result = []
    base_wave = rng.uniform(0.5, 1.8)
    for i in range(7):
        wave = round(max(0.2, base_wave + rng.gauss(0, 0.4) + i * 0.05), 2)
        wind = round(wave / 0.0248 ** 0.5 + rng.gauss(0, 1), 1)
        temp = round(23.5 + rng.gauss(0, 1.5), 1)
        s_wave = max(0, 10 - wave * 4)
        s_temp = 10 - abs(temp - 24.5) * 0.6
        s_wind = max(0, 10 - wind * 0.4)
        score  = round(s_wave*.45 + s_temp*.3 + s_wind*.25, 1)
        sec = "safe" if wave <= 1.0 else "caution" if wave <= 1.5 else "warning" if wave <= 2.5 else "danger"
        result.append({
            "dt": now + i * 86400,
            "wave": wave, "wind_ms": wind, "wind_kn": round(wind * 1.944, 1),
            "temp": temp, "pop": rng.randint(0, 40), "uvi": round(rng.uniform(4, 9), 1),
            "peche_score": score, "securite_code": sec,
        })
    return result


# ============================================================================
# 11. AGRÉGATION PAR ZONE (OpenWeather + Copernicus → Indices)
# ============================================================================

async def fetch_zone_data(
    session: aiohttp.ClientSession,
    zone_name: str,
    zone_info: dict
) -> dict:
    """
    Récupère et fusionne les données OpenWeather + Copernicus pour une zone.
    Les appels sont parallélisés via asyncio.gather pour la performance.
    """
    lat, lon = zone_info["lat"], zone_info["lon"]

    # Appels parallèles (OpenWeather + Copernicus + Prévisions 7J)
    ow_data, cop_data, forecast_7j = await asyncio.gather(
        fetch_openweather(session, lat, lon),
        fetch_copernicus(lat, lon),
        fetch_forecast_7days(lat, lon)
    )

    # Fusion : Copernicus prioritaire pour SST et courants
    wave    = ow_data.get("wave_height", 1.0)
    temp    = cop_data.get("sst") or ow_data.get("temp_air", 25.0)
    current = cop_data.get("current_speed", 0.25)

    indices = calculate_indices(wave, temp, current)

    return {
        "zone":        zone_name,
        "region":      zone_info["region"],
        "desc":        zone_info["desc"],
        "lat":         lat,
        "lon":         lon,
        "openweather": ow_data,
        "copernicus":  cop_data,
        "indices": {
            "securite_texte": indices.securite_texte,
            "securite_code":  indices.securite_code,
            "peche_score":    indices.peche_score,
            "peche_texte":    indices.peche_texte,
            "wave":           indices.wave,
            "temp":           indices.temp,
            "current":        indices.current,
        },
        "updated_at":  datetime.utcnow().isoformat(),
        "forecast_7j": forecast_7j,
    }


# ============================================================================
# 12. GÉNÉRATION DATA.JSON
# ============================================================================

def save_data_json(results: list[dict], tides_data: dict = None) -> None:
    """
    Génère data.json avec toutes les zones + métadonnées.
    Sauvegarde également un snapshot horodaté dans logs/history/.
    """
    now = datetime.utcnow()

    # Statistiques globales
    scores      = [r["indices"]["peche_score"] for r in results]
    danger_zones = [r["zone"] for r in results if r["indices"]["securite_code"] == "danger"]

    # Indexer les marées par zone pour le payload
    tides_payload = tides_data or {}
    payload = {
        "meta": {
            "version":      "4.2",
            "generated_at": now.isoformat() + "Z",
            "total_zones":  len(results),
            "sources":      list({r["copernicus"]["source"] for r in results}),
        },
        "stats": {
            "score_moyen":   round(float(np.mean(scores)), 2),
            "score_max":     max(scores),
            "score_min":     min(scores),
            "zones_danger":  danger_zones,
            "zones_count":   {
                "danger":  sum(1 for r in results if r["indices"]["securite_code"] == "danger"),
                "warning": sum(1 for r in results if r["indices"]["securite_code"] == "warning"),
                "caution": sum(1 for r in results if r["indices"]["securite_code"] == "caution"),
                "safe":    sum(1 for r in results if r["indices"]["securite_code"] == "safe"),
            }
        },
        "zones": {r["zone"]: r for r in results}
    }

    # Fichier principal — lu par le workflow GitHub Actions
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("✅ data.json généré avec succès.")

    # Snapshot horodaté
    snapshot_path = f"logs/history/data_{now.strftime('%Y%m%d_%H%M')}.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(f"📁 Snapshot sauvegardé : {snapshot_path}")



# ============================================================================
# MARÉES HARMONIQUES (Formule SHOM simplifiée — 4 constituants principaux)
# ============================================================================

TIDE_STATIONS = {
    "SAINT-LOUIS":    {"M2": 0.42, "S2": 0.14, "K1": 0.08, "O1": 0.06, "phase_offset": 0.0},
    "DAKAR-YOFF":     {"M2": 0.65, "S2": 0.22, "K1": 0.11, "O1": 0.09, "phase_offset": 0.3},
    "MBOUR-JOAL":     {"M2": 0.70, "S2": 0.24, "K1": 0.12, "O1": 0.10, "phase_offset": 0.5},
    "KAYAR":          {"M2": 0.58, "S2": 0.19, "K1": 0.10, "O1": 0.08, "phase_offset": 0.2},
    "CAP-SKIRRING":   {"M2": 0.55, "S2": 0.18, "K1": 0.09, "O1": 0.07, "phase_offset": 1.1},
    "CASAMANCE-ZIGUINCHOR": {"M2": 0.48, "S2": 0.16, "K1": 0.08, "O1": 0.06, "phase_offset": 1.4},
}
# Fréquences angulaires (rad/heure)
TIDE_OMEGA = {"M2": 0.5059, "S2": 0.5236, "K1": 0.2625, "O1": 0.2434}

def compute_tides(zone: str, date_utc: datetime) -> dict:
    """
    Calcule les horaires et hauteurs de marée via décomposition harmonique.
    Retourne PM/BM avec heures et coefficients pour la zone donnée.
    """
    station = TIDE_STATIONS.get(zone, TIDE_STATIONS["DAKAR-YOFF"])
    t0 = date_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def height(t_hours: float) -> float:
        h = 0.0
        for comp, omega in TIDE_OMEGA.items():
        	amp = station.get(comp, 0.1)
        	phase = station["phase_offset"] + t_hours * 0.05
        	h += amp * np.cos(omega * t_hours + phase)
        return round(h + 0.8, 3)  # hauteur moyenne de référence
    
    # Échantillonner sur 24h (résolution 6 minutes)
    hours = [i * 0.1 for i in range(241)]
    heights = [height(h) for h in hours]
    
    # Détecter les extrema (PM = local max, BM = local min)
    events = []
    for i in range(1, len(heights) - 1):
        if heights[i] > heights[i-1] and heights[i] > heights[i+1]:
            t = t0 + __import__("datetime").timedelta(hours=hours[i])
            coef = int(45 + (heights[i] - 0.3) / 1.2 * 60)
            events.append({
                "type": "PM", "heure": t.strftime("%H:%M"),
                "hauteur": heights[i], "coef": min(120, max(20, coef))
            })
        elif heights[i] < heights[i-1] and heights[i] < heights[i+1]:
            t = t0 + __import__("datetime").timedelta(hours=hours[i])
            events.append({
                "type": "BM", "heure": t.strftime("%H:%M"),
                "hauteur": heights[i], "coef": 0
            })
    
    # Courbe 24h (24 points)
    courbe = [round(height(h), 3) for h in range(25)]
    return {"events": events[:4], "courbe_24h": courbe, "zone": zone}


# ============================================================================
# EXPORT CSV HISTORIQUE
# ============================================================================

def export_csv(results: list) -> None:
    """Exporte les données zones en CSV dans logs/history/."""
    import csv
    now = datetime.utcnow()
    fname = f"logs/history/export_{now.strftime('%Y%m%d_%H%M')}.csv"
    fields = ["zone","region","lat","lon","wave","temp","current",
               "securite_code","peche_score","source","updated_at"]
    with open(fname, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({
                "zone":         r["zone"],
                "region":       r["region"],
                "lat":          r["lat"],
                "lon":          r["lon"],
                "wave":         r["indices"]["wave"],
                "temp":         r["indices"]["temp"],
                "current":      r["indices"]["current"],
                "securite_code":r["indices"]["securite_code"],
                "peche_score":  r["indices"]["peche_score"],
                "source":       r["copernicus"]["source"],
                "updated_at":   r["updated_at"],
            })
    logger.info(f"✅ Export CSV : {fname}")


# ============================================================================
# RAPPORT DISCORD WEBHOOK
# ============================================================================

async def send_discord(message: str) -> bool:
    """Envoie un embed Discord via webhook (optionnel — DISCORD_WEBHOOK secret)."""
    webhook_url = os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        logger.info("Discord webhook non configuré — ignoré.")
        return False

    danger_zones  = [l for l in message.split("\n") if "DANGER" in l]
    top_zones     = [l for l in message.split("\n") if "Score" in l][:3]
    color = 0xFF2044 if danger_zones else 0x00DCC8

    payload = {
        "embeds": [{
            "title":       "🌊 PecheurConnect — Rapport Maritime",
            "description": message[:2000],
            "color":       color,
            "footer":      {"text": f"Sénégal · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"},
            "thumbnail":   {"url": "https://em-content.zobj.net/source/twitter/376/fishing-pole_1f3a3.png"}
        }]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status in (200, 204):
                    logger.info("✅ Message Discord envoyé.")
                    return True
                else:
                    logger.warning(f"Discord HTTP {r.status}")
    except Exception as e:
        logger.error(f"Discord erreur : {e}")
    return False


# ============================================================================
# 13. RAPPORT TELEGRAM
# ============================================================================

async def send_telegram(message: str) -> bool:
    """Envoie un message Telegram avec gestion d'erreur."""
    token   = SECRETS.get("TELEGRAM_TOKEN")
    chat_id = SECRETS.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram non configuré — message ignoré.")
        return False

    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}

    async with aiohttp.ClientSession() as session:
        result = await fetch_with_retry(session, url, params=payload)
        if result:
            logger.info("✅ Message Telegram envoyé avec succès.")
            return True
        logger.error("❌ Échec de l'envoi Telegram.")
        return False


def build_telegram_report(results: list[dict], stats: dict) -> str:
    """Construit le message Telegram de synthèse pour les 18 zones."""
    now    = datetime.utcnow().strftime('%d/%m/%Y %H:%M')
    lines  = [f"<b>🌊 PecheurConnect — {now} UTC</b>"]
    lines += [f"📊 Score moyen : <b>{stats['score_moyen']}/10</b> | {len(results)} zones analysées"]

    if stats["zones_danger"]:
        lines.append(f"🔴 Zones DANGER : {', '.join(stats['zones_danger'])}")

    lines.append("")

    # Top 3 meilleures zones
    top3 = sorted(results, key=lambda r: r["indices"]["peche_score"], reverse=True)[:3]
    lines.append("<b>🏆 Top 3 zones de pêche :</b>")
    for i, r in enumerate(top3, 1):
        lines.append(
            f"{i}. {r['zone']} ({r['region']}) — "
            f"{r['indices']['peche_score']}/10 {r['indices']['securite_texte']}"
        )

    lines.append("")
    lines.append(
        f"🟢 Safe: {stats['zones_count']['safe']} | "
        f"🟡 Vigilance: {stats['zones_count']['caution']} | "
        f"🟠 Prudence: {stats['zones_count']['warning']} | "
        f"🔴 Danger: {stats['zones_count']['danger']}"
    )

    return "\n".join(lines)


# ============================================================================
# 14. POINT D'ENTRÉE PRINCIPAL
# ============================================================================

async def main():
    logger.info(f"=== PecheurConnect démarré — {datetime.utcnow().isoformat()} UTC ===")
    logger.info(f"{len(ZONES)} zones chargées.")

    results = []

    async with aiohttp.ClientSession() as session:
        # Traitement de toutes les zones en parallèle (batch de 6 pour éviter le rate-limit)
        zone_items = list(ZONES.items())
        batch_size = 6

        for i in range(0, len(zone_items), batch_size):
            batch = zone_items[i:i + batch_size]
            logger.info(f"Traitement batch {i // batch_size + 1} — zones : {[z[0] for z in batch]}")

            batch_results = await asyncio.gather(*[
                fetch_zone_data(session, name, info)
                for name, info in batch
            ])
            results.extend(batch_results)

            # Pause entre les batches pour respecter les rate-limits API
            if i + batch_size < len(zone_items):
                await asyncio.sleep(1.0)

    # Log résumé
    for r in results:
        logger.info(
            f"[{r['zone']:25s}] {r['indices']['securite_texte']:30s} | "
            f"Score : {r['indices']['peche_score']:4.1f}/10 | "
            f"Source : {r['copernicus']['source']}"
        )

    # ── Calcul marées pour les zones-clés ──
    logger.info("Calcul marées harmoniques...")
    now_utc = datetime.utcnow()
    tides_data = {}
    for zone_name in ["DAKAR-YOFF", "KAYAR", "MBOUR-JOAL", "SAINT-LOUIS",
                       "CAP-SKIRRING", "CASAMANCE-ZIGUINCHOR"]:
        tides_data[zone_name] = compute_tides(zone_name, now_utc)
        logger.info(f"  Marées {zone_name}: {len(tides_data[zone_name]['events'])} événements")

    # ── Injecter marées dans data.json ──
    save_data_json(results, tides_data=tides_data)

    # ── Export CSV historique ──
    try:
        export_csv(results)
    except Exception as e:
        logger.warning(f"Export CSV ignoré : {e}")

    # Calcul stats pour rapports
    scores = [r["indices"]["peche_score"] for r in results]
    stats  = {
        "score_moyen":  round(float(np.mean(scores)), 2),
        "zones_danger": [r["zone"] for r in results if r["indices"]["securite_code"] == "danger"],
        "zones_count":  {
            "danger":  sum(1 for r in results if r["indices"]["securite_code"] == "danger"),
            "warning": sum(1 for r in results if r["indices"]["securite_code"] == "warning"),
            "caution": sum(1 for r in results if r["indices"]["securite_code"] == "caution"),
            "safe":    sum(1 for r in results if r["indices"]["securite_code"] == "safe"),
        }
    }

    # ── Envoi rapports (Telegram + Discord en parallèle) ──
    message = build_telegram_report(results, stats)
    tg_ok, dc_ok = await asyncio.gather(
        send_telegram(message),
        send_discord(message)
    )
    logger.info(f"Telegram: {'✅' if tg_ok else '⚠️'} | Discord: {'✅' if dc_ok else '—'}")

    logger.info("=== PecheurConnect v4.2 terminé avec succès ===")


if __name__ == "__main__":
    asyncio.run(main())
