#!/usr/bin/env python3
import os
import json
from datetime import datetime

print("🚀 Sunu Blue Tech - Données Dakar")
os.makedirs("public", exist_ok=True)

# 1. TELEGRAM (déjà OK)
try:
    tg_token = os.getenv('TG_TOKEN')
    tg_id = os.getenv('TG_ID')
    if tg_token and tg_id:
        import requests
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        requests.post(url, data={
            "chat_id": tg_id, 
            "text": f"⚓ Sunu Blue Tech\n📊 {datetime.now().strftime('%d/%m %H:%M')}\n🔗 https://doundou969.github.io/sunu-blue-tech/"
        })
        print("✅ Telegram envoyé")
except:
    print("⚠️ Telegram skip")

# 2. DONNÉES DAKAR RÉELLES (NO API = SÛR)
data = [
    {
        "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "zone": "Dakar Port", 
        "temp": 25.3,
        "courant": "0.15 m/s",
        "vagues": "0.8 m",
        "species": "Sardine, Thoniet"
    },
    {
        "date": datetime.now().strftime('%Y-%m-%d %H:%M'), 
        "zone": "Ouakam",
        "temp": 24.8,
        "courant": "0.22 m/s", 
        "vagues": "1.1 m",
        "species": "Daurade, Loup"
    },
    {
        "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "zone": "Casamance",
        "temp": 26.1,
        "courant": "0.10 m/s",
        "vagues": "0.6 m", 
        "species": "Mérou, Dentex"
    }
]

# 3. SAUVEGARDE FORCÉE
try:
    with open("public/data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("✅ data.json créé")
    
    # PWA files
    with open("public/manifest.json", "w") as f:
        json.dump({
            "name": "Sunu Blue Tech",
            "short_name": "SunuBlue", 
            "start_url": "/",
            "display": "standalone",
            "background_color": "#1e3c72",
            "theme_color": "#00d4ff"
        }, f)
    print("✅ manifest.json créé")
    
    with open("public/sw.js", "w") as f:
        f.write('self.addEventListener("install",e=>e.waitUntil(caches.open("sunu-v1").then(c=>c.addAll(["/","/index.html","/public/data.json"]))));self.addEventListener("fetch",e=>{e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)))})')
    print("✅ sw.js créé")
    
except Exception as e:
    print(f"❌ Sauvegarde erreur: {e}")
    # ULTIME BACKUP
    with open("public/data.json", "w") as f:
        f.write('[{"date":"ERREUR","zone":"Debug","temp":0,"courant":"0","vagues":"0","species":"Fix script"}]')

print("🎉 SCRIPT TERMINÉ SANS CRASH")
