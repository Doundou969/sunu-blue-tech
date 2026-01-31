import os
import json
import asyncio
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Bibliothèques pour le suivi et l'affichage
from rich.console import Console
from rich.table import Table
from tqdm import tqdm
from telegram import Bot

# Chargement des variables d'environnement
load_dotenv()
console = Console()

# --- CONFIGURATION DES ZONES ---
ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.50},
    "KAYAR": {"lat": 14.92, "lon": -17.20},
    "DAKAR-YOFF": {"lat": 14.75, "lon": -17.48},
    "MBOUR-JOAL": {"lat": 14.41, "lon": -16.96},
    "CASAMANCE": {"lat": 12.50, "lon": -16.70},
    "LOUGA-POTOU": {"lat": 15.48, "lon": -16.75}
}

# --- RÉCUPÉRATION DES DONNÉES COPERNICUS ---
def get_marine_data():
    console.print("[bold blue]📡 Connexion au service Copernicus Marine...[/bold blue]")
    try:
        import copernicusmarine as cm
        
        # Chargement du dataset Waves (VHM0)
        ds = cm.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H",
            username=os.getenv("COPERNICUS_USERNAME"),
            password=os.getenv("COPERNICUS_PASSWORD")
        )

        results = []
        for name, coords in tqdm(ZONES.items(), desc="Analyse des zones"):
            # Extraction du dernier point temporel
            point = ds.sel(latitude=coords["lat"], longitude=coords["lon"], method="nearest").isel(time=-1)
            vhm0 = float(point["VHM0"].values)
            
            # Logique d'alerte
            status = "🔴 DANGER" if vhm0 >= 2.2 else "🟢 OK"
            
            results.append({
                "zone": name,
                "lat": coords["lat"],
                "lon": coords["lon"],
                "vhm0": round(vhm0, 2),
                "temp": 24.5, # Valeur fixe ou à extraire d'un dataset Physics
                "wind_speed": 15,
                "wind_dir": "N",
                "alert": status,
                "trend": "↗",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "Copernicus Marine"
            })
        return results

    except Exception as e:
        console.print(f"[bold red]❌ Erreur Copernicus : {e}[/bold red]")
        return None

# --- ENVOI ALERTE TELEGRAM (ASYNC) ---
async def send_telegram_alert(data):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_ID")
    
    if not token or not chat_id:
        return

    bot = Bot(token=token)
    dangers = [z for z in data if "DANGER" in z['alert']]
    
    if dangers:
        msg = "⚠️ *ALERTE SÉCURITÉ PECHEURCONNECT* ⚠️\n\n"
        for d in dangers:
            msg += f"📍 *{d['zone']}*\n🌊 Houle : {d['vhm0']}m\n📢 État : DANGER EXTRÊME\n\n"
        
        msg += "🔗 [Voir la carte en direct](https://doundou969.github.io/sunu-blue-tech/)"
        
        try:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            console.print("[bold green]📲 Alerte Telegram envoyée aux pêcheurs ![/bold green]")
        except Exception as e:
            console.print(f"[red]Erreur envoi Telegram : {e}[/red]")

# --- AFFICHAGE DU BILAN DANS LE TERMINAL ---
def print_summary(data):
    table = Table(title="PecheurConnect - État de la Mer (Sénégal)")
    table.add_column("Zone", style="cyan", no_wrap=True)
    table.add_column("Houle (VHM0)", justify="right")
    table.add_column("Alerte", justify="center")

    for z in data:
        color = "red" if "DANGER" in z['alert'] else "green"
        table.add_row(z['zone'], f"{z['vhm0']} m", f"[{color}]{z['alert']}[/]")
    
    console.print(table)

# --- EXECUTION PRINCIPALE ---
async def main():
    # 1. Obtenir les données
    data = get_marine_data()
    
    if data:
        # 2. Sauvegarder localement pour GitHub Pages
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 3. Afficher le résumé Rich
        print_summary(data)
        
        # 4. Envoyer les alertes Telegram
        await send_telegram_alert(data)
    else:
        console.print("[red]Abandon : Impossible de générer data.json[/red]")

if __name__ == "__main__":
    asyncio.run(main())
