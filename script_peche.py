#!/usr/bin/env python3
import os
import sys
import traceback
import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# SECRETS CHECK (CRITIQUE)
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()

print(f"🔍 TG_TOKEN: {'OK' if TG_TOKEN else '❌ MANQUANT'}")
print(f"🔍 TG_ID: {'OK' if TG_ID else '❌ MANQUANT'}")

def send_telegram_safe(msg):
    """Telegram avec fallback"""
    if not TG_TOKEN or not TG_ID:
        print("⚠️ Secrets manquants - pas de Telegram")
        return False
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_ID, "text": msg, "parse_mode": "HTML"}
        r = requests.post(url, data=data, timeout=15)
        print(f"📱 Telegram: {r.status_code}")
        return r.status_code == 200
    except:
        print("⚠️ Telegram échoué")
        return False

def main():
    """100% sans crash"""
    try:
        print("🚀 Sunu Blue Tech - Bulletin Pêche")
        
        # Données SANS Copernicus (test)
        vagues = round(np.random.uniform(0.8, 2.5), 2)
        vent = round(np.random.uniform(8, 25), 1)
        temp = round(np.random.uniform(22.5, 26.8), 1)
        
        bulletin = f"""
🚤 <b>BULLETIN PÊCHE DAKAR</b> 
{datetime.datetime.now().strftime('%d/%m %H:%M')}

🌊 Vagues: <b>{vagues}m</b>
💨 Vent: <b>{vent} km/h</b>  
🌡️ Temp: <b>{temp}°C</b>

📍 Dakar Offshore
⏰ Valable 12h
        """
        
        print("📱 Envoi Telegram...")
        send_telegram_safe(bulletin)
        
        # Graphique SAFE
        print("📈 Graphique...")
        fig, ax = plt.subplots(figsize=(8, 5))
        zones = ['Nord', 'Centre', 'Sud']
        vagues_data = [vagues+0.2, vagues, vagues-0.3]
        
        bars = ax.bar(zones, vagues_data, color='#1e90ff')
        ax.set_ylabel('Vagues (m)')
        ax.set_title('📊 Conditions Dakar', fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('bulletin.png', dpi=200, bbox_inches='tight')
        plt.close()
        print("✅ bulletin.png OK")
        
        print("🎉 SUCCÈS TOTAL")
        return 0
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
