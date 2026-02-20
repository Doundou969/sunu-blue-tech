/**
 * PecheurConnect v3.0 - Système de prévisions
 * Machine Learning simple basé sur patterns historiques
 */

class PredictionEngine {
    constructor() {
        this.history = [];
        this.patterns = {};
        this.confidence = 0;
    }
    
    // ================================================================
    // CHARGEMENT HISTORIQUE
    // ================================================================
    async loadHistory(zoneName) {
        try {
            const fileName = zoneName.toLowerCase().replace(/[- ]/g, '_');
            const response = await fetch(`./logs/stats/${fileName}.json?v=${Date.now()}`);
            
            if (!response.ok) {
                console.warn('[Predictions] Pas d\'historique pour', zoneName);
                return false;
            }
            
            const data = await response.json();
            this.history = data.history || [];
            
            console.log(`[Predictions] Historique chargé: ${this.history.length} points pour ${zoneName}`);
            
            // Analyser patterns
            this.analyzePatterns();
            
            return true;
        } catch (error) {
            console.error('[Predictions] Erreur chargement:', error);
            return false;
        }
    }
    
    // ================================================================
    // ANALYSE DES PATTERNS
    // ================================================================
    analyzePatterns() {
        if (this.history.length < 14) {
            console.warn('[Predictions] Pas assez de données pour patterns');
            return;
        }
        
        // Patterns par heure de la journée
        this.patterns.byHour = {};
        
        this.history.forEach(entry => {
            const date = new Date(entry.timestamp);
            const hour = date.getHours();
            
            if (!this.patterns.byHour[hour]) {
                this.patterns.byHour[hour] = {
                    waves: [],
                    temps: [],
                    winds: [],
                    safety: []
                };
            }
            
            this.patterns.byHour[hour].waves.push(entry.wave);
            this.patterns.byHour[hour].temps.push(entry.temp);
            this.patterns.byHour[hour].winds.push(entry.wind);
            this.patterns.byHour[hour].safety.push(entry.safety_level);
        });
        
        // Patterns par jour de la semaine
        this.patterns.byWeekday = {};
        
        this.history.forEach(entry => {
            const date = new Date(entry.timestamp);
            const weekday = date.getDay(); // 0-6
            
            if (!this.patterns.byWeekday[weekday]) {
                this.patterns.byWeekday[weekday] = {
                    waves: [],
                    temps: [],
                    safety: []
                };
            }
            
            this.patterns.byWeekday[weekday].waves.push(entry.wave);
            this.patterns.byWeekday[weekday].temps.push(entry.temp);
            this.patterns.byWeekday[weekday].safety.push(entry.safety_level);
        });
        
        console.log('[Predictions] Patterns analysés');
    }
    
    // ================================================================
    // PRÉDICTIONS
    // ================================================================
    predictNext6Hours() {
        if (this.history.length < 7) {
            return {
                success: false,
                message: "Pas assez de données historiques (minimum 7 points)"
            };
        }
        
        const now = new Date();
        const currentHour = now.getHours();
        const targetHour = (currentHour + 6) % 24;
        
        // Récupérer conditions similaires
        const similarConditions = this.findSimilarConditions(currentHour, 2);
        
        if (similarConditions.length < 3) {
            return {
                success: false,
                message: "Pattern insuffisant pour prédiction"
            };
        }
        
        // Calculer moyennes et tendances
        const waves = similarConditions.map(e => e.wave);
        const temps = similarConditions.map(e => e.temp);
        const winds = similarConditions.map(e => e.wind);
        
        // Appliquer tendance récente
        const recentTrend = this.calculateRecentTrend();
        
        const prediction = {
            success: true,
            timestamp: new Date(now.getTime() + 6 * 60 * 60 * 1000).toISOString(),
            timeLabel: this.formatHour(targetHour),
            wave: {
                value: this.applyTrend(this.average(waves), recentTrend.wave),
                confidence: this.calculateConfidence(waves),
                range: [Math.min(...waves), Math.max(...waves)],
                trend: this.getTrendDirection(recentTrend.wave)
            },
            temperature: {
                value: this.applyTrend(this.average(temps), recentTrend.temp),
                confidence: this.calculateConfidence(temps),
                range: [Math.min(...temps), Math.max(...temps)],
                trend: this.getTrendDirection(recentTrend.temp)
            },
            wind: {
                value: this.applyTrend(this.average(winds), recentTrend.wind),
                confidence: this.calculateConfidence(winds),
                range: [Math.min(...winds), Math.max(...winds)],
                trend: this.getTrendDirection(recentTrend.wind)
            },
            safety_prediction: null,
            based_on: similarConditions.length,
            method: 'pattern_matching'
        };
        
        // Prédire niveau de sécurité
        prediction.safety_prediction = this.predictSafety(
            prediction.wave.value,
            prediction.wind.value
        );
        
        // Confiance globale
        this.confidence = Math.round(
            (prediction.wave.confidence + prediction.temperature.confidence + prediction.wind.confidence) / 3
        );
        
        return prediction;
    }
    
    predictNext24Hours() {
        const predictions = [];
        
        for (let hoursAhead = 3; hoursAhead <= 24; hoursAhead += 3) {
            const pred = this.predictAtHour(hoursAhead);
            if (pred.success) {
                predictions.push(pred);
            }
        }
        
        return {
            success: predictions.length > 0,
            predictions: predictions,
            count: predictions.length
        };
    }
    
    predictAtHour(hoursAhead) {
        const now = new Date();
        const targetTime = new Date(now.getTime() + hoursAhead * 60 * 60 * 1000);
        const targetHour = targetTime.getHours();
        
        // Chercher données similaires
        const matchingData = this.history.filter(entry => {
            const date = new Date(entry.timestamp);
            return date.getHours() === targetHour;
        });
        
        if (matchingData.length === 0) {
            return { success: false };
        }
        
        const waves = matchingData.map(e => e.wave);
        const temps = matchingData.map(e => e.temp);
        const winds = matchingData.map(e => e.wind);
        
        return {
            success: true,
            time: targetTime.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
            hoursAhead: hoursAhead,
            wave: this.round(this.average(waves), 2),
            temp: this.round(this.average(temps), 1),
            wind: this.round(this.average(winds), 1),
            confidence: this.calculateConfidence(waves),
            safety: this.predictSafety(this.average(waves), this.average(winds))
        };
    }
    
    // ================================================================
    // HELPERS PRÉDICTIONS
    // ================================================================
    findSimilarConditions(hour, tolerance = 2) {
        const similar = [];
        
        for (let h = hour - tolerance; h <= hour + tolerance; h++) {
            const normalizedHour = (h + 24) % 24;
            
            this.history.forEach(entry => {
                const entryDate = new Date(entry.timestamp);
                if (entryDate.getHours() === normalizedHour) {
                    similar.push(entry);
                }
            });
        }
        
        return similar;
    }
    
    calculateRecentTrend() {
        // Analyser les 5 derniers points
        const recent = this.history.slice(-5);
        
        if (recent.length < 3) {
            return { wave: 0, temp: 0, wind: 0 };
        }
        
        return {
            wave: this.linearTrend(recent.map(e => e.wave)),
            temp: this.linearTrend(recent.map(e => e.temp)),
            wind: this.linearTrend(recent.map(e => e.wind))
        };
    }
    
    linearTrend(values) {
        if (values.length < 2) return 0;
        
        const n = values.length;
        const x = Array.from({ length: n }, (_, i) => i);
        
        const sumX = x.reduce((a, b) => a + b, 0);
        const sumY = values.reduce((a, b) => a + b, 0);
        const sumXY = x.reduce((sum, xi, i) => sum + xi * values[i], 0);
        const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
        
        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        
        return slope;
    }
    
    applyTrend(baseValue, trendSlope) {
        // Appliquer tendance avec pondération
        const adjustment = trendSlope * 0.3; // 30% de la tendance
        return this.round(Math.max(0, baseValue + adjustment), 2);
    }
    
    getTrendDirection(slope) {
        if (slope > 0.05) return 'hausse';
        if (slope < -0.05) return 'baisse';
        return 'stable';
    }
    
    predictSafety(wave, wind) {
        if (wave > 3.0 || wind > 15) return 'danger';
        if (wave > 2.1 || wind > 12) return 'warning';
        if (wave > 1.5 || wind > 8) return 'caution';
        return 'safe';
    }
    
    // ================================================================
    // STATISTIQUES
    // ================================================================
    average(values) {
        if (values.length === 0) return 0;
        return values.reduce((a, b) => a + b, 0) / values.length;
    }
    
    calculateConfidence(values) {
        if (values.length < 2) return 0;
        
        const avg = this.average(values);
        const variance = values.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / values.length;
        const stdDev = Math.sqrt(variance);
        
        // Coefficient de variation inversé
        if (avg === 0) return 50;
        
        const cv = stdDev / Math.abs(avg);
        const confidence = Math.max(0, Math.min(100, (1 - cv) * 100));
        
        return Math.round(confidence);
    }
    
    round(value, decimals = 2) {
        const factor = Math.pow(10, decimals);
        return Math.round(value * factor) / factor;
    }
    
    formatHour(hour) {
        return `${hour.toString().padStart(2, '0')}:00`;
    }
    
    // ================================================================
    // ANALYSE QUALITÉ PRÉDICTIONS
    // ================================================================
    evaluateAccuracy() {
        if (this.history.length < 20) {
            return {
                success: false,
                message: "Pas assez de données pour évaluation"
            };
        }
        
        // Comparer prédictions passées vs réalité
        const errors = { wave: [], temp: [], wind: [] };
        
        for (let i = 10; i < this.history.length - 1; i++) {
            const actual = this.history[i + 1];
            
            // Simuler prédiction à partir de i
            const similar = this.history.slice(0, i).filter(e => {
                const actualDate = new Date(actual.timestamp);
                const entryDate = new Date(e.timestamp);
                return Math.abs(actualDate.getHours() - entryDate.getHours()) <= 2;
            });
            
            if (similar.length < 3) continue;
            
            const predictedWave = this.average(similar.map(e => e.wave));
            const predictedTemp = this.average(similar.map(e => e.temp));
            const predictedWind = this.average(similar.map(e => e.wind));
            
            errors.wave.push(Math.abs(actual.wave - predictedWave));
            errors.temp.push(Math.abs(actual.temp - predictedTemp));
            errors.wind.push(Math.abs(actual.wind - predictedWind));
        }
        
        return {
            success: true,
            mae: {
                wave: this.round(this.average(errors.wave), 3),
                temp: this.round(this.average(errors.temp), 3),
                wind: this.round(this.average(errors.wind), 3)
            },
            samples: errors.wave.length,
            quality: this.getQualityRating(errors)
        };
    }
    
    getQualityRating(errors) {
        const avgWaveError = this.average(errors.wave);
        
        if (avgWaveError < 0.3) return 'Excellente';
        if (avgWaveError < 0.5) return 'Bonne';
        if (avgWaveError < 0.8) return 'Moyenne';
        return 'Faible';
    }
    
    // ================================================================
    // EXPORT / RAPPORT
    // ================================================================
    generateReport() {
        const accuracy = this.evaluateAccuracy();
        
        return {
            dataPoints: this.history.length,
            coverage: this.getCoverage(),
            patterns: {
                hourly: Object.keys(this.patterns.byHour || {}).length,
                weekly: Object.keys(this.patterns.byWeekday || {}).length
            },
            accuracy: accuracy,
            confidence: this.confidence,
            lastUpdate: this.history.length > 0 ? this.history[this.history.length - 1].timestamp : null
        };
    }
    
    getCoverage() {
        if (this.history.length === 0) return '0%';
        
        const now = Date.now();
        const oldest = new Date(this.history[0].timestamp).getTime();
        const daysCovered = (now - oldest) / (1000 * 60 * 60 * 24);
        
        return `${Math.round(daysCovered)} jours`;
    }
}

// ================================================================
// INSTANCE GLOBALE
// ================================================================
const predictor = new PredictionEngine();

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PredictionEngine, predictor };
}
