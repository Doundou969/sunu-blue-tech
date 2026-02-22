#!/usr/bin/env python3
"""
PecheurConnect Bot Telegram v3.0 - Bot interactif complet
Commandes: /start, /conditions, /zone, /alerts, /stats, /forecast, /help, /settings
Auteur: PecheurConnect Team
Date: 2026
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatAction,
    ParseMode, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes,
    JobQueue
)
from telegram.error import TelegramError

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATA_FILE = "data.json"
HISTORY_DIR = Path("logs/history")
STATS_DIR = Path("logs/stats")
DB_PATH = "data/cache.db"

# États pour ConversationHandler
CHOOSING_ZONE = 1
CHOOSING_REGION = 2
SETTING_ALERTS = 3
SETTING_FREQUENCY = 4

# Emoji
EMOJI = {
    "🌊": "waves", "🌡️": "temperature", "🌬️": "wind",
    "⛈️": "danger", "✅": "safe", "⚠️": "warning",
    "🐟": "fish", "🎣": "fishing", "📊": "stats",
    "⏰": "time", "📍": "location", "🔔": "alert"
}

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    filename=f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log",
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# ============================================================================
# MODÈLES DE DONNÉES
# ============================================================================

@dataclass
class UserPreferences:
    """Préférences utilisateur"""
    user_id: int
    favorite_zones: List[str] = None
    favorite_region: str = None
    alert_threshold_wave: float = 2.0
    alert_threshold_current: float = 0.5
    notification_enabled: bool = True
    notification_frequency: str = "hourly"  # hourly, 6hourly, daily
    units: str = "metric"  # metric or imperial
    language: str = "fr"  # fr or en
    
    def __post_init__(self):
        if self.favorite_zones is None:
            self.favorite_zones = []


class UserManager:
    """Gère les préférences utilisateur"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialise la table utilisateurs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                favorite_zones TEXT,
                favorite_region TEXT,
                alert_threshold_wave REAL,
                alert_threshold_current REAL,
                notification_enabled INTEGER,
                notification_frequency TEXT,
                units TEXT,
                language TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> UserPreferences:
        """Récupère préférences utilisateur"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return UserPreferences(
                    user_id=row[0],
                    favorite_zones=json.loads(row[1] or '[]'),
                    favorite_region=row[2],
                    alert_threshold_wave=row[3],
                    alert_threshold_current=row[4],
                    notification_enabled=bool(row[5]),
                    notification_frequency=row[6],
                    units=row[7],
                    language=row[8]
                )
            else:
                return UserPreferences(user_id=user_id)
        except:
            return UserPreferences(user_id=user_id)
    
    def save_user(self, user: UserPreferences):
        """Sauvegarde préférences utilisateur"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, favorite_zones, favorite_region, alert_threshold_wave,
                 alert_threshold_current, notification_enabled, notification_frequency,
                 units, language, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.user_id,
                json.dumps(user.favorite_zones),
                user.favorite_region,
                user.alert_threshold_wave,
                user.alert_threshold_current,
                int(user.notification_enabled),
                user.notification_frequency,
                user.units,
                user.language,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"User {user.user_id} saved")
        except Exception as e:
            logger.error(f"Error saving user {user.user_id}: {str(e)}")


user_manager = UserManager(DB_PATH)

# ============================================================================
# DATA MANAGER
# ============================================================================

class DataManager:
    """Gère l'accès aux données"""
    
    @staticmethod
    def load_current_data() -> Optional[List[Dict]]:
        """Charge les données actuelles"""
        try:
            if Path(DATA_FILE).exists():
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
        
        return []
    
    @staticmethod
    def get_zone_by_name(name: str) -> Optional[Dict]:
        """Récupère données d'une zone"""
        data = DataManager.load_current_data()
        
        for zone in data:
            if zone.get("zone") == name:
                return zone
        
        return None
    
    @staticmethod
    def get_zones_by_region(region: str) -> List[Dict]:
        """Récupère zones d'une région"""
        data = DataManager.load_current_data()
        return [z for z in data if z.get("region") == region]
    
    @staticmethod
    def get_all_regions() -> List[str]:
        """Récupère toutes les régions"""
        data = DataManager.load_current_data()
        regions = set(z.get("region", "") for z in data)
        return sorted(list(regions))
    
    @staticmethod
    def get_all_zones() -> List[str]:
        """Récupère tous les noms de zones"""
        data = DataManager.load_current_data()
        return [z.get("zone", "") for z in data]
    
    @staticmethod
    def get_stats(zone_name: str) -> Optional[Dict]:
        """Récupère statistiques d'une zone"""
        try:
            stats_file = STATS_DIR / f"{zone_name.lower().replace(' ', '_').replace('-', '_')}.json"
            
            if stats_file.exists():
                with open(stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading stats: {str(e)}")
        
        return None


# ============================================================================
# FORMATTERS
# ============================================================================

class MessageFormatter:
    """Formate les messages pour Telegram"""
    
    @staticmethod
    def format_zone_details(zone: Dict) -> str:
        """Formate détails d'une zone"""
        msg = f"*{zone.get('zone', 'N/A')}*\n"
        msg += f"📍 {zone.get('description', '')}\n"
        msg += f"🌍 {zone.get('region', '')}\n\n"
        
        # Conditions actuelles
        msg += f"*🌊 Vagues:* {zone.get('v_now', 0)}m\n"
        msg += f"*🌡️ Température:* {zone.get('t_now', 0)}°C\n"
        msg += f"*🌬️ Courants:* {zone.get('c_now', 0)} m/s\n"
        msg += f"*💨 Vent:* {zone.get('wind_speed', 0)} m/s\n"
        msg += f"*☁️ Nuages:* {zone.get('clouds', 0)}%\n"
        msg += f"*🌤️ Météo:* {zone.get('weather_desc', 'N/A')}\n\n"
        
        # Indice de pêche et sécurité
        msg += f"*{zone.get('index', '🎣 N/A')}*\n"
        msg += f"*{zone.get('safety', '⚠️ N/A')}*\n\n"
        
        # Recommandations
        msg += "*📋 Recommandations:*\n"
        for rec in zone.get('recommendations', [])[:3]:
            msg += f"• {rec}\n"
        
        msg += f"\n🕐 Mise à jour: {zone.get('date', 'N/A')}"
        
        return msg
    
    @staticmethod
    def format_region_summary(region: str, zones: List[Dict]) -> str:
        """Formate résumé d'une région"""
        msg = f"*📍 Région: {region}*\n"
        msg += f"*{len(zones)} zones*\n\n"
        
        # Grouper par sécurité
        safe_zones = [z for z in zones if z.get('safety_level') == 'safe']
        caution_zones = [z for z in zones if z.get('safety_level') == 'caution']
        warning_zones = [z for z in zones if z.get('safety_level') == 'warning']
        danger_zones = [z for z in zones if z.get('safety_level') == 'danger']
        
        if safe_zones:
            msg += f"🟢 *SÛR* ({len(safe_zones)}): "
            msg += ", ".join(z.get('zone', '') for z in safe_zones[:2])
            if len(safe_zones) > 2:
                msg += f" +{len(safe_zones)-2}"
            msg += "\n"
        
        if caution_zones:
            msg += f"🟡 *VIGILANCE* ({len(caution_zones)}): "
            msg += ", ".join(z.get('zone', '') for z in caution_zones[:2])
            if len(caution_zones) > 2:
                msg += f" +{len(caution_zones)-2}"
            msg += "\n"
        
        if warning_zones:
            msg += f"🟠 *PRUDENCE* ({len(warning_zones)}): "
            msg += ", ".join(z.get('zone', '') for z in warning_zones[:2])
            if len(warning_zones) > 2:
                msg += f" +{len(warning_zones)-2}"
            msg += "\n"
        
        if danger_zones:
            msg += f"🔴 *DANGER* ({len(danger_zones)}): "
            msg += ", ".join(z.get('zone', '') for z in danger_zones[:2])
            if len(danger_zones) > 2:
                msg += f" +{len(danger_zones)-2}"
            msg += "\n"
        
        msg += f"\n🕐 {zones[0].get('date', 'N/A') if zones else 'N/A'}"
        
        return msg
    
    @staticmethod
    def format_stats(zone_name: str, stats: Dict) -> str:
        """Formate statistiques"""
        if not stats:
            return f"❌ Pas de statistiques pour {zone_name}"
        
        msg = f"*📊 Statistiques - {zone_name}*\n"
        msg += f"*Période: {stats.get('period', '7 jours')}*\n\n"
        
        # Vagues
        waves = stats.get('statistics', {}).get('waves', {})
        msg += f"*🌊 Vagues:*\n"
        msg += f"  Min: {waves.get('min', 'N/A')}m | Max: {waves.get('max', 'N/A')}m\n"
        msg += f"  Moyenne: {waves.get('avg', 'N/A')}m | σ: {waves.get('std', 'N/A')}m\n"
        msg += f"  Tendance: {waves.get('trend', 'N/A')}\n\n"
        
        # Température
        temp = stats.get('statistics', {}).get('temperature', {})
        msg += f"*🌡️ Température:*\n"
        msg += f"  Min: {temp.get('min', 'N/A')}°C | Max: {temp.get('max', 'N/A')}°C\n"
        msg += f"  Moyenne: {temp.get('avg', 'N/A')}°C\n"
        msg += f"  Tendance: {temp.get('trend', 'N/A')}\n\n"
        
        # Vent
        wind = stats.get('statistics', {}).get('wind', {})
        msg += f"*🌬️ Vent:*\n"
        msg += f"  Min: {wind.get('min', 'N/A')} m/s | Max: {wind.get('max', 'N/A')} m/s\n"
        msg += f"  Moyenne: {wind.get('avg', 'N/A')} m/s\n\n"
        
        # Meilleur/pire jour
        best = stats.get('best_day', {})
        worst = stats.get('worst_day', {})
        
        msg += f"*🏆 Meilleur jour:* {best.get('date', 'N/A')}\n"
        msg += f"  {best.get('safety', 'N/A')} | {best.get('fish', 'N/A')}\n\n"
        
        msg += f"*⚠️ Pire jour:* {worst.get('date', 'N/A')}\n"
        msg += f"  {worst.get('safety', 'N/A')}\n"
        
        return msg
    
    @staticmethod
    def format_comparison(zones: List[Dict]) -> str:
        """Formate comparaison de zones"""
        msg = "*🔍 Comparaison des zones*\n\n"
        
        # Trier par vagues
        sorted_zones = sorted(zones, key=lambda z: z.get('v_now', 0))
        
        msg += "*🌊 Classement par vagues (calme → agitée):*\n"
        for i, zone in enumerate(sorted_zones, 1):
            msg += f"{i}. {zone.get('zone', '')}: {zone.get('v_now', 0)}m\n"
        
        msg += "\n"
        
        # Trier par température
        sorted_zones = sorted(zones, key=lambda z: z.get('t_now', 0), reverse=True)
        
        msg += "*🌡️ Classement par température (chaude → froide):*\n"
        for i, zone in enumerate(sorted_zones, 1):
            msg += f"{i}. {zone.get('zone', '')}: {zone.get('t_now', 0)}°C\n"
        
        msg += "\n"
        
        # Meilleure pêche
        best_zones = sorted(zones, key=lambda z: z.get('danger_score', 0))[:3]
        msg += "*🎣 Meilleures zones pour la pêche:*\n"
        for zone in best_zones:
            msg += f"• {zone.get('zone', '')}: {zone.get('index', 'N/A')}\n"
        
        return msg


# ============================================================================
# COMMANDES PRINCIPALES
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande /start"""
    user = update.effective_user
    user_prefs = user_manager.get_user(user.id)
    
    logger.info(f"User {user.id} started bot")
    
    msg = f"""
👋 *Bienvenue sur PecheurConnect Bot v3.0* 👋

Bonjour *{user.first_name}*! 🎣

Je suis votre assistant personnel pour les conditions maritimes et de pêche au Sénégal.

*Mes fonctionnalités:*
🌊 Conditions maritimes en temps réel
🎣 Indice de pêche personnalisé
📊 Statistiques 7 jours
⚠️ Alertes personnalisables
🌍 18 zones de pêche couvertes
📱 Notifications automatiques

*Commandes disponibles:*
/conditions - Voir toutes les zones
/zone - Détails d'une zone spécifique
/region - Zones d'une région
/alert - Gérer les alertes
/stats - Statistiques d'une zone
/compare - Comparer les zones
/settings - Préférences
/help - Aide complète

Que souhaitez-vous faire?
    """
    
    keyboard = [
        [InlineKeyboardButton("🌊 Conditions", callback_data="conditions"),
         InlineKeyboardButton("🌍 Régions", callback_data="regions")],
        [InlineKeyboardButton("🎣 Meilleures zones", callback_data="best_zones"),
         InlineKeyboardButton("⚠️ Alertes", callback_data="alerts")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats_menu"),
         InlineKeyboardButton("⚙️ Préférences", callback_data="settings")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande /help"""
    msg = """
*📚 AIDE COMPLÈTE - PecheurConnect Bot*

*1. AFFICHER LES CONDITIONS*
/conditions - Résumé complet de toutes les zones
/region - Filtrer par région
/zone - Détails complets d'une zone

*2. PÊCHE*
/conditions - Voir l'indice de pêche
/compare - Comparer les zones pour la pêche
/best_zones - Zones optimales en ce moment

*3. SÉCURITÉ*
/conditions - Voir les niveaux de sécurité maritime
/alert - Configurer des seuils d'alerte personnalisés
/alerts - Recevoir les alertes en temps réel

*4. ANALYSE*
/stats - Statistiques 7 jours d'une zone
/trends - Tendances actuelles
/compare - Comparaison multi-zones

*5. PARAMÈTRES*
/settings - Gérer vos préférences
/favorites - Zones favorites
/notifications - Fréquence des notifications

*6. À PROPOS*
/about - À propos du bot
/data - Source des données

*🔑 CLÉS DE LECTURE*

🌊 *Sécurité Maritime:*
🟢 SÛR - Conditions normales
🟡 VIGILANCE - Attention requise
🟠 PRUDENCE - Déconseillé
🔴 DANGER - NE PAS SORTIR

🎣 *Indice de Pêche:*
🐟🐟🐟 EXCELLENT - Conditions optimales
🐟🐟 BON - Bonnes conditions
🐟 MOYEN - Conditions acceptables
🎣 FAIBLE - Peu favorable

💨 *Légendes:*
🌊 Vagues (mètres)
🌡️ Température (°C)
🌬️ Courants (m/s)
💨 Vent (m/s)
👁️ Visibilité (km)

*💡 CONSEILS*
• Consultez avant chaque sortie
• Activez les notifications pour les alertes
• Personnalisez vos zones favorites
• Configurez vos seuils d'alerte

*📞 SUPPORT*
En cas de problème, contactez @PecheurConnectSupport
    """
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN
    )


async def conditions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande /conditions"""
    data = DataManager.load_current_data()
    
    if not data:
        await update.message.reply_text(
            "❌ Pas de données disponibles. Essayez plus tard.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Grouper par région
    regions = {}
    for zone in data:
        region = zone.get("region", "Autre")
        if region not in regions:
            regions[region] = []
        regions[region].append(zone)
    
    # Créer boutons pour chaque région
    keyboard = []
    for region in sorted(regions.keys()):
        keyboard.append([
            InlineKeyboardButton(f"📍 {region}", callback_data=f"region_{region}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Menu", callback_data="menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = f"""
*🌊 CONDITIONS ACTUELLES*

*{len(data)} zones suivies | {len(regions)} régions*

Sélectionnez une région pour plus de détails:
    """
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche les conditions d'une région"""
    query = update.callback_query
    await query.answer()
    
    region = query.data.replace("region_", "")
    zones = DataManager.get_zones_by_region(region)
    
    if not zones:
        await query.edit_message_text("❌ Pas de zones pour cette région")
        return
    
    msg = MessageFormatter.format_region_summary(region, zones)
    
    # Créer boutons pour chaque zone
    keyboard = []
    for zone in zones:
        keyboard.append([
            InlineKeyboardButton(
                f"📍 {zone.get('zone')} ({zone.get('safety_level')})",
                callback_data=f"zone_detail_{zone.get('zone')}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="conditions")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_zone_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche détails d'une zone"""
    query = update.callback_query
    await query.answer()
    
    zone_name = query.data.replace("zone_detail_", "")
    zone = DataManager.get_zone_by_name(zone_name)
    
    if not zone:
        await query.edit_message_text("❌ Zone non trouvée")
        return
    
    msg = MessageFormatter.format_zone_details(zone)
    
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data=f"stats_{zone_name}"),
         InlineKeyboardButton("🔔 Alerte", callback_data=f"alert_zone_{zone_name}")],
        [InlineKeyboardButton("❤️ Favoris", callback_data=f"fav_{zone_name}"),
         InlineKeyboardButton("🔙 Retour", callback_data="conditions")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche statistiques d'une zone"""
    query = update.callback_query
    await query.answer()
    
    zone_name = query.data.replace("stats_", "")
    stats = DataManager.get_stats(zone_name)
    
    msg = MessageFormatter.format_stats(zone_name, stats)
    
    keyboard = [
        [InlineKeyboardButton("🔙 Retour", callback_data=f"zone_detail_{zone_name}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gère les alertes"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_prefs = user_manager.get_user(user_id)
    
    msg = f"""
*⚠️ GESTION DES ALERTES*

Paramètres actuels:
• Seuil vagues: {user_prefs.alert_threshold_wave}m
• Seuil courants: {user_prefs.alert_threshold_current} m/s
• État: {'✅ Activé' if user_prefs.notification_enabled else '❌ Désactivé'}
• Fréquence: {user_prefs.notification_frequency}

Que souhaitez-vous faire?
    """
    
    keyboard = [
        [InlineKeyboardButton("🌊 Modifier seuil vagues", callback_data="alert_waves")],
        [InlineKeyboardButton("🌬️ Modifier seuil courants", callback_data="alert_current")],
        [InlineKeyboardButton("📢 Fréquence notifications", callback_data="alert_frequency")],
        [InlineKeyboardButton("🔕 Désactiver" if user_prefs.notification_enabled else "🔔 Activer",
                            callback_data="alert_toggle")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Paramètres utilisateur"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_prefs = user_manager.get_user(user_id)
    
    msg = f"""
*⚙️ PARAMÈTRES*

• Zones favorites: {len(user_prefs.favorite_zones)} zone(s)
• Région favorite: {user_prefs.favorite_region or 'Non définie'}
• Langue: {user_prefs.language.upper()}
• Unités: {'°C, m/s' if user_prefs.units == 'metric' else '°F, mph'}

Que souhaitez-vous configurer?
    """
    
    keyboard = [
        [InlineKeyboardButton("❤️ Zones favorites", callback_data="fav_list")],
        [InlineKeyboardButton("📍 Région favorite", callback_data="fav_region")],
        [InlineKeyboardButton("🌐 Langue", callback_data="lang_select")],
        [InlineKeyboardButton("📏 Unités", callback_data="units_select")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retour au menu principal"""
    query = update.callback_query
    await query.answer()
    
    msg = """
*🏠 MENU PRINCIPAL*

Que souhaitez-vous faire?
    """
    
    keyboard = [
        [InlineKeyboardButton("🌊 Conditions", callback_data="conditions"),
         InlineKeyboardButton("🌍 Régions", callback_data="regions_list")],
        [InlineKeyboardButton("🎣 Meilleures zones", callback_data="best_zones"),
         InlineKeyboardButton("⚠️ Alertes", callback_data="alerts")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats_menu"),
         InlineKeyboardButton("⚙️ Paramètres", callback_data="settings")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_best_zones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche les meilleures zones"""
    query = update.callback_query
    await query.answer()
    
    data = DataManager.load_current_data()
    
    if not data:
        await query.edit_message_text("❌ Pas de données")
        return
    
    # Trier par indice de pêche
    safe_zones = [z for z in data if z.get('safety_level') == 'safe']
    safe_zones = sorted(safe_zones, key=lambda z: z.get('danger_score', 100))[:5]
    
    msg = "*🏆 MEILLEURES ZONES EN CE MOMENT*\n\n"
    
    for i, zone in enumerate(safe_zones, 1):
        msg += f"{i}. *{zone.get('zone')}*\n"
        msg += f"   {zone.get('index', 'N/A')}\n"
        msg += f"   {zone.get('safety', 'N/A')}\n"
        msg += f"   🌊 {zone.get('v_now')}m | 🌡️ {zone.get('t_now')}°C\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Compare les zones"""
    query = update.callback_query
    await query.answer()
    
    data = DataManager.load_current_data()
    
    if not data:
        await query.edit_message_text("❌ Pas de données")
        return
    
    msg = MessageFormatter.format_comparison(data)
    
    keyboard = [
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def callback_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ajoute/retire des favoris"""
    query = update.callback_query
    await query.answer()
    
    zone_name = query.data.replace("fav_", "")
    user_id = query.from_user.id
    user_prefs = user_manager.get_user(user_id)
    
    if zone_name in user_prefs.favorite_zones:
        user_prefs.favorite_zones.remove(zone_name)
        msg = f"❌ {zone_name} retiré des favoris"
    else:
        user_prefs.favorite_zones.append(zone_name)
        msg = f"❤️ {zone_name} ajouté aux favoris"
    
    user_manager.save_user(user_prefs)
    
    await query.answer(msg, show_alert=True)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """À propos du bot"""
    msg = """
*À PROPOS DE PECHEURCONNECT*

🐟 *Plateforme complète de monitoring maritime*

*Version:* 3.0
*Auteur:* PecheurConnect Team
*Date:* 2026

*Couverture:*
• 18 zones de pêche sénégalaises
• 5 régions
• Données en temps réel

*Sources:*
🌊 Copernicus Marine Data (Vagues, Température, Courants)
🌡️ OpenWeather (Vent, Météo, Humidité)
📊 Calculs propriétaires (Indice de pêche, Sécurité)

*Fonctionnalités:*
✅ Conditions maritime en temps réel
✅ Indice de pêche personnalisé
✅ Alerte personnalisables
✅ Statistiques 7 jours
✅ Notifications automatiques
✅ Historique complet

*Limitations:*
• Mise à jour toutes les heures
• Données côtières uniquement
• Prévisions non disponibles actuellement

*Confidentiel:*
Vos données personnelles sont stockées localement et non partagées.

*Aide:* /help
*Feedback:* @PecheurConnectSupport
    """
    
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN
    )


# ============================================================================
# BROADCAST NOTIFICATIONS
# ============================================================================

async def send_alert_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envoie les alertes basées sur les préférences"""
    try:
        data = DataManager.load_current_data()
        
        if not data:
            return
        
        # Récupérer tous les utilisateurs en DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE notification_enabled = 1')
        users = cursor.fetchall()
        conn.close()
        
        for (user_id,) in users:
            user_prefs = user_manager.get_user(user_id)
            
            # Filtrer les zones de l'utilisateur
            if user_prefs.favorite_zones:
                zones_to_check = [z for z in data if z.get('zone') in user_prefs.favorite_zones]
            elif user_prefs.favorite_region:
                zones_to_check = DataManager.get_zones_by_region(user_prefs.favorite_region)
            else:
                zones_to_check = data
            
            # Vérifier les seuils
            alert_zones = [
                z for z in zones_to_check
                if z.get('v_now', 0) > user_prefs.alert_threshold_wave or
                   z.get('c_now', 0) > user_prefs.alert_threshold_current
            ]
            
            if alert_zones:
                msg = "*⚠️ ALERTE CONDITIONS MARITIMES*\n\n"
                for zone in alert_zones[:3]:
                    msg += f"🚨 *{zone.get('zone')}*\n"
                    msg += f"   {zone.get('safety', 'N/A')}\n"
                    msg += f"   🌊 {zone.get('v_now')}m | 🌬️ {zone.get('c_now')} m/s\n\n"
                
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except TelegramError as e:
                    logger.warning(f"Failed to send alert to {user_id}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error sending alerts: {str(e)}")


async def send_daily_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envoie le résumé quotidien"""
    try:
        data = DataManager.load_current_data()
        
        if not data:
            return
        
        # Récupérer tous les utilisateurs
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE notification_enabled = 1')
        users = cursor.fetchall()
        conn.close()
        
        for (user_id,) in users:
            user_prefs = user_manager.get_user(user_id)
            
            # Filtrer les zones
            if user_prefs.favorite_zones:
                zones = [z for z in data if z.get('zone') in user_prefs.favorite_zones]
            elif user_prefs.favorite_region:
                zones = DataManager.get_zones_by_region(user_prefs.favorite_region)
            else:
                zones = data[:5]  # Top 5
            
            if not zones:
                continue
            
            msg = MessageFormatter.format_region_summary(
                zones[0].get('region', 'Résumé'),
                zones
            )
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            except TelegramError as e:
                logger.warning(f"Failed to send summary to {user_id}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error sending summaries: {str(e)}")


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Démarre le bot"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN non défini")
        exit(1)
    
    print("🤖 Démarrage du bot PecheurConnect v3.0...")
    
    # Créer l'application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Commandes simples
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("conditions", conditions_command))
    app.add_handler(CommandHandler("about", about_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_conditions, pattern="^conditions$"))
    app.add_handler(CallbackQueryHandler(callback_zone_detail, pattern="^zone_detail_"))
    app.add_handler(CallbackQueryHandler(callback_stats, pattern="^stats_"))
    app.add_handler(CallbackQueryHandler(callback_alerts, pattern="^alerts$"))
    app.add_handler(CallbackQueryHandler(callback_best_zones, pattern="^best_zones$"))
    app.add_handler(CallbackQueryHandler(callback_compare, pattern="^compare$"))
    app.add_handler(CallbackQueryHandler(callback_settings, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(callback_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(callback_favorite, pattern="^fav_"))
    
    # Jobs (notifications)
    job_queue = app.job_queue
    job_queue.run_repeating(send_alert_notifications, interval=3600, first=60)  # Chaque heure
    job_queue.run_daily(send_daily_summary, time=datetime.now().replace(hour=8, minute=0))  # 8h
    
    # Démarrer le bot
    print("✅ Bot démarré et en écoute...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
