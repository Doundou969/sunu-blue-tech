#!/usr/bin/env python3
import os
import requests
import pandas as pd
from datetime import datetime
import sys
import traceback

def send_telegram(message):
    """Envoi message Telegram avec gestion d'erreur"""
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ ERREUR: TELEGRAM_TOKEN ou CHAT_ID manquant")
        return False
    
    print(f"📱 Envoi à chat_id: {chat_id[:8]}...")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"✅ Telegram: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Telegram erreur: {e}")
        return False

def job():
    """Fonction principale appelée par GitHub Actions"""
    print("🚀 SCRIPT DÉMARRE ! 22 Jan 2026")
    print(f"📅 Heure: {datetime.now()}")
    print(f"🔑 Token OK: {'TELEGRAM_TOKEN' in os.environ}")
    print(f"📱 Chat ID: {os.getenv('TELEGRAM_CHAT_ID')[:8] if os.getenv('TELEGRAM_CHAT_ID') else 'MANQUANT'}")
    
    # Test immédiat
    if send_telegram("🧪 *SUNU-BLUE-TECH TEST*\n✅ Script Python OK !\n⏰ 22 Jan 2026"):
        print("🎉 Test Telegram réussi !")
    else:
        print("💥 Test Telegram échoué !")
        sys.exit(1)
    
    # Votre logique pêche ici
    message = f"""
🎣 *RAPPORT QUOTIDIEN PÊCHE*
🇸🇳 Dakar - 22 Jan 2026

✅ Workflow GitHub OK
✅ Script Python OK
✅ Telegram connecté

*Prochaines étapes :*
• Scraping données pêche
• Analyse prix
• Alertes opportunités
"""
    
    send_telegram(message)
    print("🏁 MISSION ACCOMPLIE !")
    return True

if __name__ == "__main__":
    try:
        job()
    except Exception as e:
        print(f"💥 ERREUR FATALE: {e}")
        traceback.print_exc()
        sys.exit(1)
