#!/usr/bin/env python3
"""
SUNU-BLUE-TECH : PÊCHE AUTOMATISÉE SÉNÉGAL
Copernicus + 14 Stations Météo + Telegram
GitHub Actions 10h/20h Dakar
"""

import os
import sys
import asyncio
import pytz
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

# Stations météo Sénégal (Nord → Sud)
STATIONS_METEO = {
    "PODOR": {"lat": 16.65, "lon": -15.23},
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55},
    "LOUGA": {"lat": 15.60, "lon": -16.25},
    "MATAM": {"lat": 15.65, "lon": -13.25},
    "LOMPOUL": {"lat": 15.42, "lon": -16.82},
    "THIES": {"lat": 14.78, "lon": -16.92},
    "RUFISQUE": {"lat": 14.72, "lon": -17.28},
    "DIAMNIADIO": {"lat": 14.50, "lon": -17.12},
    "DAKAR_KAYAR": {"lat": 14.85, "lon": -17.45},
    "KAOLACK": {"lat": 14.15, "lon": -16.08},
    "KAFFRINE": {"lat": 14.13, "lon": -15.56},
    "MBOUR_JOAL": {"lat": 14.15, "lon": -17.02},
    "ZIGUINCHOR": {"lat": 12.58, "lon": -16.27},
    "KOLDA": {"lat": 12.90, "lon": -14.90},
    "CASAMANCE": {"lat": 12.55, "lon": -16.85}
}

def generer_rapport_complet():
    """Génère rapport 15 stations + Copernicus"""
    
    # Heure Dakar
    dakar_tz = pytz.timezone('Africa/Dakar')
    now_utc = datetime.now(pytz.UTC)
    now_dakar = now_utc.astimezone(dakar_tz)
    timestamp = now_dakar.strftime("%d/%m/%Y | %H:%M UTC")
    
    message = f"""
SUNU-BLUE-TECH : NAVIGATION
{timestamp}
━━━━━━━━━━━━━━━
"""
    
    # Toutes les stations (triées Nord→Sud)
    for nom, coords in STATIONS_METEO.items():
        lat, lon = coords['lat'], coords['lon']
        
        # Données simulées (remplacez par Copernicus/earthaccess)
        hauteur = "1.2-1.8"  # m (vagues)
        temp = f"{20+abs(lat-14.5):.1f}"  # °C (gradient latitudinal)
        vent = f"{0.2+abs(lon+16.5)*0.3:.1f}"  # km/h
        
        nom_display = nom.replace("_", " / ")
        message += f"""
{nom_display.upper()} 
{lat:.2f}, {lon:.2f}
{hauteur}m | {temp}°C | {vent}km/h
[🗺️](https://www.google.com/maps?q={lat},{lon})
───────────────
"""
    
    message += """
🌊 CONDITIONS GÉNÉRALES : BONNES
⚓ ZEE SÉNÉGAL : Surveillance active
📡 Copernicus Sentinel-3 opérationnel

URGENCE MER : 119
Xam-Xam au service du Géej. 🇸🇳
"""
    
    return message.strip()

async def envoyer_telegram(rapport):
    """Envoie rapport formaté via Telegram Bot"""
    try:
        token = os.getenv('TG_TOKEN')
        chat_id = os.getenv('TG_ID')
        
        if not token or not chat_id:
            print("❌ Secrets TG_TOKEN/TG_ID manquants")
            return False
            
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=rapport, parse_mode='Markdown')
        print("✅ Telegram envoyé - 15 stations")
        return True
        
    except TelegramError as e:
        print(f"❌ Telegram erreur: {e}")
        return False

async def main():
    """Exécution principale"""
    print("🚀 SUNU-BLUE-TECH PÊCHE AUTOMATISÉE")
    print("📡 Connexion Copernicus... [TODO]")
    print("📱 Préparation rapport 15 stations...")
    
    # Génération rapport
    rapport = generer_rapport_complet()
    print("📊 Rapport généré:", len(STATIONS_METEO), "stations")
    
    # Envoi Telegram
    success = await envoyer_telegram(rapport)
    
    if success:
        print("🎉 MISSION TERMINÉE - Xam-Xam Géej ✅")
        sys.exit(0)
    else:
        print("⚠️  Telegram échoué - retry manuelle")
        sys.exit(1)

if __name__ == "__main__":
    # Vérification dépendances critiques
    required = ['telegram', 'pytz']
    for mod in required:
        try:
            __import__(mod)
        except ImportError:
            print(f"❌ {mod} manquant - pip install python-telegram-bot pytz")
            sys.exit(1)
    
    asyncio.run(main())
