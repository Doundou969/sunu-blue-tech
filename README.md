# 🌊 Sunu Blue Tech

Application made in Dakar 🇸🇳 pour la navigation et la pêche artisanale.

## 🚀 Fonctionnalités

- **Rapports automatiques** : Données de vagues, courants et température pour 5 zones côtières
- **Notifications Telegram** : Bulletins quotidiens avec cartes
- **Application Web PWA** : Accessible hors ligne
- **API REST** : Endpoints pour données dynamiques
- **Interface Flask** : Serveur web complet
- **Base de données SQLite** : Persistance des données

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
4. Pour développement : `python app.py`
5. Pour production : `python wsgi.py` (Windows) ou `gunicorn --bind 0.0.0.0:8000 wsgi:app` (Linux/Mac)

## 🌐 Utilisation

- **Page d'accueil** : `http://localhost:5000/` (dev) ou `http://yourserver:8000/` (prod)
- **À propos** : `/about`
- **Services** : `/services`
- **API données** : `/api/data`
- **Lancer script** : POST `/api/run-script`

## 📊 Workflow GitHub Actions

- Exécution automatique 2x/jour (5h et 15h UTC)
- Génération de rapports et envoi Telegram

## 🔧 Développement

Le script `script_peche.py` génère automatiquement :
- `data.json` : Données de pêche
- `sw.js` : Service Worker PWA
- `manifest.json` : Configuration PWA
- Templates HTML dans `templates/`

## 🚀 Déploiement

### Heroku
1. Créer une app Heroku
2. Déployer via Git : `heroku create`, `git push heroku main`
3. Configurer les variables d'environnement dans Heroku

### Docker
Utilisez le Dockerfile fourni pour containeriser l'app.

---

*Xam-Xam au service du Géej* ⚓