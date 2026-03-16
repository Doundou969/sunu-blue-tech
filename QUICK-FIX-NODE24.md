# ⚡ MIGRATION NODE.JS 24 - GUIDE RAPIDE

**Temps requis :** 5 minutes  
**Difficulté :** ⭐ Facile  
**Impact :** Zero downtime

---

## 🎯 OBJECTIF

Éliminer les warnings GitHub Actions :
```
⚠️ Node.js 20 actions are deprecated
```

---

## ✅ 3 ÉTAPES SIMPLES

### **ÉTAPE 1 : Ajouter la variable d'environnement** (2 min)

Dans **CHAQUE** fichier `.github/workflows/*.yml`, ajoutez au début :

```yaml
env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"
```

**Exemple complet :**
```yaml
name: CI - Tests

on:
  push:
    branches: [main]

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"  # ✅ Ajouter cette ligne

jobs:
  test:
    runs-on: ubuntu-latest
    
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"  # ✅ Redéfinir au niveau job
    
    steps:
      - uses: actions/checkout@v4
      # ... reste du workflow
```

---

### **ÉTAPE 2 : Vérifier avec le script** (1 min)

```bash
# Rendre le script exécutable
chmod +x verify-node24.sh

# Lancer la vérification
./verify-node24.sh
```

**Résultat attendu :**
```
✅ TOUS LES WORKFLOWS SONT COMPATIBLES NODE.JS 24 !
```

---

### **ÉTAPE 3 : Commit et Push** (2 min)

```bash
# Créer une branche
git checkout -b fix/node24-warnings

# Commit
git add .github/workflows/
git commit -m "ci: Fix Node.js 20 deprecation warnings

Add FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true to all workflows"

# Push
git push -u origin fix/node24-warnings
```

---

## 🧪 VÉRIFICATION

**Avant :**
```
⚠️ Warning: Node.js 20 actions are deprecated
⚠️ actions/checkout@v4
⚠️ actions/setup-python@v5
```

**Après :**
```
✅ Running with Node.js 24
✅ No deprecation warnings
```

---

## 📋 WORKFLOWS À MODIFIER

Modifiez ces fichiers :
- [ ] `.github/workflows/ci.yml`
- [ ] `.github/workflows/cd.yml`
- [ ] `.github/workflows/scheduled.yml`
- [ ] `.github/workflows/pages.yml` (si existe)
- [ ] Tous les autres workflows `.yml`

---

## 🚀 FICHIERS PRÉ-CONFIGURÉS

J'ai créé des versions corrigées :
- ✅ `ci-node24.yml` → Renommer en `ci.yml`
- ✅ `scheduled-node24.yml` → Renommer en `scheduled.yml`
- ✅ `pages.yml` → Déjà prêt

**Copie rapide :**
```bash
cp ci-node24.yml .github/workflows/ci.yml
cp scheduled-node24.yml .github/workflows/scheduled.yml
```

---

## ❓ FAQ

**Q: Dois-je mettre à jour mes actions ?**  
A: Non, `actions/checkout@v4` et `actions/setup-python@v5` sont déjà compatibles. Il suffit d'ajouter la variable.

**Q: Ça va casser mes workflows ?**  
A: Non, c'est 100% rétrocompatible.

**Q: C'est urgent ?**  
A: Oui si vous voulez éliminer les warnings. Obligatoire avant le 2 juin 2026.

---

## 📞 BESOIN D'AIDE ?

Si les warnings persistent après migration :
1. Vérifiez que la variable est au niveau `env:` global
2. Vérifiez qu'elle est aussi au niveau `job`
3. Lancez `./verify-node24.sh`

---

**Migration en 5 minutes. Warnings éliminés. Projet à jour ! ✅**
