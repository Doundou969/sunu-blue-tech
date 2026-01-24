#!/usr/bin/env python3
import os
import sys
import traceback
import requests
import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json

# DEBUG : Vérifier TOUS les secrets
print("🔍 DEBUG - Vérification des variables d'environnement :")
print(f"TG_TOKEN: {'OK' if os.getenv('TG_TOKEN') else '❌ MANQUANT'}")
print(f"TG_ID: {'OK' if os.getenv('TG_ID') else '❌ MANQUANT'}")
print(f"COPERNICUS_USER: {'OK' if os.getenv('COPERNICUS_USERNAME') else '❌ MANQUANT'}")

TG_TOKEN = os.getenv('TG_TOKEN')
TG_ID = os.getenv('TG_ID')

def safe_main():
    """Version SAFE avec try/catch complet"""
    try:
        print("🚀 Sunu Blue Tech - Bulletin Pêche Dakar")
        
        # Données simulées (pas de Copernicus pour test)
        vagues = round(np.random.uniform(0.8, 2.5), 2)
        vent = round(np.random.uniform(8, 25), 1)
        temp = round(np.random.uniform(22.5, 26.8), 1)
        
        print(f"📊 Données: vagues={vagues}m, vent={vent}km/h, temp={temp}°C")
        
        # Bulletin Telegram
        bulletin = f"""
🚤 <b>BULLETIN PÊCHE DAKAR</b> - {datetime.datetime.now().strftime('%d/%m %Hh')}

🌊 <b>Vagues significatives</b>: {vagues}m
💨 <b>Vent</b>: {vent} km/h
🌡️ <b>Temp. surface</b>: {temp}°C

📍 Zone: Dakar Offshore
⏰ Valable: 12h
        """
        
        print("📱 Envoi Telegram...")
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_ID, "text": bulletin, "parse_mode": "HTML"}
        response = requests.post(url, data=data, timeout=10)
        print(f"✅ Telegram OK: {response.status_code}")
        
        # Graphique
        print("📈 Création graphique...")
        fig, ax = plt.subplots(figsize=(10, 6))
        zones = ['Dakar\nNord', 'Dakar\nCentre', 'Dakar\nSud']
        vagues_data = [vagues+0.2, vagues, vagues-0.3]
        
        bars = ax.bar(zones, vagues_data, color=['#1e90ff', '#00bfff', '#87cefa'])
        ax.set_ylabel('Hauteur vagues (m)')
        ax.set_title('📊 Conditions vagues - Dakar Offshore', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        for bar, val in zip(bars, vagues_data):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                   f'{val:.1f}m', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        img_path = "bulletin_gps.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Image sauvée: {img_path}")
        
        # Envoi image (optionnel)
        if os.path.exists(img_path):
            print("📸 Envoi image Telegram...")
            with open(img_path, 'rb') as img:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                files = {"photo": img}
                data = {"chat_id": TG_ID, "caption": "📊 Bulletin GPS Dakar"}
                response = requests.post(url, files=files, data=data, timeout=10)
                print(f"✅ Image envoyée: {response.status_code}")
        
        print("🎉 TOUT OK !")
        return 0
        
    except Exception as e:
        print(f"❌ ERREUR FATALE: {str(e)}")
        print("TRACEBACK COMPLET:")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = safe_main()
    print(f"EXIT CODE FINAL: {exit_code}")
    sys.exit(exit_code)
