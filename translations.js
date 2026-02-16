// Système de traduction complet
const translations = {
    fr: {
        // Navigation
        "home": "Accueil",
        "history": "Historique",
        "compare": "Comparateur",
        "alerts": "Alertes",
        "settings": "Paramètres",
        
        // Sécurité
        "safe": "Sûr",
        "caution": "Vigilance",
        "warning": "Prudence",
        "danger": "Danger",
        
        // Météo
        "waves": "Vagues",
        "temperature": "Température",
        "current": "Courant",
        "wind": "Vent",
        "visibility": "Visibilité",
        "humidity": "Humidité",
        "precipitation": "Précipitations",
        
        // Pêche
        "fish_index": "Indice Pêche",
        "excellent": "Excellent",
        "good": "Bon",
        "moderate": "Moyen",
        "poor": "Faible",
        
        // Actions
        "go_out": "Sortir",
        "stay_home": "Rester",
        "be_careful": "Attention",
        
        // Recommandations
        "do_not_go_out": "NE PAS SORTIR EN MER",
        "stay_near_coast": "Restez près des côtes",
        "safe_conditions": "Conditions sûres pour la navigation",
        "optimal_fishing": "Conditions OPTIMALES pour la pêche",
        "good_fishing": "Bonnes conditions de pêche",
        
        // Temps
        "today": "Aujourd'hui",
        "yesterday": "Hier",
        "tomorrow": "Demain",
        "this_week": "Cette semaine",
        "last_7_days": "7 derniers jours",
        
        // Interface
        "loading": "Chargement",
        "error": "Erreur",
        "no_data": "Aucune donnée",
        "updated": "Mis à jour",
        "zones": "zones",
        "regions": "régions",
        
        // Comparateur
        "where_to_fish": "Où pêcher aujourd'hui ?",
        "best_zone": "Meilleure zone",
        "score": "Score",
        "distance": "Distance",
        "reasons": "Raisons",
        
        // Alertes
        "enable_alerts": "Activer les alertes",
        "alert_types": "Types d'alertes",
        "zones_to_watch": "Zones à surveiller",
        "save_settings": "Sauvegarder"
    },
    
    wo: {
        // Navigation
        "home": "Kër",
        "history": "Jaar-jaar",
        "compare": "Wuute",
        "alerts": "Yéenekaay",
        "settings": "Paramètr",
        
        // Sécurité
        "safe": "Baax",
        "caution": "Seet",
        "warning": "Bàyyi",
        "danger": "Ñax",
        
        // Météo
        "waves": "Ndox",
        "temperature": "Tangoor",
        "current": "Dëkk ndox",
        "wind": "Gàmmu",
        "visibility": "Gis",
        "humidity": "Ndaw",
        "precipitation": "Taw",
        
        // Pêche
        "fish_index": "Liggéey jën",
        "excellent": "Rafet na lool",
        "good": "Baax na",
        "moderate": "Mu neex",
        "poor": "Muñ",
        
        // Actions
        "go_out": "Génn",
        "stay_home": "Toog",
        "be_careful": "Seet",
        
        // Recommandations
        "do_not_go_out": "BUL GÉNN CI GÉEJ",
        "stay_near_coast": "Toog ci buntu géej",
        "safe_conditions": "Dëkk baax na ngir génn",
        "optimal_fishing": "Dëkk RAFET na ngir jën",
        "good_fishing": "Jëfandoo na ngir jën",
        
        // Temps
        "today": "Tay",
        "yesterday": "Démb",
        "tomorrow": "Suba",
        "this_week": "Ayu-bis bii",
        "last_7_days": "7 fan ñépp",
        
        // Interface
        "loading": "Yégël",
        "error": "Njumte",
        "no_data": "Amul",
        "updated": "Yéesal",
        "zones": "bër",
        "regions": "jëf",
        
        // Comparateur
        "where_to_fish": "Fan ngay jën tey?",
        "best_zone": "Bër bu baax",
        "score": "Liggéey",
        "distance": "Wëral",
        "reasons": "Dëgg-dëgg",
        
        // Alertes
        "enable_alerts": "Lajjal yéenekaay",
        "alert_types": "Sàmm yéenekaay",
        "zones_to_watch": "Bër ngay gis",
        "save_settings": "Dugg"
    },
    
    en: {
        // Navigation
        "home": "Home",
        "history": "History",
        "compare": "Compare",
        "alerts": "Alerts",
        "settings": "Settings",
        
        // Sécurité
        "safe": "Safe",
        "caution": "Caution",
        "warning": "Warning",
        "danger": "Danger",
        
        // Météo
        "waves": "Waves",
        "temperature": "Temperature",
        "current": "Current",
        "wind": "Wind",
        "visibility": "Visibility",
        "humidity": "Humidity",
        "precipitation": "Precipitation",
        
        // Pêche
        "fish_index": "Fish Index",
        "excellent": "Excellent",
        "good": "Good",
        "moderate": "Moderate",
        "poor": "Poor",
        
        // Actions
        "go_out": "Go Out",
        "stay_home": "Stay",
        "be_careful": "Be Careful",
        
        // Recommandations
        "do_not_go_out": "DO NOT GO TO SEA",
        "stay_near_coast": "Stay near the coast",
        "safe_conditions": "Safe conditions for navigation",
        "optimal_fishing": "OPTIMAL fishing conditions",
        "good_fishing": "Good fishing conditions",
        
        // Temps
        "today": "Today",
        "yesterday": "Yesterday",
        "tomorrow": "Tomorrow",
        "this_week": "This week",
        "last_7_days": "Last 7 days",
        
        // Interface
        "loading": "Loading",
        "error": "Error",
        "no_data": "No data",
        "updated": "Updated",
        "zones": "zones",
        "regions": "regions",
        
        // Comparateur
        "where_to_fish": "Where to fish today?",
        "best_zone": "Best zone",
        "score": "Score",
        "distance": "Distance",
        "reasons": "Reasons",
        
        // Alertes
        "enable_alerts": "Enable alerts",
        "alert_types": "Alert types",
        "zones_to_watch": "Zones to watch",
        "save_settings": "Save settings"
    }
};

class LanguageManager {
    constructor() {
        this.currentLanguage = this.loadLanguage();
        this.applyLanguage();
    }
    
    loadLanguage() {
        const saved = localStorage.getItem('pecheurconnect_language');
        return saved || 'fr';
    }
    
    setLanguage(lang) {
        if (!translations[lang]) {
            console.error('Langue non supportée:', lang);
            return;
        }
        
        this.currentLanguage = lang;
        localStorage.setItem('pecheurconnect_language', lang);
        this.applyLanguage();
        
        // Recharger la page pour appliquer partout
        window.location.reload();
    }
    
    translate(key) {
        const translation = translations[this.currentLanguage][key];
        return translation || translations['fr'][key] || key;
    }
    
    t(key) {
        return this.translate(key);
    }
    
    applyLanguage() {
        // Appliquer à tous les éléments avec data-translate
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.getAttribute('data-translate');
            const translation = this.translate(key);
            
            if (element.tagName === 'INPUT' && element.placeholder) {
                element.placeholder = translation;
            } else {
                element.textContent = translation;
            }
        });
        
        // Mettre à jour l'attribut lang du document
        document.documentElement.lang = this.currentLanguage;
    }
}

// Instance globale
const lang = new LanguageManager();

// Fonction helper globale
function t(key) {
    return lang.translate(key);
}
