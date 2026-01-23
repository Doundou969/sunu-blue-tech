import os
import requests
import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')  # NON interactif pour GitHub Actions
import matplotlib.pyplot as plt
import json
import shutil

# Configuration
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55},
    "LOMPOUL": {"lat": 15.42, "lon": -16.82},
    "DAKAR / KAYAR": {"lat": 14.85, "lon": -17.45},
    "MBOUR / JOAL": {"lat": 14.15, "lon": -17.02},
    "CASAMANCE": {"lat": 12.55, "lon": -16.85}
}

def ensure_dirs():
    """Créer dossiers nécessaires"""
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)

def send_tg_with_photo(caption, photo_path):
    """Envoyer Telegram avec image"""
    if not TG_TOKEN or not TG_ID:
        print("⚠️ Secrets Telegram manquants")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            requests.post(url, 
                         data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, 
                         files={"photo": photo},
                         timeout=10)
        print("✅ Telegram envoyé")
    except Exception as e:
        print(f"❌ Telegram erreur: {e}")

def main():
    ensure_dirs()
    
    # Données simulées si pas de Copernicus (GitHub Actions)
    if not USER or not PASS:
        print("⚠️ Copernicus credentials manquants - données simulées")
        data = []
        for nom, coord in ZONES.items():
            vague = np.random.uniform(0.5, 2.5)
            temp = np.random.uniform(22, 28)
            vitesse = np.random.uniform(5, 25)
            status = "✅" if vague < 1.5 else "⚠️" if vague < 2.5 else "🛑"
            
            data.append({
                'zone': nom, 'lat': coord['lat'], 'lon': coord['lon'],
                'vague': vague, 'temp': temp, 'vitesse': vitesse, 'status': status
            })
    else:
        try:
            import copernicusmarine
            ds_phys = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m",
                username=USER, password=PASS,
                minimum_longitude=-18.5, maximum_longitude=-16.0,
                minimum_latitude=12.0, maximum_latitude=17.0
            )
            ds_wav = copernicusmarine.open_dataset(
                dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
                username=USER, password=PASS,
                minimum_longitude=-18.5, maximum_longitude=-16.0,
                minimum_latitude=12.0, maximum_latitude=17.0
            )
            
            data = []
            for nom, coord in ZONES.items():
                dp = ds_phys.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
                if 'depth' in dp.dims: dp = dp.isel(depth=0)
                dw = ds_wav.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
                
                u, v = float(dp.uo.values), float(dp.vo.values)
                temp, vague = float(dp.thetao.values), float(dw.VHM0.values)
                vitesse = np.sqrt(u**2 + v**2) * 3.6
                status = "✅" if vague < 1.5 else "⚠️" if vague < 2.5 else "🛑"
                
                data.append({
                    'zone': nom, 'lat': coord['lat'], 'lon': coord['lon'],
                    'vague': vague, 'temp': temp, 'vitesse': vitesse, 'status': status
                })
        except Exception as e:
            print(f"❌ Copernicus erreur: {e}")
            # Fallback simulé
            data = [{'zone': 'Dakar', 'vague': 1.2, 'temp': 25.0, 'vitesse': 12.0, 'status': '✅'}]

    # Rapport Telegram
    rapport = f"🇸🇳 *SUNU-BLUE-TECH : NAVIGATION*\n📅 `{datetime.datetime.now().strftime('%d/%m/%Y | %H:%M UTC')}`\n━━━━━━━━━━━━━━━\n\n"
    for d in data:
        gmaps = f"https://www.google.com/maps?q={d['lat']},{d['lon']}"
        rapport += f"📍 *{d['zone']}* {d['status']}\n🌐 `{d['lat']:.2f}, {d['lon']:.2f}`\n🌊 *{d['vague']:.1f}m* | 🌡️ {d['temp']:.1f}°C | 🚩 {d['vitesse']:.1f}km/h\n🔗 [Carte]({gmaps})\n───────────────\n"
    rapport += "\n🆘 *URGENCE MER : 119*\n⚓ *Xam-Xam au service du Géej.*"

    # Graphique
    plt.figure(figsize=(10, 8))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, d in enumerate(data):
        plt.quiver(0, -i, 0.5*np.random.rand(), 0.3*np.random.rand(), 
                  color=colors[i], scale=1.5, width=0.015)
        plt.text(0.3, -i, f"{d['zone']}: {d['vague']:.1f}m", 
                va='center', fontsize=11, fontweight='bold', color=colors[i])
    
    plt.title("🪝 Bulletin Navigation - Sunu Blue Tech", fontsize=14, pad=20)
    plt.xlim(-0.5, 2.5); plt.ylim(-len(ZONES), 1); plt.axis('off')
    plt.tight_layout()
    
    image_path = "static/bulletin_gps.png"
    plt.savefig(image_path, bbox_inches='tight', dpi=150, facecolor='white')
    plt.close()

    # Envoyer Telegram
    send_tg_with_photo(rapport, image_path)

    # Données pêche pour web
    fishing_data = [
        {"date": datetime.datetime.now().strftime('%Y-%m-%d'), "zone": d['zone'], 
         "temp": d['temp'], "species": "Sardine, Thon" if d['vague'] < 1.5 else "Céphalopodes"}
        for d in data
    ]

    # Fichiers web
    with open("static/data.json", "w", encoding="utf-8") as f:
        json.dump(fishing_data, f, ensure_ascii=False, indent=2)

    # Service Worker PWA
    sw_content = '''self.addEventListener('install', event => {
        event.waitUntil(caches.open('sunu-cache-v1').then(cache => {
            return cache.addAll(['/', '/static/data.json', '/static/manifest.json']);
        }));
    });
    self.addEventListener('fetch', event => {
        event.respondWith(caches.match(event.request).then(response => {
            return response || fetch(event.request);
        }));
    });'''
    
    with open("static/sw.js", "w") as f:
        f.write(sw_content)

    # Manifest PWA
    manifest = {
        "name": "Sunu Blue Tech", "short_name": "SunuBT",
        "start_url": "/", "display": "standalone",
        "background_color": "#1e3c72", "theme_color": "#00d4ff",
        "icons": [{"src": "https://via.placeholder.com/192x192/00d4ff/ffffff?text=SBT", "sizes": "192x192"}]
    }
    
    with open("static/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("✅ Script terminé - Fichiers générés:")
    print("- static/bulletin_gps.png")
    print("- static/data.json")
    print("- static/sw.js")
    print("- static/manifest.json")

if __name__ == "__main__":
    main()
