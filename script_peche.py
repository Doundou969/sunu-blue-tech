import os
import json
import asyncio
import numpy as np
import pandas as pd
import xarray as xr
import copernicusmarine as cm
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from tqdm import tqdm
import warnings

# Ignorer les warnings
warnings.filterwarnings('ignore')

load_dotenv()

console = Console()

# Configuration des zones de pêche au Sénégal
ZONES = {
    "SAINT-LOUIS": {"lat": 16.05, "lon": -16.65, "desc": "Ndar - Nord"},
    "KAYAR": {"lat": 14.95, "lon": -17.35, "desc": "Kayar - Centre-Nord"},
    "DAKAR-YOFF": {"lat": 14.80, "lon": -17.65, "desc": "Dakar - Capitale"},
    "MBOUR-JOAL": {"lat": 14.35, "lon": -17.15, "desc": "Petite Côte"},
    "CASAMANCE": {"lat": 12.50, "lon": -16.95, "desc": "Ziguinchor - Sud"}
}

# Seuils de sécurité optimisés
THRESHOLDS = {
    "DANGER": {"wave": 3.0, "current": 1.0, "wind": 15.0},
    "WARNING": {"wave": 2.1, "current": 0.6, "wind": 12.0},
    "CAUTION": {"wave": 1.5, "current": 0.4, "wind": 8.0}
}

# Configuration Copernicus Marine
DATASETS = {
    "temperature": "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
    "current": "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i",
    "waves": "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
}


class PecheurConnectLogger:
    """Gestionnaire de logs avancé pour PecheurConnect"""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"log_{datetime.now().strftime('%Y%m')}.txt"
        self.errors = []
        self.warnings = []
        self.infos = []
    
    def log(self, message, level="INFO"):
        """Enregistre un message avec Rich console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Affichage console avec Rich
        if level == "ERROR":
            console.print(f"[bold red]❌ {message}[/bold red]")
            self.errors.append(message)
        elif level == "WARNING":
            console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")
            self.warnings.append(message)
        elif level == "SUCCESS":
            console.print(f"[bold green]✅ {message}[/bold green]")
        else:
            console.print(f"[cyan]ℹ️  {message}[/cyan]")
        
        self.infos.append(log_entry)
        
        # Écriture dans le fichier
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def log_execution(self, success, zones_count, errors_count, duration):
        """Enregistre le résumé d'une exécution avec statistiques"""
        status = "SUCCESS" if success else "FAILURE"
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "zones_processed": zones_count,
            "zones_total": len(ZONES),
            "errors": errors_count,
            "duration_seconds": round(duration, 2),
            "error_details": self.errors,
            "warnings": self.warnings
        }
        
        history_file = self.log_dir / "execution_history.json"
        
        # Charger l'historique existant
        history = []
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []
        
        # Ajouter la nouvelle exécution
        history.append(summary)
        
        # Garder seulement les 100 dernières exécutions
        history = history[-100:]
        
        # Sauvegarder
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        # Afficher le résumé
        self.display_execution_summary(summary)
    
    def display_execution_summary(self, summary):
        """Affiche un résumé visuel de l'exécution"""
        table = Table(title="📊 Résumé de l'Exécution", box=box.ROUNDED)
        table.add_column("Métrique", style="cyan", no_wrap=True)
        table.add_column("Valeur", style="magenta")
        
        status_color = "green" if summary["status"] == "SUCCESS" else "red"
        table.add_row("Statut", f"[{status_color}]{summary['status']}[/{status_color}]")
        table.add_row("Zones traitées", f"{summary['zones_processed']}/{summary['zones_total']}")
        table.add_row("Erreurs", f"[red]{summary['errors']}[/red]" if summary['errors'] > 0 else "[green]0[/green]")
        table.add_row("Durée", f"{summary['duration_seconds']}s")
        table.add_row("Timestamp", summary['timestamp'])
        
        console.print(table)


logger = PecheurConnectLogger()


def calculate_safety_level(v_now, c_now, wind_speed=None):
    """Calcule le niveau de sécurité basé sur vagues, courants et vent"""
    # Calcul basé sur les vagues et courants
    if v_now > THRESHOLDS["DANGER"]["wave"] or c_now > THRESHOLDS["DANGER"]["current"]:
        base_level = ("🔴 DANGER", "danger", "#d32f2f")
    elif v_now > THRESHOLDS["WARNING"]["wave"] or c_now > THRESHOLDS["WARNING"]["current"]:
        base_level = ("🟠 PRUDENCE", "warning", "#ff9800")
    elif v_now > THRESHOLDS["CAUTION"]["wave"] or c_now > THRESHOLDS["CAUTION"]["current"]:
        base_level = ("🟡 VIGILANCE", "caution", "#ffc107")
    else:
        base_level = ("🟢 SÛR", "safe", "#28a745")
    
    # Ajuster selon le vent si disponible
    if wind_speed:
        if wind_speed > THRESHOLDS["DANGER"]["wind"] and base_level[1] != "danger":
            base_level = ("🟠 PRUDENCE", "warning", "#ff9800")
        elif wind_speed > THRESHOLDS["WARNING"]["wind"] and base_level[1] == "safe":
            base_level = ("🟡 VIGILANCE", "caution", "#ffc107")
    
    return base_level


def calculate_fish_index(t_now, c_now, v_now):
    """Calcule l'index de pêche optimisé avec scoring avancé"""
    score = 0
    factors = []
    
    # Température optimale : 18-24°C (zone de plancton et poissons)
    if 18 <= t_now <= 24:
        score += 3
        factors.append("🌡️ Température idéale")
    elif 15 <= t_now <= 27:
        score += 1
        factors.append("🌡️ Température acceptable")
    else:
        factors.append("🌡️ Température non optimale")
    
    # Courants modérés favorables (0.2-0.5 m/s)
    if 0.2 <= c_now <= 0.5:
        score += 2
        factors.append("🧭 Courants favorables")
    elif c_now < 0.2:
        score += 1
        factors.append("🧭 Courants faibles")
    else:
        factors.append("🧭 Courants forts")
    
    # Mer calme (vagues < 1.5m)
    if v_now < 1.0:
        score += 3
        factors.append("🌊 Mer très calme")
    elif v_now < 1.5:
        score += 2
        factors.append("🌊 Mer calme")
    elif v_now < 2.0:
        score += 1
        factors.append("🌊 Mer modérée")
    else:
        factors.append("🌊 Mer agitée")
    
    # Déterminer le niveau
    if score >= 7:
        return "🐟🐟🐟 EXCELLENT", "excellent", factors
    elif score >= 5:
        return "🐟🐟 BON", "good", factors
    elif score >= 3:
        return "🐟 MOYEN", "moderate", factors
    else:
        return "🎣 FAIBLE", "poor", factors


def generate_recommendations(safety_level, fish_level, v_now, c_now, t_now):
    """Génère des recommandations intelligentes"""
    recommendations = []
    
    # Recommandations de sécurité
    if safety_level == "danger":
        recommendations.append("⛔ NE PAS SORTIR EN MER - Conditions dangereuses")
        recommendations.append("🏠 Restez à quai et surveillez les alertes")
    elif safety_level == "warning":
        recommendations.append("⚠️ Sortie fortement déconseillée")
        recommendations.append("📱 Si sortie nécessaire, restez près des côtes")
        recommendations.append("🦺 Équipement de sécurité OBLIGATOIRE")
    elif safety_level == "caution":
        recommendations.append("⚠️ Vigilance accrue recommandée")
        recommendations.append("👥 Privilégiez les sorties en groupe")
    else:
        recommendations.append("✅ Conditions sûres pour la navigation")
    
    # Recommandations de pêche
    if fish_level == "excellent":
        recommendations.append("🎣 Conditions OPTIMALES pour la pêche")
        recommendations.append("🐟 Forte probabilité de bonnes prises")
    elif fish_level == "good":
        recommendations.append("🎣 Bonnes conditions de pêche")
        recommendations.append("🐟 Activité des poissons favorable")
    elif fish_level == "moderate":
        recommendations.append("🎣 Pêche possible mais conditions moyennes")
    else:
        recommendations.append("🎣 Conditions de pêche peu favorables")
    
    # Recommandations spécifiques
    if v_now > 2.5:
        recommendations.append("🌊 Vagues importantes - Attention aux chavirement")
    if c_now > 0.7:
        recommendations.append("🧭 Courants forts - Risque de dérive")
    if t_now < 18:
        recommendations.append("❄️ Eau froide - Poissons en profondeur")
    elif t_now > 26:
        recommendations.append("🌡️ Eau chaude - Poissons près de la surface")
    
    return recommendations


async def fetch_marine_data():
    """Récupère les données marines avec progress bar et optimisations"""
    results = []
    errors = 0
    now = datetime.utcnow()
    next_24h = now + timedelta(hours=24)
    
    user = os.getenv("COPERNICUS_USERNAME")
    pw = os.getenv("COPERNICUS_PASSWORD")
    
    if not user or not pw:
        logger.log("Identifiants Copernicus manquants dans .env", "ERROR")
        return None, len(ZONES)
    
    console.print(Panel.fit(
        "[bold cyan]🌊 PECHEURCONNECT - Collecte des Données Marines[/bold cyan]",
        border_style="cyan"
    ))
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # Connexion
            task_login = progress.add_task("[cyan]Connexion à Copernicus...", total=1)
            cm.login(username=user, password=pw)
            progress.update(task_login, advance=1)
            logger.log("Connexion Copernicus réussie", "SUCCESS")
            
            # Chargement des datasets
            task_datasets = progress.add_task("[cyan]Chargement des datasets...", total=3)
            
            ds_temp = cm.open_dataset(
                dataset_id=DATASETS["temperature"],
                username=user,
                password=pw
            )
            progress.update(task_datasets, advance=1)
            
            ds_cur = cm.open_dataset(
                dataset_id=DATASETS["current"],
                username=user,
                password=pw
            )
            progress.update(task_datasets, advance=1)
            
            ds_wav = cm.open_dataset(
                dataset_id=DATASETS["waves"],
                username=user,
                password=pw
            )
            progress.update(task_datasets, advance=1)
            
            logger.log("Datasets chargés avec succès", "SUCCESS")
            
            # Traitement des zones
            task_zones = progress.add_task("[cyan]Traitement des zones...", total=len(ZONES))
            
            for name, coords in ZONES.items():
                try:
                    progress.update(task_zones, description=f"[cyan]Traitement {name}...")
                    
                    # === DONNÉES ACTUELLES ===
                    
                    # Température de surface
                    st = ds_temp.sel(
                        latitude=coords["lat"], 
                        longitude=coords["lon"], 
                        time=now, 
                        method="nearest"
                    )
                    if 'depth' in st.coords: 
                        st = st.isel(depth=0)
                    t_now = round(float(st["thetao"].values.flatten()[0]), 1)
                    
                    # Courants
                    sc = ds_cur.sel(
                        latitude=coords["lat"], 
                        longitude=coords["lon"], 
                        time=now, 
                        method="nearest"
                    )
                    if 'depth' in sc.coords: 
                        sc = sc.isel(depth=0)
                    
                    u = float(sc["uo"].values.flatten()[0])
                    v = float(sc["vo"].values.flatten()[0])
                    c_now = round(float(np.sqrt(u**2 + v**2)), 2)
                    
                    # Direction du courant
                    current_direction = round(float(np.degrees(np.arctan2(v, u))), 1)
                    
                    # Vagues
                    sw = ds_wav.sel(
                        latitude=coords["lat"], 
                        longitude=coords["lon"], 
                        time=now, 
                        method="nearest"
                    )
                    v_now = round(float(sw["VHM0"].values.flatten()[0]), 2)
                    
                    # Période des vagues (si disponible)
                    wave_period = None
                    if "VTPK" in sw.variables:
                        wave_period = round(float(sw["VTPK"].values.flatten()[0]), 1)
                    
                    # === PRÉVISIONS 24H ===
                    forecast = []
                    try:
                        times_wav = ds_wav.sel(
                            latitude=coords["lat"], 
                            longitude=coords["lon"],
                            time=slice(now, next_24h),
                            method="nearest"
                        )
                        
                        # Prendre 8 points (toutes les 3h sur 24h)
                        time_points = times_wav.time.values[:8]
                        
                        for t in time_points:
                            sw_f = ds_wav.sel(
                                latitude=coords["lat"],
                                longitude=coords["lon"],
                                time=t,
                                method="nearest"
                            )
                            
                            v_forecast = round(float(sw_f["VHM0"].values.flatten()[0]), 2)
                            time_dt = pd.to_datetime(t)
                            time_str = time_dt.strftime("%H:%M")
                            
                            forecast.append({
                                "time": time_str,
                                "wave": v_forecast,
                                "timestamp": time_dt.isoformat()
                            })
                        
                    except Exception as e:
                        logger.log(f"Prévisions non disponibles pour {name}: {str(e)}", "WARNING")
                        forecast = []
                    
                    # === CALCULS AVANCÉS ===
                    
                    # Niveau de sécurité
                    safety, safety_level, color = calculate_safety_level(v_now, c_now)
                    
                    # Index de pêche
                    fish, fish_level, fish_factors = calculate_fish_index(t_now, c_now, v_now)
                    
                    # Recommandations
                    recommendations = generate_recommendations(
                        safety_level, fish_level, v_now, c_now, t_now
                    )
                    
                    # Score de danger (0-100)
                    danger_score = min(100, int(
                        (v_now / 4.0) * 40 +  # Vagues pèsent 40%
                        (c_now / 1.5) * 30 +   # Courants pèsent 30%
                        ((30 - t_now) / 15 if t_now < 30 else 0) * 30  # Température 30%
                    ))
                    
                    results.append({
                        "zone": name,
                        "description": coords["desc"],
                        "lat": coords["lat"],
                        "lon": coords["lon"],
                        "v_now": v_now,
                        "wave_period": wave_period,
                        "t_now": t_now,
                        "c_now": c_now,
                        "current_direction": current_direction,
                        "index": fish,
                        "fish_level": fish_level,
                        "fish_factors": fish_factors,
                        "safety": safety,
                        "safety_level": safety_level,
                        "color": color,
                        "danger_score": danger_score,
                        "date": now.strftime("%d/%m %H:%M"),
                        "timestamp": now.isoformat(),
                        "forecast": forecast,
                        "recommendations": recommendations
                    })
                    
                    logger.log(
                        f"{name}: {safety} | Vagues {v_now}m | Pêche {fish}",
                        "SUCCESS"
                    )
                    
                    progress.update(task_zones, advance=1)
                    
                except Exception as e:
                    logger.log(f"Erreur {name}: {str(e)}", "ERROR")
                    errors += 1
                    progress.update(task_zones, advance=1)
                    continue
        
        # Afficher le résumé
        console.print(f"\n[bold green]✅ Traitement terminé: {len(results)}/{len(ZONES)} zones[/bold green]\n")
        
        return results, errors
        
    except Exception as e:
        logger.log(f"Erreur critique: {str(e)}", "ERROR")
        return None, len(ZONES)


def send_telegram_alert(data):
    """Envoie une alerte Telegram enrichie"""
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    
    if not token or not chat_id:
        logger.log("Identifiants Telegram manquants", "WARNING")
        return
    
    # Analyse de la situation
    danger_zones = [z for z in data if z['safety_level'] == "danger"]
    warning_zones = [z for z in data if z['safety_level'] == "warning"]
    caution_zones = [z for z in data if z['safety_level'] == "caution"]
    safe_zones = [z for z in data if z['safety_level'] == "safe"]
    
    # Construction du message
    if danger_zones:
        message = "🚨 *ALERTE DANGER - PECHEURCONNECT* 🚨\n\n"
        message += f"⛔ {len(danger_zones)} zone(s) DANGEREUSE(S)\n"
        message += f"⚠️ NE PAS SORTIR EN MER\n\n"
    elif warning_zones:
        message = "⚠️ *ALERTE PRUDENCE - PECHEURCONNECT*\n\n"
        message += f"🟠 {len(warning_zones)} zone(s) nécessitent PRUDENCE\n\n"
    else:
        message = "🌊 *PECHEURCONNECT - RAPPORT QUOTIDIEN*\n\n"
    
    # Résumé global avec emojis
    message += f"📊 *Résumé Général*\n"
    message += f"✅ Sûr: {len(safe_zones)} | "
    message += f"🟡 Vigilance: {len(caution_zones)}\n"
    message += f"🟠 Prudence: {len(warning_zones)} | "
    message += f"🔴 Danger: {len(danger_zones)}\n\n"
    
    # Détails par zone (seulement les zones avec alerte)
    priority_zones = danger_zones + warning_zones + caution_zones
    if priority_zones:
        message += "⚠️ *ZONES À RISQUE*\n\n"
        for z in priority_zones:
            message += f"━━━━━━━━━━━━━━━\n"
            message += f"📍 *{z['zone']}* ({z['description']})\n"
            message += f"{z['safety']} | Pêche: {z['index']}\n"
            message += f"🌊 Vagues: {z['v_now']}m\n"
            message += f"🌡️ Temp: {z['t_now']}°C | 🧭 Courant: {z['c_now']}m/s\n"
            
            # Prévision sur 6h
            if z.get('forecast') and len(z['forecast']) >= 2:
                next_6h = z['forecast'][:2]
                trend = "↗️" if next_6h[1]['wave'] > z['v_now'] else "↘️"
                message += f"📈 Tendance 6h: {trend} {next_6h[1]['wave']}m\n"
            
            # Top recommandation
            if z.get('recommendations'):
                message += f"💡 {z['recommendations'][0]}\n"
            
            message += "\n"
    
    # Zones sûres (résumé compact)
    if safe_zones:
        message += f"✅ *ZONES SÛRES* ({len(safe_zones)})\n"
        for z in safe_zones:
            message += f"• {z['zone']}: 🌊{z['v_now']}m | 🐟{z['index'].split()[0]}\n"
        message += "\n"
    
    message += f"🕐 Mise à jour: {data[0]['date']} UTC\n"
    message += f"🌐 Consultez la carte: https://doundou969.github.io/sunu-blue-tech/"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }, timeout=10)
        
        if response.status_code == 200:
            logger.log("Alerte Telegram envoyée avec succès", "SUCCESS")
        else:
            logger.log(f"Erreur Telegram: {response.status_code}", "ERROR")
            
    except Exception as e:
        logger.log(f"Erreur envoi Telegram: {str(e)}", "ERROR")


def save_data(data):
    """Sauvegarde les données avec backup"""
    try:
        # Sauvegarder data.json
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.log(f"data.json sauvegardé ({len(data)} zones)", "SUCCESS")
        
        # Créer un backup horodaté
        backup_dir = Path("logs/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"data_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Garder seulement les 30 derniers backups
        backups = sorted(backup_dir.glob("data_*.json"))
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                old_backup.unlink()
                
        logger.log(f"Backup créé: {backup_file.name}", "SUCCESS")
        
        return True
        
    except Exception as e:
        logger.log(f"Erreur sauvegarde: {str(e)}", "ERROR")
        return False


def generate_statistics(data):
    """Génère des statistiques détaillées"""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "total_zones": len(data),
        "safety_breakdown": {
            "safe": len([z for z in data if z['safety_level'] == "safe"]),
            "caution": len([z for z in data if z['safety_level'] == "caution"]),
            "warning": len([z for z in data if z['safety_level'] == "warning"]),
            "danger": len([z for z in data if z['safety_level'] == "danger"])
        },
        "fish_breakdown": {
            "excellent": len([z for z in data if z['fish_level'] == "excellent"]),
            "good": len([z for z in data if z['fish_level'] == "good"]),
            "moderate": len([z for z in data if z['fish_level'] == "moderate"]),
            "poor": len([z for z in data if z['fish_level'] == "poor"])
        },
        "averages": {
            "wave_height": round(np.mean([z['v_now'] for z in data]), 2),
            "temperature": round(np.mean([z['t_now'] for z in data]), 1),
            "current_speed": round(np.mean([z['c_now'] for z in data]), 2),
            "danger_score": round(np.mean([z['danger_score'] for z in data]), 1)
        },
        "extremes": {
            "max_wave": {
                "value": max([z['v_now'] for z in data]),
                "zone": [z['zone'] for z in data if z['v_now'] == max([z['v_now'] for z in data])][0]
            },
            "min_temp": {
                "value": min([z['t_now'] for z in data]),
                "zone": [z['zone'] for z in data if z['t_now'] == min([z['t_now'] for z in data])][0]
            },
            "max_current": {
                "value": max([z['c_now'] for z in data]),
                "zone": [z['zone'] for z in data if z['c_now'] == max([z['c_now'] for z in data])][0]
            }
        }
    }
    
    # Sauvegarder les stats
    stats_file = Path("logs/statistics.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # Afficher les stats
    display_statistics(stats)
    
    return stats


def display_statistics(stats):
    """Affiche les statistiques avec Rich"""
    
    # Tableau de sécurité
    safety_table = Table(title="🚦 Répartition Sécurité", box=box.ROUNDED)
    safety_table.add_column("Niveau", style="cyan")
    safety_table.add_column("Zones", style="magenta", justify="right")
    
    safety_table.add_row("🟢 Sûr", str(stats['safety_breakdown']['safe']))
    safety_table.add_row("🟡 Vigilance", str(stats['safety_breakdown']['caution']))
    safety_table.add_row("🟠 Prudence", str(stats['safety_breakdown']['warning']))
    safety_table.add_row("🔴 Danger", str(stats['safety_breakdown']['danger']))
    
    # Tableau de pêche
    fish_table = Table(title="🐟 Conditions de Pêche", box=box.ROUNDED)
    fish_table.add_column("Niveau", style="cyan")
    fish_table.add_column("Zones", style="magenta", justify="right")
    
    fish_table.add_row("🐟🐟🐟 Excellent", str(stats['fish_breakdown']['excellent']))
    fish_table.add_row("🐟🐟 Bon", str(stats['fish_breakdown']['good']))
    fish_table.add_row("🐟 Moyen", str(stats['fish_breakdown']['moderate']))
    fish_table.add_row("🎣 Faible", str(stats['fish_breakdown']['poor']))
    
    # Tableau moyennes
    avg_table = Table(title="📊 Moyennes", box=box.ROUNDED)
    avg_table.add_column("Métrique", style="cyan")
    avg_table.add_column("Valeur", style="magenta")
    
    avg_table.add_row("Hauteur vagues", f"{stats['averages']['wave_height']}m")
    avg_table.add_row("Température", f"{stats['averages']['temperature']}°C")
    avg_table.add_row("Vitesse courant", f"{stats['averages']['current_speed']}m/s")
    avg_table.add_row("Score danger", f"{stats['averages']['danger_score']}/100")
    
    # Tableau extrêmes
    ext_table = Table(title="⚡ Extrêmes", box=box.ROUNDED)
    ext_table.add_column("Métrique", style="cyan")
    ext_table.add_column("Valeur", style="magenta")
    ext_table.add_column("Zone", style="yellow")
    
    ext_table.add_row(
        "Vagues max",
        f"{stats['extremes']['max_wave']['value']}m",
        stats['extremes']['max_wave']['zone']
    )
    ext_table.add_row(
        "Temp min",
        f"{stats['extremes']['min_temp']['value']}°C",
        stats['extremes']['min_temp']['zone']
    )
    ext_table.add_row(
        "Courant max",
        f"{stats['extremes']['max_current']['value']}m/s",
        stats['extremes']['max_current']['zone']
    )
    
    # Afficher tous les tableaux
    console.print("\n")
    console.print(safety_table)
    console.print(fish_table)
    console.print(avg_table)
    console.print(ext_table)
    console.print("\n")


def main():
    """Point d'entrée principal"""
    start_time = datetime.now()
    
    # Banner
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]🇸🇳 PECHEURCONNECT[/bold cyan]\n"
        "[white]Système de Sécurité Maritime pour le Sénégal[/white]\n"
        f"[dim]Démarré le {start_time.strftime('%d/%m/%Y à %H:%M:%S')}[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    # Récupération des données
    data, errors = asyncio.run(fetch_marine_data())
    
    if not data or len(data) == 0:
        logger.log("Aucune donnée collectée - Arrêt du script", "ERROR")
        duration = (datetime.now() - start_time).total_seconds()
        logger.log_execution(False, 0, errors, duration)
        exit(1)
    
    # Sauvegarde
    if not save_data(data):
        logger.log("Échec de la sauvegarde", "ERROR")
        duration = (datetime.now() - start_time).total_seconds()
        logger.log_execution(False, len(data), errors, duration)
        exit(1)
    
    # Statistiques
    stats = generate_statistics(data)
    
    # Notification Telegram
    console.print("\n[cyan]📱 Envoi de l'alerte Telegram...[/cyan]")
    send_telegram_alert(data)
    
    # Durée d'exécution
    duration = (datetime.now() - start_time).total_seconds()
    
    # Log d'exécution
    logger.log_execution(True, len(data), errors, duration)
    
    # Banner final
    console.print(Panel.fit(
        f"[bold green]✅ Mise à jour terminée avec succès[/bold green]\n"
        f"[white]Durée: {duration:.2f}s | Zones: {len(data)}/{len(ZONES)} | Erreurs: {errors}[/white]",
        border_style="green",
        box=box.DOUBLE
    ))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]⚠️  Script interrompu par l'utilisateur[/bold red]")
        exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Erreur fatale: {str(e)}[/bold red]")
        logger.log(f"Erreur fatale: {str(e)}", "ERROR")
        exit(1)
