#!/usr/bin/env python3
import os
import requests
import json

print("🚀 Script démarré")
os.makedirs("public", exist_ok=True)

# TEST TELEGRAM
tg_token = os.getenv('TG_TOKEN')
tg_id = os.getenv('TG_ID')

print(f"🔍 TG_TOKEN: {'OK' if tg_token else '❌ MANQUANT'}")
print(f"🔍 TG_ID: {'OK' if tg_id else '❌ MANQUANT'}")

if tg_token and tg_id:
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    data = {
        "chat_id": tg_id,
        "text": "⚓ *Sunu Blue Tech* - Test GitHub Actions\n\n✅ Script OK ! Données 05h/17h UTC\n🌊 Dakar → Casamance"
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"📱 Telegram: {response.status_code}")
        if response.status_code == 200:
            print("✅ MESSAGE TELEGRAM ENVOYÉ !")
        else:
            print(f"❌ Telegram erreur: {response.text}")
    except Exception as e:
        print(f"❌ Telegram erreur: {e}")
else:
    print("⚠️ Secrets TG_TOKEN/TG_ID manquants - Pas de Telegram")

# DONNÉES TEST (toujours)
data = [{"date": "2026-01-23 03h", "zone": "Dakar", "temp": 24.5, "species": "Thon"}]
with open("public/data.json", "w") as f:
    json.dump(data, f)
print("✅ public/data.json créé")

print("🎉 SCRIPT TERMINÉ SANS ERREUR")
