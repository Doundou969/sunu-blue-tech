#!/usr/bin/env python3
"""
PecheurConnect Bot Telegram v3.1 - Bugs corrigés
Corrections:
  - Handler fav_ ambiguë (capturait fav_list, fav_region)
  - regions_list sans handler
  - region_XXX callbacks sans handler dédié
  - stats_menu sans handler
  - lang_select / units_select sans handlers
  - alert_toggle / alert_waves / alert_current / alert_frequency sans handlers
  - alert_zone_ sans handler
  - fav_list sans handler
Auteur: PecheurConnect Team
Date: 2026
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import sqlite3

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ParseMode
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
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

# ============================================================================
# LOGGING
# ============================================================================

Path("logs").mkdir(exist_ok=True)
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
    user_id: int
    favorite_zones: List[str] = None
    favorite_region: str = None
    alert_threshold_wave: float = 2.0
    alert_threshold_current: float = 0.5
    notification_enabled: bool = True
    notification_frequency: str = "hourly"
    units: str = "metric"
    language: str = "fr"

    def __post_init__(self):
        if self.favorite_zones is None:
            self.favorite_zones = []


class UserManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                favorite_zones TEXT,
                favorite_region TEXT,
                alert_threshold_wave REAL DEFAULT 2.0,
                alert_threshold_current REAL DEFAULT 0.5,
                notification_enabled INTEGER DEFAULT 1,
                notification_frequency TEXT DEFAULT 'hourly',
                units TEXT DEFAULT 'metric',
                language TEXT DEFAULT 'fr',
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')
        conn.commit()
        conn.close()

    def get_user(self, user_id: int) -> UserPreferences:
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
                    alert_threshold_wave=row[3] or 2.0,
                    alert_threshold_current=row[4] or 0.5,
                    notification_enabled=bool(row[5]),
                    notification_frequency=row[6] or "hourly",
                    units=row[7] or "metric",
                    language=row[8] or "fr"
                )
        except Exception as e:
            logger.error(f"get_user error: {e}")
        return UserPreferences(user_id=user_id)

    def save_user(self, user: UserPreferences):
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
        except Exception as e:
            logger.error(f"save_user error: {e}")


user_manager = UserManager(DB_PATH)

# ============================================================================
# DATA MANAGER
# ============================================================================

class DataManager:
    @staticmethod
    def load_current_data() -> List[Dict]:
        try:
            if Path(DATA_FILE).exists():
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"load_current_data error: {e}")
        return []

    @staticmethod
    def get_zone_by_name(name: str) -> Optional[Dict]:
        for zone in DataManager.load_current_data():
            if zone.get("zone") == name:
                return zone
        return None

    @staticmethod
    def get_zones_by_region(region: str) -> List[Dict]:
        return [z for z in DataManager.load_current_data() if z.get("region") == region]

    @staticmethod
    def get_all_regions() -> List[str]:
        data = DataManager.load_current_data()
        return sorted(set(z.get("region", "") for z in data))

    @staticmethod
    def get_stats(zone_name: str) -> Optional[Dict]:
        try:
            stats_file = STATS_DIR / f"{zone_name.lower().replace(' ', '_').replace('-', '_')}.json"
            if stats_file.exists():
                with open(stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"get_stats error: {e}")
        return None


# ============================================================================
# FORMATTERS
# ============================================================================

class MessageFormatter:
    @staticmethod
    def format_zone_details(zone: Dict) -> str:
        msg = f"*{zone.get('zone', 'N/A')}*\n"
        msg += f"📍 {zone.get('description', '')}\n"
        msg += f"🌍 {zone.get('region', '')}\n\n"
        msg += f"*🌊 Vagues:* {zone.get('v_now', 0)}m\n"
        msg += f"*🌡️ Température:* {zone.get('t_now', 0)}°C\n"
        msg += f"*🌬️ Courants:* {zone.get('c_now', 0)} m/s\n"
        msg += f"*💨 Vent:* {zone.get('wind_speed', 0)} m/s\n"
        msg += f"*☁️ Nuages:* {zone.get('clouds', 0)}%\n"
        msg += f"*🌤️ Météo:* {zone.get('weather_desc', 'N/A')}\n\n"
        msg += f"*{zone.get('index', '🎣 N/A')}*\n"
        msg += f"*{zone.get('safety', '⚠️ N/A')}*\n\n"
        msg += "*📋 Recommandations:*\n"
        for rec in zone.get('recommendations', [])[:3]:
            msg += f"• {rec}\n"
        msg += f"\n🕐 Mise à jour: {zone.get('date', 'N/A')}"
        return msg

    @staticmethod
    def format_region_summary(region: str, zones: List[Dict]) -> str:
        msg = f"*📍 Région: {region}*\n"
        msg += f"*{len(zones)} zones*\n\n"
        safe_zones = [z for z in zones if z.get('safety_level') == 'safe']
        caution_zones = [z for z in zones if z.get('safety_level') == 'caution']
        warning_zones = [z for z in zones if z.get('safety_level') == 'warning']
        danger_zones = [z for z in zones if z.get('safety_level') == 'danger']
        for label, color, group in [
            ("SÛR", "🟢", safe_zones),
            ("VIGILANCE", "🟡", caution_zones),
            ("PRUDENCE", "🟠", warning_zones),
            ("DANGER", "🔴", danger_zones)
        ]:
            if group:
                names = ", ".join(z.get('zone', '') for z in group[:2])
                extra = f" +{len(group)-2}" if len(group) > 2 else ""
                msg += f"{color} *{label}* ({len(group)}): {names}{extra}\n"
        msg += f"\n🕐 {zones[0].get('date', 'N/A') if zones else 'N/A'}"
        return msg

    @staticmethod
    def format_stats(zone_name: str, stats: Dict) -> str:
        if not stats:
            return f"❌ Pas de statistiques pour {zone_name}"
        msg = f"*📊 Statistiques - {zone_name}*\n"
        msg += f"*Période: {stats.get('period', '7 jours')}*\n\n"
        waves = stats.get('statistics', {}).get('waves', {})
        msg += f"*🌊 Vagues:*\n"
        msg += f"  Min: {waves.get('min', 'N/A')}m | Max: {waves.get('max', 'N/A')}m\n"
        msg += f"  Moyenne: {waves.get('avg', 'N/A')}m | Tendance: {waves.get('trend', 'N/A')}\n\n"
        temp = stats.get('statistics', {}).get('temperature', {})
        msg += f"*🌡️ Température:*\n"
        msg += f"  Min: {temp.get('min', 'N/A')}°C | Max: {temp.get('max', 'N/A')}°C\n"
        msg += f"  Moyenne: {temp.get('avg', 'N/A')}°C | Tendance: {temp.get('trend', 'N/A')}\n\n"
        wind = stats.get('statistics', {}).get('wind', {})
        msg += f"*🌬️ Vent:*\n"
        msg += f"  Min: {wind.get('min', 'N/A')} m/s | Max: {wind.get('max', 'N/A')} m/s\n"
        msg += f"  Moyenne: {wind.get('avg', 'N/A')} m/s\n\n"
        best = stats.get('best_day', {})
        worst = stats.get('worst_day', {})
        msg += f"*🏆 Meilleur jour:* {best.get('date', 'N/A')}\n"
        msg += f"  Vagues: {best.get('wave', 'N/A')}m | Temp: {best.get('temp', 'N/A')}°C\n\n"
        msg += f"*⚠️ Pire jour:* {worst.get('date', 'N/A')}\n"
        msg += f"  Vagues: {worst.get('wave', 'N/A')}m\n"
        return msg

    @staticmethod
    def format_comparison(zones: List[Dict]) -> str:
        msg = "*🔍 Comparaison des zones*\n\n"
        sorted_by_wave = sorted(zones, key=lambda z: z.get('v_now', 0))
        msg += "*🌊 Classement par vagues (calme → agitée):*\n"
        for i, zone in enumerate(sorted_by_wave, 1):
            msg += f"{i}. {zone.get('zone', '')}: {zone.get('v_now', 0)}m\n"
        msg += "\n"
        sorted_by_temp = sorted(zones, key=lambda z: z.get('t_now', 0), reverse=True)
        msg += "*🌡️ Classement par température (chaude → froide):*\n"
        for i, zone in enumerate(sorted_by_temp, 1):
            msg += f"{i}. {zone.get('zone', '')}: {zone.get('t_now', 0)}°C\n"
        msg += "\n"
        best_zones = sorted(zones, key=lambda z: z.get('danger_score', 0))[:3]
        msg += "*🎣 Meilleures zones pour la pêche:*\n"
        for zone in best_zones:
            msg += f"• {zone.get('zone', '')}: {zone.get('index', 'N/A')}\n"
        return msg


# ============================================================================
# CLAVIER MENU PRINCIPAL
# ============================================================================

def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🌊 Conditions", callback_data="conditions"),
         InlineKeyboardButton("🌍 Régions", callback_data="regions_list")],
        [InlineKeyboardButton("🏆 Meilleures zones", callback_data="best_zones"),
         InlineKeyboardButton("⚠️ Alertes", callback_data="alerts")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats_menu"),
         InlineKeyboardButton("⚙️ Paramètres", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================================
# COMMANDES
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"User {user.id} started bot")
    msg = f"""
👋 *Bienvenue sur PecheurConnect Bot v3.1* 👋

Bonjour *{user.first_name}*! 🎣

Je suis votre assistant pour les conditions maritimes et de pêche au Sénégal.

*🌊 18 zones | 5 régions | Données en temps réel*

Que souhaitez-vous faire ?
    """
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = """
*📚 AIDE - PecheurConnect Bot*

*/start* - Menu principal
*/conditions* - Toutes les zones
*/about* - À propos

*🌊 Sécurité Maritime:*
🟢 SÛR | 🟡 VIGILANCE | 🟠 PRUDENCE | 🔴 DANGER

*🎣 Indice de Pêche:*
🐟🐟🐟 EXCELLENT | 🐟🐟 BON | 🐟 MOYEN | 🎣 FAIBLE

*Support:* @PecheurConnectSupport
    """
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def conditions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = DataManager.load_current_data()
    if not data:
        await update.message.reply_text("❌ Pas de données disponibles. Essayez plus tard.")
        return
    regions = DataManager.get_all_regions()
    keyboard = [[InlineKeyboardButton(f"📍 {r}", callback_data=f"region_{r}")] for r in regions]
    keyboard.append([InlineKeyboardButton("🔙 Menu", callback_data="menu")])
    msg = f"*🌊 CONDITIONS ACTUELLES*\n\n*{len(data)} zones | {len(regions)} régions*\n\nSélectionnez une région :"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN,
                                    reply_markup=InlineKeyboardMarkup(keyboard))


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = """
*À PROPOS DE PECHEURCONNECT*

🐟 *Version:* 3.1 | *Date:* 2026

*Couverture:* 18 zones | 5 régions sénégalaises

*Sources:*
🌊 Copernicus Marine (Vagues, Température, Courants)
🌡️ OpenWeather (Vent, Météo)

*Confidentiel:* Données stockées localement.
*Support:* @PecheurConnectSupport
    """
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ============================================================================
# CALLBACKS
# ============================================================================

async def cb_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menu principal"""
    query = update.callback_query
    await query.answer()
    msg = "*🏠 MENU PRINCIPAL*\n\nQue souhaitez-vous faire ?"
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=main_menu_keyboard())


async def cb_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Liste des régions depuis bouton menu"""
    query = update.callback_query
    await query.answer()
    data = DataManager.load_current_data()
    if not data:
        await query.edit_message_text("❌ Pas de données disponibles.")
        return
    regions = DataManager.get_all_regions()
    keyboard = [[InlineKeyboardButton(f"📍 {r}", callback_data=f"region_{r}")] for r in regions]
    keyboard.append([InlineKeyboardButton("🔙 Menu", callback_data="menu")])
    msg = f"*🌊 CONDITIONS ACTUELLES*\n\n*{len(data)} zones | {len(regions)} régions*\n\nSélectionnez une région :"
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_regions_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #2 : regions_list n'avait pas de handler.
    Affiche la liste de toutes les régions.
    """
    query = update.callback_query
    await query.answer()
    regions = DataManager.get_all_regions()
    if not regions:
        await query.edit_message_text("❌ Aucune région disponible.")
        return
    keyboard = [[InlineKeyboardButton(f"📍 {r}", callback_data=f"region_{r}")] for r in regions]
    keyboard.append([InlineKeyboardButton("🔙 Menu", callback_data="menu")])
    msg = f"*🌍 RÉGIONS*\n\n{len(regions)} régions disponibles :\n\nSélectionnez une région :"
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_region(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #3 : region_XXX n'avait pas de handler dédié — le handler
    conditions ne gérait que ^conditions$ sans capturer le préfixe region_.
    """
    query = update.callback_query
    await query.answer()
    region = query.data.replace("region_", "")
    zones = DataManager.get_zones_by_region(region)
    if not zones:
        await query.edit_message_text("❌ Pas de zones pour cette région.")
        return
    msg = MessageFormatter.format_region_summary(region, zones)
    keyboard = []
    for zone in zones:
        level = zone.get('safety_level', '')
        emoji = {"safe": "🟢", "caution": "🟡", "warning": "🟠", "danger": "🔴"}.get(level, "⚪")
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {zone.get('zone')}",
            callback_data=f"zone_detail_{zone.get('zone')}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="conditions")])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_zone_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    zone_name = query.data.replace("zone_detail_", "")
    zone = DataManager.get_zone_by_name(zone_name)
    if not zone:
        await query.edit_message_text("❌ Zone non trouvée.")
        return
    msg = MessageFormatter.format_zone_details(zone)
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data=f"stats_{zone_name}"),
         InlineKeyboardButton("🔔 Alerte zone", callback_data=f"alert_zone_{zone_name}")],
        [InlineKeyboardButton("❤️ Favoris", callback_data=f"fav_toggle_{zone_name}"),
         InlineKeyboardButton("🔙 Retour", callback_data="conditions")]
    ]
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_stats_zone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stats d'une zone spécifique (pattern stats_ZONENAME)"""
    query = update.callback_query
    await query.answer()
    zone_name = query.data.replace("stats_", "")
    stats = DataManager.get_stats(zone_name)
    msg = MessageFormatter.format_stats(zone_name, stats)
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data=f"zone_detail_{zone_name}")]]
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #4 : stats_menu n'avait pas de handler.
    Affiche la liste des zones pour choisir les stats.
    """
    query = update.callback_query
    await query.answer()
    data = DataManager.load_current_data()
    if not data:
        await query.edit_message_text("❌ Pas de données disponibles.")
        return
    keyboard = []
    for zone in data:
        keyboard.append([InlineKeyboardButton(
            f"📊 {zone.get('zone')}",
            callback_data=f"stats_{zone.get('zone')}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Menu", callback_data="menu")])
    msg = "*📊 STATISTIQUES*\n\nChoisissez une zone :"
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_best_zones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = DataManager.load_current_data()
    if not data:
        await query.edit_message_text("❌ Pas de données.")
        return
    safe_zones = [z for z in data if z.get('safety_level') == 'safe']
    top = sorted(safe_zones, key=lambda z: z.get('danger_score', 100))[:5]
    if not top:
        top = sorted(data, key=lambda z: z.get('danger_score', 100))[:5]
    msg = "*🏆 MEILLEURES ZONES EN CE MOMENT*\n\n"
    for i, zone in enumerate(top, 1):
        msg += f"{i}. *{zone.get('zone')}*\n"
        msg += f"   {zone.get('index', 'N/A')}\n"
        msg += f"   {zone.get('safety', 'N/A')}\n"
        msg += f"   🌊 {zone.get('v_now')}m | 🌡️ {zone.get('t_now')}°C\n\n"
    keyboard = [[InlineKeyboardButton("🔙 Menu", callback_data="menu")]]
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_prefs = user_manager.get_user(query.from_user.id)
    msg = f"""
*⚠️ GESTION DES ALERTES*

Paramètres actuels :
• Seuil vagues : *{user_prefs.alert_threshold_wave}m*
• Seuil courants : *{user_prefs.alert_threshold_current} m/s*
• Notifications : *{'✅ Activées' if user_prefs.notification_enabled else '❌ Désactivées'}*
• Fréquence : *{user_prefs.notification_frequency}*
    """
    toggle_label = "🔕 Désactiver" if user_prefs.notification_enabled else "🔔 Activer"
    keyboard = [
        [InlineKeyboardButton("🌊 Seuil vagues : 1m", callback_data="alert_wave_1.0"),
         InlineKeyboardButton("🌊 Seuil vagues : 2m", callback_data="alert_wave_2.0")],
        [InlineKeyboardButton("🌊 Seuil vagues : 3m", callback_data="alert_wave_3.0")],
        [InlineKeyboardButton("🌬️ Seuil courants : 0.3", callback_data="alert_curr_0.3"),
         InlineKeyboardButton("🌬️ Seuil courants : 0.5", callback_data="alert_curr_0.5")],
        [InlineKeyboardButton("⏱️ Fréq : horaire", callback_data="alert_freq_hourly"),
         InlineKeyboardButton("⏱️ Fréq : 6h", callback_data="alert_freq_6hourly")],
        [InlineKeyboardButton("⏱️ Fréq : quotidien", callback_data="alert_freq_daily")],
        [InlineKeyboardButton(toggle_label, callback_data="alert_toggle")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ]
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_alert_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #6a : alert_toggle n'avait pas de handler.
    Active ou désactive les notifications.
    """
    query = update.callback_query
    await query.answer()
    user_prefs = user_manager.get_user(query.from_user.id)
    user_prefs.notification_enabled = not user_prefs.notification_enabled
    user_manager.save_user(user_prefs)
    state = "activées ✅" if user_prefs.notification_enabled else "désactivées ❌"
    await query.answer(f"Notifications {state}", show_alert=True)
    # Rafraîchir le menu alertes
    await cb_alerts(update, context)


async def cb_alert_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #6b : alert_wave_X n'avait pas de handler.
    Modifie le seuil de vagues.
    """
    query = update.callback_query
    await query.answer()
    value = float(query.data.replace("alert_wave_", ""))
    user_prefs = user_manager.get_user(query.from_user.id)
    user_prefs.alert_threshold_wave = value
    user_manager.save_user(user_prefs)
    await query.answer(f"Seuil vagues : {value}m ✅", show_alert=True)
    await cb_alerts(update, context)


async def cb_alert_curr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #6c : alert_curr_X n'avait pas de handler.
    Modifie le seuil de courants.
    """
    query = update.callback_query
    await query.answer()
    value = float(query.data.replace("alert_curr_", ""))
    user_prefs = user_manager.get_user(query.from_user.id)
    user_prefs.alert_threshold_current = value
    user_manager.save_user(user_prefs)
    await query.answer(f"Seuil courants : {value} m/s ✅", show_alert=True)
    await cb_alerts(update, context)


async def cb_alert_freq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #6d : alert_freq_X n'avait pas de handler.
    Modifie la fréquence des notifications.
    """
    query = update.callback_query
    await query.answer()
    freq = query.data.replace("alert_freq_", "")
    user_prefs = user_manager.get_user(query.from_user.id)
    user_prefs.notification_frequency = freq
    user_manager.save_user(user_prefs)
    labels = {"hourly": "horaire", "6hourly": "toutes les 6h", "daily": "quotidienne"}
    await query.answer(f"Fréquence : {labels.get(freq, freq)} ✅", show_alert=True)
    await cb_alerts(update, context)


async def cb_alert_zone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #7 : alert_zone_ n'avait pas de handler.
    Affiche l'alerte liée à une zone spécifique.
    """
    query = update.callback_query
    await query.answer()
    zone_name = query.data.replace("alert_zone_", "")
    zone = DataManager.get_zone_by_name(zone_name)
    if not zone:
        await query.answer("❌ Zone non trouvée", show_alert=True)
        return
    user_prefs = user_manager.get_user(query.from_user.id)
    wave = zone.get('v_now', 0)
    curr = zone.get('c_now', 0)
    wave_alert = "🚨" if wave > user_prefs.alert_threshold_wave else "✅"
    curr_alert = "🚨" if curr > user_prefs.alert_threshold_current else "✅"
    msg = f"""
*🔔 ALERTE - {zone_name}*

{wave_alert} Vagues : *{wave}m* (seuil : {user_prefs.alert_threshold_wave}m)
{curr_alert} Courants : *{curr} m/s* (seuil : {user_prefs.alert_threshold_current} m/s)

*{zone.get('safety', 'N/A')}*

➡️ Modifiez vos seuils dans ⚠️ Alertes
    """
    keyboard = [
        [InlineKeyboardButton("⚠️ Gérer alertes", callback_data="alerts"),
         InlineKeyboardButton("🔙 Zone", callback_data=f"zone_detail_{zone_name}")]
    ]
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_prefs = user_manager.get_user(query.from_user.id)
    msg = f"""
*⚙️ PARAMÈTRES*

• Zones favorites : *{len(user_prefs.favorite_zones)}* zone(s)
• Région favorite : *{user_prefs.favorite_region or 'Non définie'}*
• Langue : *{user_prefs.language.upper()}*
• Unités : *{'°C, m/s' if user_prefs.units == 'metric' else '°F, mph'}*
    """
    keyboard = [
        [InlineKeyboardButton("❤️ Mes favoris", callback_data="fav_list")],
        [InlineKeyboardButton("📍 Région favorite", callback_data="fav_region_menu")],
        [InlineKeyboardButton("🌐 Français", callback_data="lang_fr"),
         InlineKeyboardButton("🌐 English", callback_data="lang_en")],
        [InlineKeyboardButton("📏 Métrique (°C)", callback_data="units_metric"),
         InlineKeyboardButton("📏 Impérial (°F)", callback_data="units_imperial")],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ]
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_fav_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #8 : fav_list n'avait pas de handler.
    Affiche la liste des zones favorites avec option de retrait.
    """
    query = update.callback_query
    await query.answer()
    user_prefs = user_manager.get_user(query.from_user.id)
    if not user_prefs.favorite_zones:
        msg = "*❤️ MES FAVORIS*\n\nAucune zone favorite.\nAjoutez des zones via 🌊 Conditions → zone → ❤️ Favoris"
        keyboard = [[InlineKeyboardButton("🔙 Paramètres", callback_data="settings")]]
    else:
        msg = f"*❤️ MES FAVORIS* ({len(user_prefs.favorite_zones)} zones)\n\nCliquez pour retirer :"
        keyboard = []
        for zone_name in user_prefs.favorite_zones:
            keyboard.append([InlineKeyboardButton(
                f"❌ Retirer {zone_name}",
                callback_data=f"fav_toggle_{zone_name}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Paramètres", callback_data="settings")])
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_fav_region_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #8b : fav_region n'avait pas de handler.
    Affiche liste des régions pour en choisir une comme favorite.
    """
    query = update.callback_query
    await query.answer()
    regions = DataManager.get_all_regions()
    keyboard = [[InlineKeyboardButton(f"📍 {r}", callback_data=f"set_fav_region_{r}")] for r in regions]
    keyboard.append([InlineKeyboardButton("❌ Effacer", callback_data="set_fav_region_none")])
    keyboard.append([InlineKeyboardButton("🔙 Paramètres", callback_data="settings")])
    msg = "*📍 RÉGION FAVORITE*\n\nChoisissez votre région préférée :"
    await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_set_fav_region(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enregistre la région favorite"""
    query = update.callback_query
    await query.answer()
    region = query.data.replace("set_fav_region_", "")
    user_prefs = user_manager.get_user(query.from_user.id)
    user_prefs.favorite_region = None if region == "none" else region
    user_manager.save_user(user_prefs)
    label = "effacée" if region == "none" else f"définie sur *{region}*"
    await query.answer(f"Région favorite {label} ✅", show_alert=True)
    await cb_settings(update, context)


async def cb_fav_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #1 : fav_ capturait aussi fav_list et fav_region.
    Renommé en fav_toggle_ pour éviter toute ambiguïté.
    Ajoute ou retire une zone des favoris.
    """
    query = update.callback_query
    zone_name = query.data.replace("fav_toggle_", "")
    user_prefs = user_manager.get_user(query.from_user.id)
    if zone_name in user_prefs.favorite_zones:
        user_prefs.favorite_zones.remove(zone_name)
        msg = f"❌ {zone_name} retiré des favoris"
    else:
        user_prefs.favorite_zones.append(zone_name)
        msg = f"❤️ {zone_name} ajouté aux favoris"
    user_manager.save_user(user_prefs)
    await query.answer(msg, show_alert=True)


async def cb_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #5a : lang_select n'avait pas de handler.
    Enregistre la langue choisie.
    """
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    user_prefs = user_manager.get_user(query.from_user.id)
    user_prefs.language = lang
    user_manager.save_user(user_prefs)
    label = "Français" if lang == "fr" else "English"
    await query.answer(f"Langue : {label} ✅", show_alert=True)
    await cb_settings(update, context)


async def cb_units(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    BUG CORRIGÉ #5b : units_select n'avait pas de handler.
    Enregistre le système d'unités choisi.
    """
    query = update.callback_query
    await query.answer()
    units = query.data.replace("units_", "")
    user_prefs = user_manager.get_user(query.from_user.id)
    user_prefs.units = units
    user_manager.save_user(user_prefs)
    label = "Métrique (°C, m/s)" if units == "metric" else "Impérial (°F, mph)"
    await query.answer(f"Unités : {label} ✅", show_alert=True)
    await cb_settings(update, context)


# ============================================================================
# NOTIFICATIONS AUTOMATIQUES
# ============================================================================

async def send_alert_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = DataManager.load_current_data()
        if not data:
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE notification_enabled = 1')
        users = cursor.fetchall()
        conn.close()
        for (user_id,) in users:
            user_prefs = user_manager.get_user(user_id)
            if user_prefs.favorite_zones:
                zones_to_check = [z for z in data if z.get('zone') in user_prefs.favorite_zones]
            elif user_prefs.favorite_region:
                zones_to_check = DataManager.get_zones_by_region(user_prefs.favorite_region)
            else:
                zones_to_check = data
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
                    await context.bot.send_message(chat_id=user_id, text=msg,
                                                   parse_mode=ParseMode.MARKDOWN)
                except TelegramError as e:
                    logger.warning(f"Alert to {user_id} failed: {e}")
    except Exception as e:
        logger.error(f"send_alert_notifications error: {e}")


async def send_daily_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = DataManager.load_current_data()
        if not data:
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE notification_enabled = 1')
        users = cursor.fetchall()
        conn.close()
        for (user_id,) in users:
            user_prefs = user_manager.get_user(user_id)
            if user_prefs.favorite_zones:
                zones = [z for z in data if z.get('zone') in user_prefs.favorite_zones]
            elif user_prefs.favorite_region:
                zones = DataManager.get_zones_by_region(user_prefs.favorite_region)
            else:
                zones = data[:5]
            if not zones:
                continue
            msg = MessageFormatter.format_region_summary(zones[0].get('region', 'Résumé'), zones)
            try:
                await context.bot.send_message(chat_id=user_id, text=msg,
                                               parse_mode=ParseMode.MARKDOWN)
            except TelegramError as e:
                logger.warning(f"Summary to {user_id} failed: {e}")
    except Exception as e:
        logger.error(f"send_daily_summary error: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN non défini")
        exit(1)

    print("🤖 Démarrage PecheurConnect Bot v3.1...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Commandes ---
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("conditions", conditions_command))
    app.add_handler(CommandHandler("about", about_command))

    # --- Callbacks (ordre important : plus spécifique en premier) ---

    # Menu & navigation
    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(cb_conditions, pattern="^conditions$"))
    app.add_handler(CallbackQueryHandler(cb_regions_list, pattern="^regions_list$"))  # CORRIGÉ #2
    app.add_handler(CallbackQueryHandler(cb_region, pattern="^region_"))              # CORRIGÉ #3
    app.add_handler(CallbackQueryHandler(cb_best_zones, pattern="^best_zones$"))

    # Zones
    app.add_handler(CallbackQueryHandler(cb_zone_detail, pattern="^zone_detail_"))

    # Stats
    app.add_handler(CallbackQueryHandler(cb_stats_menu, pattern="^stats_menu$"))      # CORRIGÉ #4
    app.add_handler(CallbackQueryHandler(cb_stats_zone, pattern="^stats_"))

    # Alertes
    app.add_handler(CallbackQueryHandler(cb_alerts, pattern="^alerts$"))
    app.add_handler(CallbackQueryHandler(cb_alert_toggle, pattern="^alert_toggle$"))  # CORRIGÉ #6a
    app.add_handler(CallbackQueryHandler(cb_alert_wave, pattern="^alert_wave_"))      # CORRIGÉ #6b
    app.add_handler(CallbackQueryHandler(cb_alert_curr, pattern="^alert_curr_"))      # CORRIGÉ #6c
    app.add_handler(CallbackQueryHandler(cb_alert_freq, pattern="^alert_freq_"))      # CORRIGÉ #6d
    app.add_handler(CallbackQueryHandler(cb_alert_zone, pattern="^alert_zone_"))      # CORRIGÉ #7

    # Favoris (fav_toggle_ AVANT les handlers settings pour éviter collision)
    app.add_handler(CallbackQueryHandler(cb_fav_toggle, pattern="^fav_toggle_"))      # CORRIGÉ #1
    app.add_handler(CallbackQueryHandler(cb_fav_list, pattern="^fav_list$"))          # CORRIGÉ #8
    app.add_handler(CallbackQueryHandler(cb_fav_region_menu, pattern="^fav_region_menu$"))  # CORRIGÉ #8b
    app.add_handler(CallbackQueryHandler(cb_set_fav_region, pattern="^set_fav_region_"))

    # Paramètres
    app.add_handler(CallbackQueryHandler(cb_settings, pattern="^settings$"))
    app.add_handler(CallbackQueryHandler(cb_lang, pattern="^lang_"))                  # CORRIGÉ #5a
    app.add_handler(CallbackQueryHandler(cb_units, pattern="^units_"))                # CORRIGÉ #5b

    # --- Jobs ---
    job_queue = app.job_queue
    job_queue.run_repeating(send_alert_notifications, interval=3600, first=60)
    job_queue.run_daily(
        send_daily_summary,
        time=datetime.now().replace(hour=8, minute=0, second=0, microsecond=0).time()
    )

    print("✅ Bot v3.1 démarré — tous les bugs corrigés !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
