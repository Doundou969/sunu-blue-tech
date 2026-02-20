/**
 * PecheurConnect v3.0 - Système d'alertes push
 * Notifications PWA, gestion préférences, vérification conditions
 */

class AlertSystem {
    constructor() {
        this.subscription = null;
        this.preferences = this.loadPreferences();
        this.checkInterval = null;
        this.lastCheck = null;
    }
    
    // ================================================================
    // GESTION PRÉFÉRENCES
    // ================================================================
    loadPreferences() {
        const saved = localStorage.getItem('pecheurconnect_alerts');
        
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (e) {
                console.error('Erreur chargement préférences:', e);
            }
        }
        
        // Préférences par défaut
        return {
            enabled: false,
            zones: [], // Vide = toutes les zones
            conditions: {
                danger: true,
                warning: true,
                optimal: true,
                degradation: false
            },
            thresholds: {
                wave: 2.5,
                wind: 12.0,
                current: 0.8
            },
            quiet_hours: {
                enabled: false,
                start: '22:00',
                end: '07:00'
            },
            sound: true,
            vibration: true
        };
    }
    
    savePreferences() {
        try {
            localStorage.setItem('pecheurconnect_alerts', JSON.stringify(this.preferences));
            console.log('[Alerts] Préférences sauvegardées');
            return true;
        } catch (e) {
            console.error('[Alerts] Erreur sauvegarde:', e);
            return false;
        }
    }
    
    updatePreferences(updates) {
        this.preferences = { ...this.preferences, ...updates };
        this.savePreferences();
        
        // Redémarrer surveillance si activé
        if (this.preferences.enabled) {
            this.startMonitoring();
        } else {
            this.stopMonitoring();
        }
    }
    
    // ================================================================
    // PERMISSIONS
    // ================================================================
    async requestPermission() {
        if (!('Notification' in window)) {
            console.error('[Alerts] Notifications non supportées');
            return false;
        }
        
        if (Notification.permission === 'granted') {
            console.log('[Alerts] Permission déjà accordée');
            return true;
        }
        
        if (Notification.permission === 'denied') {
            console.error('[Alerts] Permission refusée');
            return false;
        }
        
        try {
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                console.log('[Alerts] Permission accordée');
                this.preferences.enabled = true;
                this.savePreferences();
                await this.subscribe();
                return true;
            } else {
                console.log('[Alerts] Permission refusée par utilisateur');
                return false;
            }
        } catch (error) {
            console.error('[Alerts] Erreur permission:', error);
            return false;
        }
    }
    
    // ================================================================
    // PUSH SUBSCRIPTION
    // ================================================================
    async subscribe() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            console.log('[Alerts] Push non supporté, utilisation locale');
            return;
        }
        
        try {
            const registration = await navigator.serviceWorker.ready;
            
            // Clé VAPID publique (à générer avec web-push)
            // Pour générer: npm install -g web-push && web-push generate-vapid-keys
            const vapidPublicKey = 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBrXhqhHk6LvySnk5S8s';
            
            this.subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(vapidPublicKey)
            });
            
            console.log('[Alerts] Subscription:', this.subscription);
            
            // Envoyer subscription au serveur (si backend disponible)
            await this.sendSubscriptionToServer(this.subscription);
            
        } catch (error) {
            console.error('[Alerts] Erreur subscription:', error);
        }
    }
    
    async unsubscribe() {
        if (!this.subscription) return;
        
        try {
            await this.subscription.unsubscribe();
            this.subscription = null;
            console.log('[Alerts] Désabonné');
        } catch (error) {
            console.error('[Alerts] Erreur unsubscribe:', error);
        }
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        
        return outputArray;
    }
    
    async sendSubscriptionToServer(subscription) {
        // TODO: Implémenter endpoint backend
        console.log('[Alerts] Subscription à envoyer au serveur:', JSON.stringify(subscription));
        
        // Exemple avec fetch (nécessite backend)
        /*
        try {
            await fetch('/api/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subscription })
            });
        } catch (error) {
            console.error('Erreur envoi subscription:', error);
        }
        */
    }
    
    // ================================================================
    // NOTIFICATIONS LOCALES
    // ================================================================
    showLocalNotification(title, body, data = {}) {
        if (!this.preferences.enabled) return;
        
        // Vérifier heures silencieuses
        if (this.isQuietHours()) {
            console.log('[Alerts] Heures silencieuses - notification ignorée');
            return;
        }
        
        if (Notification.permission !== 'granted') {
            console.warn('[Alerts] Permission non accordée');
            return;
        }
        
        const options = {
            body: body,
            icon: 'https://cdn-icons-png.flaticon.com/128/2965/2965315.png',
            badge: 'https://cdn-icons-png.flaticon.com/72/2965/2965315.png',
            vibrate: this.preferences.vibration ? [200, 100, 200] : [],
            silent: !this.preferences.sound,
            data: data,
            tag: data.zone || 'general',
            requireInteraction: data.priority === 'high',
            actions: [
                { action: 'view', title: 'Voir', icon: '🗺️' },
                { action: 'close', title: 'Fermer', icon: '✕' }
            ]
        };
        
        try {
            const notification = new Notification(title, options);
            
            notification.onclick = (event) => {
                event.preventDefault();
                window.focus();
                
                if (data.zone && data.action === 'view') {
                    window.location.href = `./index.html?zone=${encodeURIComponent(data.zone)}`;
                }
                
                notification.close();
            };
            
            console.log('[Alerts] Notification affichée:', title);
        } catch (error) {
            console.error('[Alerts] Erreur notification:', error);
        }
    }
    
    isQuietHours() {
        if (!this.preferences.quiet_hours.enabled) return false;
        
        const now = new Date();
        const currentTime = now.getHours() * 60 + now.getMinutes();
        
        const [startH, startM] = this.preferences.quiet_hours.start.split(':').map(Number);
        const [endH, endM] = this.preferences.quiet_hours.end.split(':').map(Number);
        
        const start = startH * 60 + startM;
        const end = endH * 60 + endM;
        
        if (start < end) {
            return currentTime >= start && currentTime < end;
        } else {
            // Période traversant minuit
            return currentTime >= start || currentTime < end;
        }
    }
    
    // ================================================================
    // SURVEILLANCE DES CONDITIONS
    // ================================================================
    startMonitoring(intervalMinutes = 30) {
        if (!this.preferences.enabled) return;
        
        console.log('[Alerts] Démarrage surveillance (intervalle:', intervalMinutes, 'min)');
        
        // Vérification immédiate
        this.checkConditions();
        
        // Puis vérifications périodiques
        this.checkInterval = setInterval(() => {
            this.checkConditions();
        }, intervalMinutes * 60 * 1000);
    }
    
    stopMonitoring() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
            console.log('[Alerts] Surveillance arrêtée');
        }
    }
    
    async checkConditions() {
        try {
            const response = await fetch('./data.json?v=' + Date.now());
            if (!response.ok) throw new Error('Erreur chargement données');
            
            const zones = await response.json();
            
            zones.forEach(zone => {
                this.evaluateZone(zone);
            });
            
            this.lastCheck = new Date();
            console.log('[Alerts] Vérification effectuée:', this.lastCheck.toLocaleTimeString());
            
        } catch (error) {
            console.error('[Alerts] Erreur vérification:', error);
        }
    }
    
    evaluateZone(zone) {
        const prefs = this.preferences;
        
        // Vérifier si zone suivie
        if (prefs.zones.length > 0 && !prefs.zones.includes(zone.zone)) {
            return;
        }
        
        // Stocker état précédent
        const previousState = this.getZoneState(zone.zone);
        
        // ALERTE DANGER
        if (zone.safety_level === 'danger' && prefs.conditions.danger) {
            if (!previousState || previousState.safety_level !== 'danger') {
                this.showLocalNotification(
                    `🔴 ALERTE DANGER - ${zone.zone}`,
                    `Vagues: ${zone.v_now}m | Vent: ${zone.wind_speed}m/s\nNE PAS SORTIR EN MER !`,
                    {
                        zone: zone.zone,
                        priority: 'high',
                        type: 'danger',
                        action: 'view'
                    }
                );
            }
        }
        
        // ALERTE PRUDENCE
        if (zone.safety_level === 'warning' && prefs.conditions.warning) {
            if (!previousState || previousState.safety_level !== 'warning') {
                this.showLocalNotification(
                    `🟠 Prudence - ${zone.zone}`,
                    `Les conditions se dégradent. Sortie déconseillée.`,
                    {
                        zone: zone.zone,
                        priority: 'medium',
                        type: 'warning',
                        action: 'view'
                    }
                );
            }
        }
        
        // ALERTE CONDITIONS OPTIMALES
        if (zone.fish_level === 'excellent' && zone.safety_level === 'safe' && prefs.conditions.optimal) {
            if (!previousState || previousState.fish_level !== 'excellent') {
                this.showLocalNotification(
                    `🎣 Conditions optimales - ${zone.zone}`,
                    `Mer calme (${zone.v_now}m) et excellente pêche !`,
                    {
                        zone: zone.zone,
                        priority: 'low',
                        type: 'optimal',
                        action: 'view'
                    }
                );
            }
        }
        
        // ALERTE DÉGRADATION
        if (prefs.conditions.degradation && previousState) {
            if (previousState.safety_level === 'safe' && zone.safety_level !== 'safe') {
                this.showLocalNotification(
                    `⚠️ Dégradation - ${zone.zone}`,
                    `Les conditions ont changé: ${zone.safety}`,
                    {
                        zone: zone.zone,
                        priority: 'medium',
                        type: 'degradation',
                        action: 'view'
                    }
                );
            }
        }
        
        // SEUILS PERSONNALISÉS
        if (zone.v_now >= prefs.thresholds.wave) {
            this.showLocalNotification(
                `🌊 Seuil vagues dépassé - ${zone.zone}`,
                `Vagues: ${zone.v_now}m (seuil: ${prefs.thresholds.wave}m)`,
                { zone: zone.zone, priority: 'medium', type: 'threshold' }
            );
        }
        
        // Sauvegarder état
        this.saveZoneState(zone.zone, {
            safety_level: zone.safety_level,
            fish_level: zone.fish_level,
            wave: zone.v_now,
            timestamp: Date.now()
        });
    }
    
    // ================================================================
    // STOCKAGE ÉTATS
    // ================================================================
    getZoneState(zoneName) {
        const states = localStorage.getItem('pecheurconnect_zone_states');
        if (!states) return null;
        
        try {
            const parsed = JSON.parse(states);
            return parsed[zoneName];
        } catch (e) {
            return null;
        }
    }
    
    saveZoneState(zoneName, state) {
        let states = {};
        
        const existing = localStorage.getItem('pecheurconnect_zone_states');
        if (existing) {
            try {
                states = JSON.parse(existing);
            } catch (e) {}
        }
        
        states[zoneName] = state;
        localStorage.setItem('pecheurconnect_zone_states', JSON.stringify(states));
    }
    
    clearZoneStates() {
        localStorage.removeItem('pecheurconnect_zone_states');
    }
    
    // ================================================================
    // HELPERS
    // ================================================================
    async testNotification() {
        const granted = await this.requestPermission();
        
        if (granted) {
            this.showLocalNotification(
                '✅ Test de notification',
                'Les alertes PecheurConnect fonctionnent correctement !',
                { zone: 'TEST', priority: 'low', type: 'test' }
            );
        }
    }
    
    getStatus() {
        return {
            enabled: this.preferences.enabled,
            permission: Notification.permission,
            subscribed: !!this.subscription,
            monitoring: !!this.checkInterval,
            lastCheck: this.lastCheck,
            zonesWatched: this.preferences.zones.length || 'Toutes'
        };
    }
}

// ================================================================
// INSTANCE GLOBALE
// ================================================================
const alertSystem = new AlertSystem();

// Auto-démarrage si activé
document.addEventListener('DOMContentLoaded', () => {
    if (alertSystem.preferences.enabled && Notification.permission === 'granted') {
        alertSystem.startMonitoring();
        console.log('[Alerts] Système démarré automatiquement');
    }
});

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AlertSystem, alertSystem };
}
