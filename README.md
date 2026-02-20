# 🌊 PecheurConnect v3.0

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-green.svg)](https://github.com/features/actions)

**Système de sécurité maritime en temps réel pour les pêcheurs sénégalais** 🇸🇳

---

## 📋 Table des matières

- [Présentation](#-présentation)
- [Fonctionnalités](#-fonctionnalités)
- [Démo en ligne](#-démo-en-ligne)
- [Technologies](#️-technologies)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Utilisation](#-utilisation)
- [Architecture](#️-architecture)
- [API](#-api)
- [Contribution](#-contribution)
- [Roadmap](#️-roadmap)
- [Licence](#-licence)
- [Contact](#-contact)

---

## 🎯 Présentation

**PecheurConnect** est une plateforme web progressive (PWA) qui fournit des informations océanographiques et météorologiques en temps réel pour **18 zones de pêche** le long des **700 km de côtes sénégalaises**.

### Problème résolu

Chaque année, des centaines de pêcheurs artisanaux sénégalais perdent la vie en mer faute d'informations météorologiques accessibles. PecheurConnect démocratise l'accès aux données maritimes pour sauver des vies.

### Impact

- ✅ **18 zones surveillées** de Saint-Louis à la Casamance
- ✅ **Mise à jour toutes les 6h** automatiquement
- ✅ **Gratuit et open source**
- ✅ **Accessible hors ligne** (PWA)
- ✅ **Multilingue** (Français, Wolof, English)

---

## ✨ Fonctionnalités

### 🗺️ Carte Interactive
- Visualisation en temps réel des 18 zones
- Markers avec hauteur des vagues par couleur
- Clusters intelligents pour zones proches
- Filtrage par région
- Recherche de zones
- Géolocalisation utilisateur

### 📊 Historique & Statistiques
- Graphiques 7 jours (vagues, température, vent)
- Identification du meilleur/pire jour
- Tendances (hausse/baisse/stable)
- Tableau des 30 dernières mesures
- Statistiques par zone

### 🎯 Comparateur Intelligent
- Recommandation des meilleures zones
- Score 0-100 par zone
- Calcul de distance depuis position utilisateur
- Filtres personnalisables (région, distance, priorité)
- Top 10 des zones recommandées

### 🔔 Alertes Push
- Notifications en temps réel
- Alertes DANGER (conditions dangereuses)
- Alertes PRUDENCE (dégradation)
- Alertes CONDITIONS OPTIMALES
- Surveillance zones personnalisables
- Heures silencieuses configurables

### 📄 Export de Données
- Export PDF (rapports complets avec graphiques)
- Export CSV (pour Excel/analyse)
- Export JSON (pour développeurs)
- Export Image (pour partage réseaux sociaux)
- Données historiques 7-30 jours

### 🏛️ Dashboard Admin
- Vue d'ensemble nationale
- KPIs en temps réel (zones sûres, alertes)
- Graphiques agrégés par région
- Tableau détaillé de toutes les zones
- Auto-refresh toutes les 5 minutes

### 🌐 Multilingue
- **Français** (langue principale)
- **Wolof** (langue nationale)
- **English** (international)
- Traduction complète de l'interface
- Détection automatique de la langue

### 📱 PWA (Progressive Web App)
- Installable sur mobile et desktop
- Fonctionne hors ligne
- Notifications push natives
- Cache intelligent des données
- Mode offline avec page dédiée

---

## 🌐 Démo en ligne

🔗 **Site web** : [https://doundou969.github.io/sunu-blue-tech/](https://doundou969.github.io/sunu-blue-tech/)

### Pages disponibles :
- 🗺️ [Carte principale](https://doundou969.github.io/sunu-blue-tech/index.html)
- 📊 [Historique](https://doundou969.github.io/sunu-blue-tech/history.html)
- 🎯 [Comparateur](https://doundou969.github.io/sunu-blue-tech/comparator.html)
- 📄 [Export](https://doundou969.github.io/sunu-blue-tech/export.html)
- 🔔 [Alertes](https://doundou969.github.io/sunu-blue-tech/alerts-settings.html)
- 🏛️ [Admin](https://doundou969.github.io/sunu-blue-tech/admin.html)

---

## 🛠️ Technologies

### Frontend
- **HTML5** / **CSS3** / **JavaScript ES6+**
- **Leaflet.js** - Cartographie interactive
- **Chart.js** - Graphiques et visualisations
- **Service Worker** - Mode offline et cache
- **Web Notifications API** - Alertes push

### Backend
- **Python 3.11+**
- **Copernicus Marine Service** - Données océanographiques
- **OpenWeather API** - Météo en temps réel
- **GitHub Actions** - Automatisation CI/CD

### Hébergement
- **GitHub Pages** - Hébergement gratuit
- **GitHub Actions** - Exécution automatique toutes les 6h

---

## 🚀 Installation

### Prérequis
- Python 3.11+
- pip
- Git
- Compte [Copernicus Marine](https://marine.copernicus.eu/)
- Clé API [OpenWeather](https://openweathermap.org/api) (gratuit)

### Installation locale

```bash
# 1. Cloner le repository
git clone https://github.com/doundou969/sunu-blue-tech.git
cd sunu-blue-tech

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# 4. Lancer le script
python script_peche.py

# 5. Ouvrir index.html dans un navigateur
open index.html  # macOS
start index.html  # Windows
xdg-open index.html  # Linux
```

---

## ⚙️ Configuration

### Variables d'environnement

Créez un fichier `.env` à la racine :

```env
# Copernicus Marine (OBLIGATOIRE)
COPERNICUS_USERNAME=votre_username
COPERNICUS_PASSWORD=votre_password

# OpenWeather (RECOMMANDÉ - Gratuit jusqu'à 1000 appels/jour)
OPENWEATHER_API_KEY=votre_clé_api

# Telegram Bot (OPTIONNEL)
TG_TOKEN=votre_bot_token
TG_ID=votre_chat_id

# WorldTides (OPTIONNEL - 50$/mois)
WORLDTIDES_API_KEY=votre_clé_worldtides
```

### GitHub Secrets

Pour le déploiement automatique, ajoutez ces secrets dans **Settings → Secrets → Actions** :

- `COPERNICUS_USERNAME`
- `COPERNICUS_PASSWORD`
- `OPENWEATHER_API_KEY`
- `TG_TOKEN` (optionnel)
- `TG_ID` (optionnel)

---

## 📖 Utilisation

### Script Python

```bash
# Exécution unique
python script_peche.py

# Le script va :
# 1. Se connecter à Copernicus Marine
# 2. Récupérer données pour 18 zones
# 3. Interroger OpenWeather pour la météo
# 4. Générer data.json
# 5. Sauvegarder historique dans logs/
# 6. Générer statistiques dans logs/stats/
# 7. Envoyer notification Telegram (optionnel)
```

### Automatisation (GitHub Actions)

Le workflow `.github/workflows/update.yml` s'exécute automatiquement :
- **Toutes les 6 heures** (00:00, 06:00, 12:00, 18:00 UTC)
- **Manuellement** depuis l'onglet Actions

### Interface Web

```bash
# Avec serveur HTTP simple (Python)
python -m http.server 8000

# Ouvrir dans navigateur
http://localhost:8000
```

---

## 🏗️ Architecture

```
sunu-blue-tech/
├── index.html                 # Carte principale
├── history.html               # Historique 7 jours
├── comparator.html            # Comparateur zones
├── export.html                # Export données
├── alerts-settings.html       # Config alertes
├── admin.html                 # Dashboard admin
├── offline.html               # Page hors ligne
├── manifest.json              # PWA manifest
├── sw.js                      # Service Worker
├── script_peche.py            # Script Python principal
├── requirements.txt           # Dépendances Python
├── translations.js            # Système multilingue
├── alerts.js                  # Système alertes
├── predictions.js             # Prévisions ML
├── data.json                  # Données actuelles (généré)
├── logs/
│   ├── history/               # Historique quotidien JSON
│   ├── stats/                 # Statistiques par zone
│   └── backups/               # Backups horodatés
└── .github/workflows/
    └── update.yml             # Automatisation CI/CD
```

---

## 🔌 API

### Endpoints disponibles

Toutes les données sont accessibles via JSON statique :

#### Données actuelles
```
GET https://doundou969.github.io/sunu-blue-tech/data.json
```

Retourne les données en temps réel des 18 zones.

#### Statistiques globales
```
GET https://doundou969.github.io/sunu-blue-tech/logs/stats/all_zones.json
```

Retourne les statistiques 7 jours de toutes les zones.

#### Statistiques par zone
```
GET https://doundou969.github.io/sunu-blue-tech/logs/stats/{zone_name}.json
```

Exemple : `rufisque.json`, `dakar_yoff.json`

### Format des données

```json
{
  "zone": "RUFISQUE",
  "region": "Dakar",
  "lat": 14.72,
  "lon": -17.28,
  "v_now": 1.15,
  "t_now": 18.7,
  "c_now": 0.05,
  "wind_speed": 3.1,
  "visibility": 10,
  "weather_desc": "ciel dégagé",
  "index": "🐟🐟🐟 EXCELLENT",
  "safety": "🟢 SÛR",
  "safety_level": "safe",
  "fish_level": "excellent",
  "date": "20/02 16:33"
}
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! 

### Comment contribuer

1. **Fork** le projet
2. Créer une branche (`git checkout -b feature/amelioration`)
3. Commit (`git commit -m 'Ajout fonctionnalité X'`)
4. Push (`git push origin feature/amelioration`)
5. Ouvrir une **Pull Request**

### Guidelines

- Suivre le style de code existant
- Ajouter des tests si applicable
- Mettre à jour la documentation
- Commiter avec des messages clairs

---

## 🗺️ Roadmap

### ✅ Version 3.0 (Actuelle)
- [x] 18 zones surveillées
- [x] Historique 7 jours
- [x] Comparateur intelligent
- [x] Alertes push
- [x] Multilingue (FR/WO/EN)
- [x] Export données (PDF/CSV/JSON/Image)
- [x] Dashboard admin
- [x] PWA installable
- [x] Mode offline

### 🚧 Version 3.1 (Q2 2026)
- [ ] Prévisions 72h
- [ ] Données marées (WorldTides)
- [ ] Zones personnalisables par GPS
- [ ] Système de signalement communautaire
- [ ] Base de données espèces de poissons

### 🔮 Version 4.0 (Q3-Q4 2026)
- [ ] App mobile native (iOS/Android)
- [ ] Intégration autorités (DPM, Marine Nationale)
- [ ] Système SOS intégré
- [ ] ML avancé (prédictions IA)
- [ ] Expansion régionale (Mauritanie, Gambie)

---

## 📄 Licence

Ce projet est sous licence **MIT**. Voir [LICENSE](LICENSE) pour plus de détails.

```
MIT License

Copyright (c) 2026 PecheurConnect

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 📞 Contact

### Équipe PecheurConnect

- 📧 **Email** : contact@pecheurconnect.sn
- 📱 **WhatsApp** : [+221 77 702 08 18](https://wa.me/221777020818)
- 🐙 **GitHub** : [@doundou969](https://github.com/doundou969)
- 🌐 **Site web** : [doundou969.github.io/sunu-blue-tech](https://doundou969.github.io/sunu-blue-tech/)

### Partenaires

- 🌊 **Copernicus Marine Service** - Données océanographiques
- ☁️ **OpenWeather** - Données météorologiques
- 🇸🇳 **Ministère de la Pêche du Sénégal** - Support institutionnel

---

## 🙏 Remerciements

Merci à tous ceux qui ont contribué à rendre la mer plus sûre pour les pêcheurs sénégalais :

- Équipe Copernicus Marine pour les données océanographiques
- OpenWeather pour l'API météo gratuite
- GitHub pour l'hébergement et l'automatisation
- La communauté des pêcheurs sénégalais pour leurs retours

---

## 📊 Statistiques du Projet

- **18 zones** surveillées
- **700 km** de côtes couvertes
- **6 régions** maritimes
- **Mise à jour** toutes les 6h
- **3 langues** supportées
- **100% gratuit** et open source

---

<div align="center">

**🌊 PecheurConnect - Pour une pêche plus sûre au Sénégal 🇸🇳**

*Jëf-jël ak jàmm !* (Travail et Paix en Wolof)

[⭐ Star le projet](https://github.com/doundou969/sunu-blue-tech) · [🐛 Reporter un bug](https://github.com/doundou969/sunu-blue-tech/issues) · [💡 Suggérer une fonctionnalité](https://github.com/doundou969/sunu-blue-tech/issues)

</div>
