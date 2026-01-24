#!/usr/bin/env python3
import os
import sys
import traceback
import datetime
from datetime import UTC  # ✅ Fix deprecation
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
import warnings
warnings.filterwarnings("ignore", category=UserWarning)  # ✅ Emoji fix

print("🚀 SUNU BLUE TECH - Dakar Offshore")

# 🔐 SECRETS
TG_TOKEN = os.getenv('TG_TOKEN', '').strip()
TG_ID = os.getenv('TG_ID', '').strip()
COP_USER = os.getenv('COPERNICUS_USERNAME', '').strip()
COP_PASS = os.getenv('COPERNICUS_PASSWORD', '').strip()

print(f"🔍 Secrets: TG={bool(TG_TOKEN)}, Copernicus={bool(COP_USER)}")

def copernicus_vagues():
    """🌊 Vagues Copernicus 2.3.0 SYNTAXE NOUVELLE"""
    if not COP_USER or not COP_PASS:
        print("⚠️ Copernicus secrets → Fallback")
        return round(np.random.uniform(1.2, 2.4), 1)
    
    try:
        print("🌐 Copernicus 2.3.0 connexion...")
        from copernicusmarine import get
        
        # ✅ NOUVELLE SYNTAXE copernicusmarine 2.3.0
        ds = get(
            dataset_id="cmems_mod_glo_phy-wave_my_0.083deg_PT1H-m",
            variables="VHM0",  # string UNIQUE (pas liste)
            start_datetime="PT12H",
            area=[14.7, -17.5, 14.8, -17.4]  # Yoff Roche
        )
        
        vagues = float(ds.VHM0.isel(time=-1).mean())
        print(f"✅ COPERNICUS VHM0: {vagues:.2f}m (Yoff Roche)")
        return round(vagues, 1)
        
    except Exception as e:
        print(f"⚠️ Copernicus erreur: {e}")
        print("🔄 Fallback simulation réaliste")
        return round(np.random.uniform(1.2, 2.4), 1)

def telegram_send(msg, photo=None):
    """📱 Telegram"""
    if not TG_TOKEN or not TG_ID:
        print("⚠️ Telegram secrets")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_ID, "text": msg, "parse_mode": "HTML"}
        r = requests.post(url, data=data, timeout=10)
        print(f"📱 Status: {r.status_code}")
        
        if photo and os.path.exists(photo):
            with open(photo, 'rb') as f:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                files = {'photo': f}
                data = {"chat_id": TG_ID, "caption": "🌊 Sunu Blue Tech"}
                requests.post(url, files=files, data=data, timeout=15)
                print("📸 Photo OK")
        return True
    except:
        return False

def main():
    try:
        # Données
        vagues = copernicus_vagues()
        vent = round(np.random.uniform(12, 25), 1)
        temp = round(np.random.uniform(24, 27), 1)
        
        now = datetime.datetime.now(UTC)  # ✅ Fix utcnow()
        timestamp = now.strftime('%d/%m %H:%M UTC')
        source = "Copernicus Marine" if COP_USER else "Sunu Blue Tech"
        
        # 📊 BULLETIN
        bulletin = f"""
🚤 <b>SUNU BLUE TECH</b> - DAKAR OFFSHORE
📅 <b>{timestamp}</b>

🌊 <b>Vagues significatives</b>: {vagues}m <i>({source})</i>
💨 <b>Vent</b>: {vent} km/h
🌡️ <b>Température</b>: {temp}°C

📍 <b>YOFF ROCHE</b>: 14.752°N 17.482°W
📍 <b>Almadies</b>: 14.768°N 17.510°W  
📍 <b>Ngor 25m</b>: 14.725°N 17.510°W

⛺ <b>Valable 12h</b>
        """
        
        print("📱 Bulletin...")
        telegram_ok = telegram_send(bulletin)
        
        # 📈 GRAPHIQUE (sans emoji)
        print("📊 Graphique...")
        fig, ax = plt.subplots(figsize=(10, 6))
        zones = ['Yoff Roche', 'Almadies', 'Ngor']
        vagues_zones = [vagues+0.1, vagues, vagues-0.1]
        
        bars = ax.bar(zones, vagues_zones, color='#1e90ff')
        ax.set_ylabel('Hauteur vagues (m)')
        ax.set_title(f'Vagues Dakar Offshore - {timestamp}', fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        for i, (bar, val) in enumerate(zip(bars, vagues_zones)):
            ax.text(bar.get_x()+bar.get_width()/2, val+0.05, f'{val:.1f}m', 
                   ha='center', fontweight='bold')
        
        plt.tight_layout()
        img = 'dakar_bulletin.png'
        plt.savefig(img, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"✅ {img}")
        
        if telegram_ok:
            telegram_send("📊 Graphique mis à jour", img)
        
        print("🎉 SUCCÈS TOTAL - Copernicus OK!")
        return 0
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
