# PecheurConnect 🇸🇳

## Description
PecheurConnect est une Progressive Web App (PWA) qui fournit en temps réel les données satellites pour la pêche artisanale au Sénégal : température, houle, vent, alertes critiques.  
Fonctionne offline et installable sur Android/iOS.

---

## Déploiement GitHub Pages

1. Crée un dépôt GitHub : `PecheurConnect`.
2. Pousse les fichiers : `index.html`, `manifest.json`, `sw.js`.
3. Active GitHub Pages dans les paramètres (`Settings > Pages > branch: main`).
4. URL finale : `https://<username>.github.io/PecheurConnect/`
5. Test : ouvrir sur mobile → bouton “Ajouter à l’écran d’accueil” pour installer la PWA.

---

## Mise à jour des données

- `index.html` charge `data.json` depuis GitHub Pages.
- Automatiser via **GitHub Actions** pour actualiser `data.json` toutes les 10 minutes ou 6h selon la configuration du script PecheurConnect Runner.
