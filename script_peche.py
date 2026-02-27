#!/usr/bin/env python3
"""
PecheurConnect - Système de surveillance maritime pour pêcheurs sénégalais
Optimisé pour GitHub Actions avec gestion robuste des erreurs et retry.
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
from dataclasses import dataclass
from typing import Optional

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
        maxBytes=5 * 1024 * 1024,  # 5 Mo — lisible et explicite
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
    """Charge et valide les variables d'environnement critiques."""
    secrets = {
        "COPERNICUS_USER":    os.getenv("COPERNICUS_USERNAME"),
        "COPERNICUS_PASS":    os.getenv("COPERNICUS_PASSWORD"),
        "OPENWEATHER_KEY":    os.getenv("OPENWEATHER_API_KEY"),
        "TELEGRAM_TOKEN":     os.getenv("TELEGRAM_BOT_TOKEN"),  # Un seul token unifié
        "TELEGRAM_CHAT_ID":   os.getenv("TG_ID"),
    }
    missing = [k for k, v in secrets.items() if not v]
    if missing:
        logger.warning(f"Secrets manquants : {missing} — certaines fonctions seront désactivées.")
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
    logger.warning("copernicusmarine absente — mode simulation activé.")


# ============================================================================
# 4. ZONES SÉNÉGALAISES (18 zones complètes)
# ============================================================================

ZONES: dict[str, dict] = {
    "SAINT-LOUIS":             {"lat": 16.05, "lon": -16.65, "region": "Nord",         "desc": "Ndar - Nord"},
    "KAYAR":                   {"lat": 14.95, "lon": -17.35, "region": "Grande Côte",  "desc": "Fosse de Kayar"},
    "DAKAR-YOFF":              {"lat": 14.80, "lon": -17.65, "region": "Dakar",        "desc": "Yoff - Virage"},
    "DAKAR-SOUMBEDIOUNE":      {"lat": 14.68, "lon": -17.44, "region": "Dakar",        "desc": "Port artisanal"},
    "MBOUR-JOAL":              {"lat": 14.35, "lon": -17.15, "region": "Petite Côte",  "desc": "Port de Mbour"},
    "JOAL-FADIOUTH":           {"lat": 14.16, "lon": -16.85, "region": "Petite Côte",  "desc": "Île coquillière"},
    "PALMARIN":                {"lat": 14.00, "lon": -16.80, "region": "Petite Côte",  "desc": "Zone protégée"},
    "NDANGANE":                {"lat": 13.75, "lon": -16.65, "region": "Sine-Saloum",  "desc": "Delta du Saloum"},
    "DJIFER":                  {"lat": 13.60, "lon": -16.75, "region": "Sine-Saloum",  "desc": "Pointe de Sangomar"},
    "KAFOUNTINE":              {"lat": 12.90, "lon": -16.75, "region": "Casamance",    "desc": "Nord Casamance"},
    "CASAMANCE-ZIGUINCHOR":    {"lat": 12.50, "lon": -16.95, "region": "Casamance",    "desc": "Embouchure"},
    "CAP-SKIRRING":            {"lat": 12.39, "lon": -16.74, "region": "Casamance",    "desc": "Sud Casamance"},
    "DAKAR-HANN":              {"lat": 14.72, "lon": -17.38, "region": "Dakar",        "desc": "Baie de Hann"},
    "THIAROYE-SUR-MER":        {"lat": 14.75, "lon": -17.40, "region": "Dakar",        "desc": "Banlieue littorale"},
    "LOMPOUL":                 {"lat": 15.45, "lon": -16.70, "region": "Grande Côte",  "desc": "Plage isolée Nord"},
    "POTOU":                   {"lat": 15.70, "lon": -16.55, "region": "Grande Côte",  "desc": "Pêche côtière"},
    "GANDON":                  {"lat": 16.00, "lon": -16.50, "region": "Nord",         "desc": "Estuaire du Fleuve"},
    "SAINT-LOUIS-HYDROBASE":   {"lat": 16.10, "lon": -16.48, "region": "Nord",         "desc": "Zone estuarienne"},
}


# ============================================================================
# 5. CALCULS HALIEUTIQUES ET SÉCURITÉ (complète et typée)
# ============================================================================

@dataclass
class IndicesMaritime:
    securite_texte: str
    securite_code: str       # "danger" | "caution" | "safe"
    peche_score: float       # 0–10
    peche_texte: str
    conditions: dict


def calculate_indices(
    wave: float,
    temp: float,
    current: float
) -> IndicesMaritime:
    """
    Calcule les indices de sécurité et de pêche à partir des données marines.

    Args:
        wave:    Hauteur des vagues en mètres
        temp:    Température de surface (SST) en °C
        current: Vitesse du courant en m/s

    Returns:
        IndicesMaritime avec codes de sécurité et score de pêche
    """
    # --- Sécurité ---
    if wave > 2.5:
        s_text, s_code = "🔴 DANGER — Mer agitée", "danger"
    elif wave > 1.5:
        s_text, s_code = "🟡 PRUDENCE — Mer formée", "caution"
    else:
        s_text, s_code = "🟢 FAVORABLE — Mer calme", "safe"

    # --- Score de pêche (0–10) basé sur 3 critères pondérés ---
    # Température optimale pour les espèces côtières sénégalaises : 22–27°C
    temp_score = max(0.0, 10.0 - abs(temp - 24.5) * 1.2)

    # Vagues : idéalement < 1.0 m
    wave_score = max(0.0, 10.0 - wave * 4.0)

    # Courant : idéalement 0.1–0.4 m/s (upwelling favorable)
    current_score = 10.0 if 0.1 <= current <= 0.4 else max(0.0, 10.0 - abs(current - 0.25) * 15)

    peche_score = round(np.average(
        [temp_score, wave_score, current_score],
        weights=[0.4, 0.4, 0.2]
    ), 1)

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
        conditions={"wave": wave, "temp": temp, "current": current}
    )


# ============================================================================
# 6. CLIENT HTTP AVEC RETRY AUTOMATIQUE
# ============================================================================

async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    params: Optional[dict] = None,
    retries: int = 3,
    delay: float = 2.0
) -> Optional[dict]:
    """Effectue une requête GET avec retry exponentiel."""
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"HTTP {resp.status} sur {url} (tentative {attempt}/{retries})")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Erreur réseau (tentative {attempt}/{retries}) : {e}")

        if attempt < retries:
            await asyncio.sleep(delay * attempt)  # Backoff exponentiel

    return None


# ============================================================================
# 7. ENVOI TELEGRAM
# ============================================================================

async def send_telegram(message: str) -> bool:
    """Envoie un message Telegram avec gestion d'erreur."""
    token = SECRETS.get("TELEGRAM_TOKEN")
    chat_id = SECRETS.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram non configuré — message ignoré.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    async with aiohttp.ClientSession() as session:
        result = await fetch_with_retry(session, url, params=payload)
        if result:
            logger.info("Message Telegram envoyé avec succès.")
            return True
        logger.error("Échec de l'envoi Telegram.")
        return False


# ============================================================================
# 8. POINT D'ENTRÉE PRINCIPAL
# ============================================================================

async def main():
    logger.info(f"=== PecheurConnect démarré — {datetime.utcnow().isoformat()} UTC ===")
    logger.info(f"{len(ZONES)} zones chargées.")

    # Exemple : calcul pour Kayar
    zone = ZONES["KAYAR"]
    indices = calculate_indices(wave=1.2, temp=23.5, current=0.3)
    logger.info(f"[KAYAR] {indices.securite_texte} | Score pêche : {indices.peche_score}/10")

    message = (
        f"<b>🌊 PecheurConnect — {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC</b>\n"
        f"📍 Zone : KAYAR ({zone['desc']})\n"
        f"{indices.securite_texte}\n"
        f"{indices.peche_texte} ({indices.peche_score}/10)"
    )
    await send_telegram(message)


if __name__ == "__main__":
    asyncio.run(main())
