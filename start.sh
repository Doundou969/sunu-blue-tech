#!/bin/bash
# ============================================================================
# PECHEURCONNECT v2.1 - LANCEUR COMPLET
# ============================================================================
# Ce script lance le système complet PecheurConnect:
# 1. Collecte des données Copernicus
# 2. Bot Telegram interactif
# ============================================================================

set -e  # Arrêter en cas d'erreur

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de log
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERREUR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# ============================================================================
# VÉRIFICATIONS PRÉLIMINAIRES
# ============================================================================

log "Démarrage PecheurConnect v2.1..."
echo ""

# Vérifier que le fichier .env existe
if [ ! -f .env ]; then
    error "Fichier .env non trouvé!"
    warning "Créez un fichier .env basé sur .env.example"
    echo ""
    echo "Exemple:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
    exit 1
fi

log "✓ Fichier .env trouvé"

# Charger les variables d'environnement
export $(cat .env | grep -v '^#' | xargs)

# Vérifier les identifiants Copernicus
if [ -z "$COPERNICUS_USERNAME" ] || [ -z "$COPERNICUS_PASSWORD" ]; then
    error "Identifiants Copernicus manquants dans .env"
    exit 1
fi

log "✓ Identifiants Copernicus configurés"

# Vérifier le token Telegram bot
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    warning "TELEGRAM_BOT_TOKEN non configuré"
    warning "Le bot interactif ne sera pas lancé"
    BOT_ENABLED=false
else
    log "✓ Token bot Telegram configuré"
    BOT_ENABLED=true
fi

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 n'est pas installé"
    exit 1
fi

log "✓ Python 3 disponible"

# Vérifier les dépendances
log "Vérification des dépendances..."

python3 -c "import copernicusmarine" 2>/dev/null || {
    error "Module copernicusmarine manquant"
    echo "Installez avec: pip install -r requirements_bot.txt"
    exit 1
}

if [ "$BOT_ENABLED" = true ]; then
    python3 -c "import telegram" 2>/dev/null || {
        error "Module python-telegram-bot manquant"
        echo "Installez avec: pip install python-telegram-bot"
        exit 1
    }
fi

log "✓ Toutes les dépendances sont installées"
echo ""

# ============================================================================
# COLLECTE DES DONNÉES
# ============================================================================

log "========================================="
log "ÉTAPE 1: COLLECTE DES DONNÉES"
log "========================================="
echo ""

python3 script_peche_complet.py

if [ $? -ne 0 ]; then
    error "La collecte des données a échoué"
    exit 1
fi

echo ""
log "✓ Collecte des données terminée avec succès"
echo ""

# Vérifier que data.json a été créé
if [ ! -f data.json ]; then
    error "data.json n'a pas été créé"
    exit 1
fi

log "✓ Fichier data.json créé"

# ============================================================================
# LANCEMENT DU BOT TELEGRAM
# ============================================================================

if [ "$BOT_ENABLED" = true ]; then
    log "========================================="
    log "ÉTAPE 2: BOT TELEGRAM INTERACTIF"
    log "========================================="
    echo ""
    
    info "Le bot Telegram va démarrer..."
    info "Commandes disponibles:"
    echo "  /start - Démarrer"
    echo "  /conditions - Toutes les zones"
    echo "  /zone [nom] - Zone spécifique"
    echo "  /alertes - Zones dangereuses"
    echo "  /meilleures - Top 5 zones"
    echo "  /regions - Par région"
    echo "  /historique [zone] - Historique 7j"
    echo ""
    
    info "Appuyez sur Ctrl+C pour arrêter le bot"
    echo ""
    
    # Lancer le bot
    python3 bot_telegram.py
else
    log "========================================="
    log "BOT TELEGRAM NON CONFIGURÉ"
    log "========================================="
    echo ""
    warning "Le bot Telegram n'est pas configuré"
    info "Pour l'activer:"
    echo "  1. Créer un bot avec @BotFather"
    echo "  2. Ajouter TELEGRAM_BOT_TOKEN dans .env"
    echo "  3. Relancer ce script"
    echo ""
fi

log "Terminé!"
