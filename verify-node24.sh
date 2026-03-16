#!/bin/bash
# ============================================================================
# SCRIPT DE VÉRIFICATION - Node.js 24 Migration
# ============================================================================
# Vérifie que tous les workflows sont compatibles Node.js 24
# Usage: ./verify-node24.sh
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 VÉRIFICATION MIGRATION NODE.JS 24"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier existence dossier workflows
if [ ! -d ".github/workflows" ]; then
    echo -e "${RED}❌ Dossier .github/workflows non trouvé${NC}"
    exit 1
fi

TOTAL_WORKFLOWS=0
COMPATIBLE_WORKFLOWS=0
WARNINGS=()

# Vérifier chaque workflow
for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
    if [ -f "$workflow" ]; then
        TOTAL_WORKFLOWS=$((TOTAL_WORKFLOWS + 1))
        FILENAME=$(basename "$workflow")
        
        echo -e "${BLUE}📄 Vérification: $FILENAME${NC}"
        
        # Vérifier présence de FORCE_JAVASCRIPT_ACTIONS_TO_NODE24
        if grep -q "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24.*true" "$workflow"; then
            echo -e "   ${GREEN}✅ Variable Node.js 24 présente${NC}"
            COMPATIBLE_WORKFLOWS=$((COMPATIBLE_WORKFLOWS + 1))
        else
            echo -e "   ${RED}❌ Variable Node.js 24 ABSENTE${NC}"
            WARNINGS+=("$FILENAME: Variable FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 manquante")
        fi
        
        # Vérifier versions des actions
        echo "   🔍 Vérification des versions d'actions..."
        
        # actions/checkout
        if grep -q "actions/checkout@v4" "$workflow"; then
            echo -e "   ${GREEN}✅ actions/checkout@v4${NC}"
        fi
        
        # actions/setup-python
        if grep -q "actions/setup-python@v5" "$workflow"; then
            echo -e "   ${GREEN}✅ actions/setup-python@v5${NC}"
        elif grep -q "actions/setup-python@v4" "$workflow"; then
            echo -e "   ${YELLOW}⚠️  actions/setup-python@v4 (recommandé: v5)${NC}"
            WARNINGS+=("$FILENAME: actions/setup-python@v4 devrait être v5")
        fi
        
        # actions/upload-artifact
        if grep -q "actions/upload-artifact@v4" "$workflow"; then
            echo -e "   ${GREEN}✅ actions/upload-artifact@v4${NC}"
        elif grep -q "actions/upload-artifact@v3" "$workflow"; then
            echo -e "   ${YELLOW}⚠️  actions/upload-artifact@v3 (recommandé: v4)${NC}"
            WARNINGS+=("$FILENAME: actions/upload-artifact@v3 devrait être v4")
        fi
        
        # actions/configure-pages
        if grep -q "actions/configure-pages@v5" "$workflow"; then
            echo -e "   ${GREEN}✅ actions/configure-pages@v5${NC}"
        elif grep -q "actions/configure-pages@v4" "$workflow"; then
            echo -e "   ${YELLOW}⚠️  actions/configure-pages@v4 (recommandé: v5)${NC}"
            WARNINGS+=("$FILENAME: actions/configure-pages@v4 devrait être v5")
        fi
        
        # codecov/codecov-action
        if grep -q "codecov/codecov-action@v5" "$workflow"; then
            echo -e "   ${GREEN}✅ codecov/codecov-action@v5${NC}"
        elif grep -q "codecov/codecov-action@v4" "$workflow"; then
            echo -e "   ${YELLOW}⚠️  codecov/codecov-action@v4 (recommandé: v5)${NC}"
            WARNINGS+=("$FILENAME: codecov/codecov-action@v4 devrait être v5")
        fi
        
        # docker/build-push-action
        if grep -q "docker/build-push-action@v6" "$workflow"; then
            echo -e "   ${GREEN}✅ docker/build-push-action@v6${NC}"
        elif grep -q "docker/build-push-action@v5" "$workflow"; then
            echo -e "   ${YELLOW}⚠️  docker/build-push-action@v5 (recommandé: v6)${NC}"
            WARNINGS+=("$FILENAME: docker/build-push-action@v5 devrait être v6")
        fi
        
        echo ""
    fi
done

# Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RÉSUMÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Workflows analysés: $TOTAL_WORKFLOWS"
echo "Compatibles Node.js 24: $COMPATIBLE_WORKFLOWS"
echo ""

if [ ${#WARNINGS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ TOUS LES WORKFLOWS SONT COMPATIBLES NODE.JS 24 !${NC}"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  AVERTISSEMENTS DÉTECTÉS:${NC}"
    echo ""
    for warning in "${WARNINGS[@]}"; do
        echo -e "   ${YELLOW}•${NC} $warning"
    done
    echo ""
    echo -e "${YELLOW}📝 Recommandation:${NC}"
    echo "   1. Ajoutez 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true' dans env:"
    echo "   2. Mettez à jour les versions des actions"
    echo "   3. Relancez ce script pour vérifier"
    echo ""
    exit 1
fi
