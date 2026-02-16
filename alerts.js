// Système d'alertes push PWA
class AlertSystem {
    constructor() {
        this.subscription = null;
        this.preferences = this.loadPreferences();
    }
    
    loadPreferences() {
        const saved = localStorage.getItem('alert_preferences');
        return saved ? JSON.parse(saved) : {
            enabled: false,
            zones: [],
            conditions: {
                danger: true,
                warning: true,
                optimal: true
            },
            thresholds: {
                wave: 2.5,
                wind: 12.0
            }
        };
    }
    
    savePreferences() {
        localStorage.setItem('alert_preferences', JSON.stringify(this.preferences));
    }
    
    async requestPermission() {
        if (!('Notification' in window)) {
            alert('Les notifications ne sont pas supportées par votre navigateur');
            return false;
        }
        
        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
            this.preferences.enabled = true;
            this.savePreferences();
            await this.subscribe();
            return true;
        }
        
        return false;
    }
    
    async subscribe() {
        if (!('serviceWorker' in navigator)) return;
        
        try {
            const registration = await navigator.serviceWorker.ready;
            
            // Clé VAPID publique (à générer)
            const vapidPublicKey = 'YOUR_VAPID_PUBLIC_KEY';
            
            this.subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(vapidPublicKey)
            });
            
            // Envoyer subscription au serveur
            await this.sendSubscriptionToServer(this.subscription);
            
        } catch (error) {
            console.error('Erreur subscription:', error);
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
        // Envoyer au serveur pour stockage
        // À implémenter côté serveur
        console.log('Subscription:', JSON.stringify(subscription));
    }
    
    showLocalNotification(title, body, data) {
        if (!this.preferences.enabled) return;
        
        if (Notification.permission === 'granted') {
            new Notification(title, {
                body: body,
                icon: './icons/icon-192.png',
                badge: './icons/badge-72.png',
                data: data,
                tag: data.zone || 'general',
                requireInteraction: data.priority === 'high'
            });
        }
    }
    
    checkConditions(zones) {
        zones.forEach(zone => {
            const prefs = this.preferences;
            
            // Zone suivie ?
            if (prefs.zones.length > 0 && !prefs.zones.includes(zone.zone)) {
                return;
            }
            
            // Vérifier conditions
            if (zone.safety_level === 'danger' && prefs.conditions.danger) {
                this.showLocalNotification(
                    `🔴 ALERTE DANGER - ${zone.zone}`,
                    `Vagues: ${zone.v_now}m | Vent: ${zone.wind_speed}m/s. NE PAS SORTIR !`,
                    { zone: zone.zone, priority: 'high', type: 'danger' }
                );
            }
            
            if (zone.safety_level === 'warning' && prefs.conditions.warning) {
                this.showLocalNotification(
                    `🟠 Prudence - ${zone.zone}`,
                    `Conditions se dégradent. Restez vigilant.`,
                    { zone: zone.zone, priority: 'medium', type: 'warning' }
                );
            }
            
            if (zone.fish_level === 'excellent' && zone.safety_level === 'safe' && prefs.conditions.optimal) {
                this.showLocalNotification(
                    `🎣 Conditions optimales - ${zone.zone}`,
                    `C'est le moment idéal pour sortir !`,
                    { zone: zone.zone, priority: 'low', type: 'optimal' }
                );
            }
        });
    }
}

// Initialiser
const alertSystem = new AlertSystem();
