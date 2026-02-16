// Système de prédiction simple basé sur patterns
class PredictionEngine {
    constructor() {
        this.history = [];
    }
    
    async loadHistory(zoneName) {
        try {
            const response = await fetch(`./logs/stats/${zoneName.toLowerCase().replace(/[- ]/g, '_')}.json`);
            const data = await response.json();
            this.history = data.history || [];
        } catch (error) {
            console.error('Erreur chargement historique:', error);
        }
    }
    
    predictNext6Hours(zoneName) {
        if (this.history.length < 7) {
            return {
                success: false,
                message: "Pas assez de données historiques"
            };
        }
        
        const now = new Date();
        const currentHour = now.getHours();
        
        // Trouver patterns similaires (même heure, jours précédents)
        const similarConditions = this.history.filter(entry => {
            const entryDate = new Date(entry.timestamp);
            const entryHour = entryDate.getHours();
            return Math.abs(entryHour - currentHour) <= 2;
        });
        
        if (similarConditions.length < 3) {
            return {
                success: false,
                message: "Pattern insuffisant"
            };
        }
        
        // Calculer moyennes et tendances
        const waves = similarConditions.map(e => e.wave);
        const temps = similarConditions.map(e => e.temp);
        const winds = similarConditions.map(e => e.wind);
        
        const prediction = {
            success: true,
            timestamp: new Date(now.getTime() + 6 * 60 * 60 * 1000).toISOString(),
            wave: {
                value: this.calculateAverage(waves),
                confidence: this.calculateConfidence(waves),
                range: [Math.min(...waves), Math.max(...waves)],
                trend: this.calculateTrend(waves)
            },
            temperature: {
                value: this.calculateAverage(temps),
                confidence: this.calculateConfidence(temps),
                range: [Math.min(...temps), Math.max(...temps)],
                trend: this.calculateTrend(temps)
            },
            wind: {
                value: this.calculateAverage(winds),
                confidence: this.calculateConfidence(winds),
                range: [Math.min(...winds), Math.max(...winds)],
                trend: this.calculateTrend(winds)
            },
            safety_prediction: null,
            based_on: similarConditions.length
        };
        
        // Prédire niveau de sécurité
        if (prediction.wave.value > 3.0 || prediction.wind.value > 15) {
            prediction.safety_prediction = "danger";
        } else if (prediction.wave.value > 2.1 || prediction.wind.value > 12) {
            prediction.safety_prediction = "warning";
        } else if (prediction.wave.value > 1.5 || prediction.wind.value > 8) {
            prediction.safety_prediction = "caution";
        } else {
            prediction.safety_prediction = "safe";
        }
        
        return prediction;
    }
    
    calculateAverage(values) {
        return Math.round(values.reduce((a, b) => a + b, 0) / values.length * 100) / 100;
    }
    
    calculateConfidence(values) {
        // Confiance basée sur variance
        const avg = this.calculateAverage(values);
        const variance = values.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / values.length;
        const stdDev = Math.sqrt(variance);
        
        // Plus la variance est faible, plus la confiance est haute
        const confidence = Math.max(0, Math.min(1, 1 - (stdDev / avg)));
        return Math.round(confidence * 100);
    }
    
    calculateTrend(values) {
        if (values.length < 2) return "stable";
        
        // Régression linéaire simple
        const n = values.length;
        const x = Array.from({ length: n }, (_, i) => i);
        const sumX = x.reduce((a, b) => a + b, 0);
        const sumY = values.reduce((a, b) => a + b, 0);
        const sumXY = x.reduce((sum, xi, i) => sum + xi * values[i], 0);
        const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
        
        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        
        if (slope > 0.1) return "hausse";
        if (slope < -0.1) return "baisse";
        return "stable";
    }
    
    predict24Hours(zoneName) {
        // Prédictions toutes les 3h sur 24h
        const predictions = [];
        
        for (let i = 3; i <= 24; i += 3) {
            const pred = this.predictAtHour(zoneName, i);
            if (pred.success) {
                predictions.push(pred);
            }
        }
        
        return predictions;
    }
    
    predictAtHour(zoneName, hoursAhead) {
        // Simplification : utiliser pattern historique
        const targetTime = new Date(Date.now() + hoursAhead * 60 * 60 * 1000);
        const targetHour = targetTime.getHours();
        
        const matchingData = this.history.filter(entry => {
            const date = new Date(entry.timestamp);
            return date.getHours() === targetHour;
        });
        
        if (matchingData.length === 0) {
            return { success: false };
        }
        
        const waves = matchingData.map(e => e.wave);
        const temps = matchingData.map(e => e.temp);
        
        return {
            success: true,
            time: targetTime.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
            wave: this.calculateAverage(waves),
            temp: this.calculateAverage(temps),
            confidence: this.calculateConfidence(waves)
        };
    }
}

// Instance globale
const predictor = new PredictionEngine();
