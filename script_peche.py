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

    def _blocking_fetch():
        try:
            ds = cm.open_dataset(
                dataset_id        = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
                variables         = ["uo", "vo", "thetao"],
                minimum_latitude  = lat - 0.1,
                maximum_latitude  = lat + 0.1,
                minimum_longitude = lon - 0.1,
                maximum_longitude = lon + 0.1,
                start_datetime    = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                end_datetime      = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                username          = user,
                password          = pwd,
            )
            uo  = float(ds["uo"].mean().values)
            vo  = float(ds["vo"].mean().values)
            sst = float(ds["thetao"].mean().values)
            current_speed = round(float(np.sqrt(uo**2 + vo**2)), 3)

            return {
                "source":        "copernicus",
                "sst":           round(sst, 2),
                "current_speed": current_speed,
                "current_u":     round(uo, 3),
                "current_v":     round(vo, 3),
                "timestamp":     datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Copernicus fetch error : {e}")
            return None

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, _blocking_fetch)

    return result if result else _simulate_marine_data(lat, lon)


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

    # Appels parallèles
    ow_data, cop_data = await asyncio.gather(
        fetch_openweather(session, lat, lon),
        fetch_copernicus(lat, lon)
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
        "updated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# 12. GÉNÉRATION DATA.JSON
# ============================================================================

def save_data_json(results: list[dict]) -> None:
    """
    Génère data.json avec toutes les zones + métadonnées.
    Sauvegarde également un snapshot horodaté dans logs/history/.
    """
    now = datetime.utcnow()

    # Statistiques globales
    scores      = [r["indices"]["peche_score"] for r in results]
    danger_zones = [r["zone"] for r in results if r["indices"]["securite_code"] == "danger"]

    payload = {
        "meta": {
            "version":      "3.0",
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

    # Génération data.json
    save_data_json(results)

    # Calcul stats pour Telegram
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

    # Envoi rapport Telegram
    message = build_telegram_report(results, stats)
    await send_telegram(message)

    logger.info("=== PecheurConnect terminé avec succès ===")


if __name__ == "__main__":
    asyncio.run(main())
