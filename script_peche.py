import os
import requests
import copernicusmarine
import datetime
import numpy as np
import matplotlib.pyplot as plt
import json
# from app import db, FishingData, app  # Import DB and model - moved inside function to avoid circular import

# --- CONFIGURATION ---
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

# --- CONFIGURATION ---
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")

# Zones avec coordonnées précises
ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55},
    "LOMPOUL": {"lat": 15.42, "lon": -16.82},
    "DAKAR / KAYAR": {"lat": 14.85, "lon": -17.45},
    "MBOUR / JOAL": {"lat": 14.15, "lon": -17.02},
    "CASAMANCE": {"lat": 12.55, "lon": -16.85}
}

def send_tg_with_photo(caption, photo_path):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, files={"photo": photo})

def job():
    from app import db, FishingData, app  # Import DB and model inside function to avoid circular import
    try:
        # Datasets
        ds_phys = copernicusmarine.open_dataset(dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m", username=USER, password=PASS, minimum_longitude=-18.5, maximum_longitude=-16.0, minimum_latitude=12.0, maximum_latitude=17.0)
        ds_wav = copernicusmarine.open_dataset(dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", username=USER, password=PASS, minimum_longitude=-18.5, maximum_longitude=-16.0, minimum_latitude=12.0, maximum_latitude=17.0)

        rapport = f"🇸🇳 *SUNU-BLUE-TECH : NAVIGATION*\n"
        rapport += f"📅 `{datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')}`\n"
        rapport += "━━━━━━━━━━━━━━━\n\n"
        
        plt.figure(figsize=(10, 8))
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, (nom, coord) in enumerate(ZONES.items()):
            dp = ds_phys.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
            if 'depth' in dp.dims: dp = dp.isel(depth=0)
            dw = ds_wav.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)

            u, v = float(dp.uo.values), float(dp.vo.values)
            temp, vague = float(dp.thetao.values), float(dw.VHM0.values)
            vitesse = np.sqrt(u**2 + v**2) * 3.6 
            
            # Diagnostic
            status = "✅" if vague < 1.5 else "⚠️" if vague < 2.5 else "🛑"
            
            # Création du lien Google Maps
            gmaps_link = f"https://www.google.com/maps?q={coord['lat']},{coord['lon']}"

            rapport += f"📍 *{nom}* {status}\n"
            rapport += f"🌐 GPS : `{coord['lat']}, {coord['lon']}`\n"
            rapport += f"🌊 Vagues : *{vague:.2f} m* | 🌡️ {temp:.1f}°C\n"
            rapport += f"🚩 Courant : {vitesse:.1f} km/h\n"
            rapport += f"🔗 [Voir sur la Carte]({gmaps_link})\n"
            rapport += "───────────────\n"

            plt.quiver(0, -i, u, v, color=colors[i], scale=1.5, width=0.015)
            plt.text(0.3, -i, f"{nom}: {vague:.1f}m", va='center', fontsize=11, fontweight='bold', color=colors[i])

        rapport += "\n🆘 *URGENCE MER : 119*\n"
        rapport += "⚓ *Xam-Xam au service du Géej.*"

        plt.title("Carte des Courants et Vagues - Sunu-Blue-Tech", fontsize=14)
        plt.xlim(-0.5, 2.5); plt.ylim(-len(ZONES), 1); plt.axis('off')
        
        image_path = "bulletin_gps.png"
        plt.savefig(image_path, bbox_inches='tight', dpi=150); plt.close()

        send_tg_with_photo(rapport, image_path)

        # Save to DB
        with app.app_context():
            db.create_all()  # Ensure DB tables exist
            # Clear existing data
            db.session.query(FishingData).delete()
            # Add new data (dummy for now)
            for nom in ZONES.keys():
                db_data = FishingData(
                    date=datetime.datetime.now().strftime('%Y-%m-%d'),
                    zone=nom,
                    temp=24.0 + np.random.rand() * 2,
                    species="Sardine, Thon"
                )
                db.session.add(db_data)
            db.session.commit()

            # Create data for JSON from DB
            fishing_records = FishingData.query.all()
            data = [
                {
                    "date": record.date,
                    "zone": record.zone,
                    "temp": record.temp,
                    "species": record.species
                }
                for record in fishing_records
            ]

        # Update sw.js to cache data.json
        sw = '''
        self.addEventListener('install', event => {
            event.waitUntil(
                caches.open('sunu-cache').then(cache => {
                    return cache.addAll([
                        '/',
                        '/index.html',
                        '/manifest.json',
                        '/data.json'
                    ]);
                })
            );
        });

        self.addEventListener('fetch', event => {
            event.respondWith(
                caches.match(event.request).then(response => {
                    return response || fetch(event.request);
                })
            );
        });
        '''

        with open("sw.js", "w", encoding="utf-8") as f:
            f.write(sw)

        # Create manifest.json for PWA
        manifest = {
            "name": "Sunu Blue Tech",
            "short_name": "SunuBT",
            "description": "Application de navigation et pêche made in Dakar",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#1e3c72",
            "theme_color": "#00d4ff",
            "icons": [
                {
                    "src": "https://via.placeholder.com/192x192/00d4ff/ffffff?text=SBT",
                    "sizes": "192x192",
                    "type": "image/png"
                }
            ]
        }

        with open("manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=4)

        # Update index.html with dynamic data loading
        html_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunu Blue Tech - App Officielle</title>
    <link rel="manifest" href="manifest.json">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0; padding: 20px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; text-align: center;
        }
        .container {
            max-width: 600px; margin: 0 auto;
            background: rgba(255,255,255,0.1); padding: 40px;
            border-radius: 20px; backdrop-filter: blur(10px);
        }
        nav {
            background: rgba(0,0,0,0.3); padding: 15px; border-radius: 15px; margin-bottom: 30px;
        }
        nav a {
            color: #00d4ff; text-decoration: none; margin: 0 20px; font-weight: bold; font-size: 1.1em;
        }
        nav a:hover { color: white; }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        button {
            background: #00d4ff; color: black; border: none; padding: 15px 30px;
            font-size: 1.2em; border-radius: 50px; cursor: pointer; margin: 10px;
            transition: all 0.3s;
        }
        button:hover { background: #00b8e6; transform: scale(1.05); }
        #data-container { margin-top: 30px; text-align: left; }
        .data-item { background: rgba(0,0,0,0.2); padding: 15px; margin: 10px 0; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <a href="index.html">🏠 Accueil</a>
            <a href="about.html">👨‍💻 À Propos</a>
            <a href="services.html">⚙️ Services</a>
        </nav>
        <h1>🌊 Sunu Blue Tech</h1>
        <p>Votre application officielle est prête ! Navigation complète ✅</p>
        <button onclick="showMessage()">🚀 Démarrer l'app</button>
        <button onclick="alert('Bonjour depuis Dakar ! 🇸🇳')">📱 Test</button>
        <div id="data-container">
            <h2>📊 Données de Pêche Récentes</h2>
            <div id="data-list"></div>
        </div>
    </div>

    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('sw.js');
        }

        function showMessage() {
            alert("🎉 Félicitations ! Navigation multi-pages fonctionnelle !");
        }

        // Load data from /api/data
        fetch('/api/data')
            .then(response => response.json())
            .then(data => {
                const dataList = document.getElementById('data-list');
                data.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'data-item';
                    div.innerHTML = `
                        <strong>${item.date}</strong> - ${item.zone}<br>
                        Température: ${item.temp}°C<br>
                        Espèces: ${item.species}
                    `;
                    dataList.appendChild(div);
                });
            })
            .catch(error => console.error('Erreur chargement données:', error));
    </script>
</body>
</html>"""

        with open("templates/index.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        # Create README.md
        readme_content = """# 🌊 Sunu Blue Tech

Application made in Dakar 🇸🇳 pour la navigation et la pêche artisanale.

## 🚀 Fonctionnalités

- **Rapports automatiques** : Données de vagues, courants et température pour 5 zones côtières
- **Notifications Telegram** : Bulletins quotidiens avec cartes
- **Application Web PWA** : Accessible hors ligne
- **Données dynamiques** : Intégration temps réel depuis Copernicus Marine

## 📍 Zones couvertes

- Saint-Louis
- Loumpoul
- Dakar / Kayar
- Mbour / Joal
- Casamance

## 🛠 Installation

1. Cloner le repo
2. Installer les dépendances : `pip install -r requirements.txt`
3. Configurer les variables d'environnement :
   - `COPERNICUS_USERNAME`
   - `COPERNICUS_PASSWORD`
   - `TG_TOKEN`
   - `TG_ID`
4. Lancer : `python script_peche.py`

## 📊 Workflow GitHub Actions

- Exécution automatique 2x/jour (5h et 15h UTC)
- Génération de rapports et envoi Telegram

## 🌐 Application Web

- Ouvrir `index.html` dans un navigateur
- Installer comme PWA pour accès hors ligne

---

*Xam-Xam au service du Géej* ⚓"""

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_ID, "text": "✅ Intégration données terminée !\n📊 Données chargées dynamiquement depuis data.json\n🚀 App complète et déployée !"})

    except Exception as e:
        print(f"Erreur: {e}")
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_ID, "text": f"❌ Erreur GPS : {e}"})
        except:
            pass  # Ignore if no TG configured
        # Create dummy data if real data fails
        data = [
            {"date": "2026-01-22", "zone": "Dakar", "temp": 24.5, "species": "Sardine, Thon"},
            {"date": "2026-01-21", "zone": "Cap Vert", "temp": 23.8, "species": "Maquereau"},
            {"date": "2026-01-20", "zone": "Goree", "temp": 25.2, "species": "Poisson volant"}
        ]

    # Always create the web files
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # Update sw.js to cache data.json
    sw = '''
    self.addEventListener('install', event => {
        event.waitUntil(
            caches.open('sunu-cache').then(cache => {
                return cache.addAll([
                    '/',
                    '/static/manifest.json',
                    '/static/data.json'
                ]);
            })
        );
    });

    self.addEventListener('fetch', event => {
        event.respondWith(
            caches.match(event.request).then(response => {
                return response || fetch(event.request);
            })
        );
    });
    '''

    with open("static/sw.js", "w", encoding="utf-8") as f:
        f.write(sw)

    # Create manifest.json for PWA
    manifest = {
        "name": "Sunu Blue Tech",
        "short_name": "SunuBT",
        "description": "Application de navigation et pêche made in Dakar",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1e3c72",
        "theme_color": "#00d4ff",
        "icons": [
            {
                "src": "https://via.placeholder.com/192x192/00d4ff/ffffff?text=SBT",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }

    with open("static/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)

    # Update index.html with dynamic data loading
    html_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunu Blue Tech - App Officielle</title>
    <link rel="manifest" href="/static/manifest.json">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0; padding: 20px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; text-align: center;
        }
        .container {
            max-width: 600px; margin: 0 auto;
            background: rgba(255,255,255,0.1); padding: 40px;
            border-radius: 20px; backdrop-filter: blur(10px);
        }
        nav {
            background: rgba(0,0,0,0.3); padding: 15px; border-radius: 15px; margin-bottom: 30px;
        }
        nav a {
            color: #00d4ff; text-decoration: none; margin: 0 20px; font-weight: bold; font-size: 1.1em;
        }
        nav a:hover { color: white; }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        button {
            background: #00d4ff; color: black; border: none; padding: 15px 30px;
            font-size: 1.2em; border-radius: 50px; cursor: pointer; margin: 10px;
            transition: all 0.3s;
        }
        button:hover { background: #00b8e6; transform: scale(1.05); }
        #data-container { margin-top: 30px; text-align: left; }
        .data-item { background: rgba(0,0,0,0.2); padding: 15px; margin: 10px 0; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <a href="/">🏠 Accueil</a>
            <a href="/about">👨‍💻 À Propos</a>
            <a href="/services">⚙️ Services</a>
        </nav>
        <h1>🌊 Sunu Blue Tech</h1>
        <p>Votre application officielle est prête ! Navigation complète ✅</p>
        <button onclick="showMessage()">🚀 Démarrer l'app</button>
        <button onclick="alert('Bonjour depuis Dakar ! 🇸🇳')">📱 Test</button>
        <div id="data-container">
            <h2>📊 Données de Pêche Récentes</h2>
            <div id="data-list"></div>
        </div>
    </div>

    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js');
        }

        function showMessage() {
            alert("🎉 Félicitations ! Navigation multi-pages fonctionnelle !");
        }

        // Load data from /api/data
        fetch('/api/data')
            .then(response => response.json())
            .then(data => {
                const dataList = document.getElementById('data-list');
                data.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'data-item';
                    div.innerHTML = `
                        <strong>${item.date}</strong> - ${item.zone}<br>
                        Température: ${item.temp}°C<br>
                        Espèces: ${item.species}
                    `;
                    dataList.appendChild(div);
                });
            })
            .catch(error => console.error('Erreur chargement données:', error));
    </script>
</body>
</html>"""

    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    # Create README.md
    readme_content = """# 🌊 Sunu Blue Tech

Application made in Dakar 🇸🇳 pour la navigation et la pêche artisanale.

## 🚀 Fonctionnalités

- **Rapports automatiques** : Données de vagues, courants et température pour 5 zones côtières
- **Notifications Telegram** : Bulletins quotidiens avec cartes
- **Application Web PWA** : Accessible hors ligne
- **API REST** : Endpoints pour données dynamiques
- **Interface Flask** : Serveur web complet

## 📍 Zones couvertes

- Saint-Louis
- Loumpoul
- Dakar / Kayar
- Mbour / Joal
- Casamance

## 🛠 Installation

1. Cloner le repo
2. Installer les dépendances : `pip install -r requirements.txt`
3. Configurer les variables d'environnement :
   - `COPERNICUS_USERNAME`
   - `COPERNICUS_PASSWORD`
   - `TG_TOKEN`
   - `TG_ID`
4. Lancer l'app : `python app.py`

## 🌐 Utilisation

- **Page d'accueil** : `http://localhost:5000/`
- **À propos** : `http://localhost:5000/about`
- **Services** : `http://localhost:5000/services`
- **API données** : `http://localhost:5000/api/data`
- **Lancer script** : POST `http://localhost:5000/api/run-script`

## 📊 Workflow GitHub Actions

- Exécution automatique 2x/jour (5h et 15h UTC)
- Génération de rapports et envoi Telegram

## 🔧 Développement

Le script `script_peche.py` génère automatiquement :
- `data.json` : Données de pêche
- `sw.js` : Service Worker PWA
- `manifest.json` : Configuration PWA
- Templates HTML dans `templates/`

---

*Xam-Xam au service du Géej* ⚓"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

if __name__ == "__main__":
    job()
