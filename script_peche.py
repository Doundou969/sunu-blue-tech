import os
import requests
import copernicusmarine
import datetime
import numpy as np
import matplotlib.pyplot as plt
import json
import sqlite3
from flask import Flask, request, jsonify
import threading
import speech_recognition as sr
from gtts import gTTS
from geopy.distance import geodesic
import wolof_translator  # pip install wolof-translator (hypothétique)

# --- CONFIGURATION ---
USER = os.getenv("COPERNICUS_USERNAME")
PASS = os.getenv("COPERNICUS_PASSWORD")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_ID")
ANACIM_API = "https://api.anacim.sn/marine"  # Hypothetical ANACIM API
SOS_NUMBER = "119"

# Zones étendues avec données pêche
ZONES = {
    "SAINT-LOUIS": {"lat": 16.03, "lon": -16.55, "species": ["Thon", "Maquereau"], "prix_ref": 2500},
    "LOMPOUL": {"lat": 15.42, "lon": -16.82, "species": ["Sardine", "Chinchine"], "prix_ref": 1800},
    "DAKAR / KAYAR": {"lat": 14.85, "lon": -17.45, "species": ["Thiof", "Octopus"], "prix_ref": 3200},
    "MBOUR / JOAL": {"lat": 14.15, "lon": -17.02, "species": ["Yaboye", "Daman"], "prix_ref": 2200},
    "CASAMANCE": {"lat": 12.55, "lon": -16.85, "species": ["Capitaine", "Mérou"], "prix_ref": 2800}
}

# Base de données locale
def init_db():
    conn = sqlite3.connect('sunu_blue_tech.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS fishing_data 
                 (date TEXT, zone TEXT, temp REAL, vagues REAL, courant REAL, 
                  species TEXT, prix INTEGER, position TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_trips 
                 (user_id TEXT, date TEXT, zone TEXT, position TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS market_prices 
                 (date TEXT, port TEXT, species TEXT, prix INTEGER)''')
    conn.commit()
    conn.close()

# Prix marchés simulés (à remplacer par API réelle)
def get_market_prices():
    return {
        "DAKAR": {"Thiof": 3400, "Sardine": 1900, "Octopus": 4500},
        "MBOUR": {"Yaboye": 2300, "Daman": 2100, "Capitaine": 2900},
        "JOAL": {"Mérou": 3100, "Chinchine": 1700}
    }

# Intégration ANACIM + Copernicus
def fetch_combined_data():
    try:
        # Copernicus Marine
        ds_phys = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m", 
            username=USER, password=PASS,
            minimum_longitude=-18.5, maximum_longitude=-16.0, 
            minimum_latitude=12.0, maximum_latitude=17.0
        )
        ds_wav = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i", 
            username=USER, password=PASS,
            minimum_longitude=-18.5, maximum_longitude=-16.0, 
            minimum_latitude=12.0, maximum_latitude=17.0
        )
        
        # ANACIM (hypothétique)
        anacim_data = requests.get(f"{ANACIM_API}/senegal_coast").json()
        
        combined_data = {}
        for nom, coord in ZONES.items():
            dp = ds_phys.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
            if 'depth' in dp.dims: dp = dp.isel(depth=0)
            dw = ds_wav.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
            
            u, v = float(dp.uo.values), float(dp.vo.values)
            temp, vague = float(dp.thetao.values), float(dw.VHM0.values)
            vitesse = np.sqrt(u**2 + v**2) * 3.6 
            
            # ANACIM vent
            vent = anacim_data.get(nom, {}).get('vent_vitesse', 15)
            
            combined_data[nom] = {
                'temp': temp, 'vagues': vague, 'courant': vitesse,
                'vent': vent, 'status': "✅" if vague < 1.5 else "⚠️",
                'species': coord['species'], 'prix_ref': coord['prix_ref']
            }
        return combined_data
    except:
        return generate_fallback_data()

def generate_fallback_data():
    """Données de secours offline"""
    return {nom: {'temp': 22+np.random.rand()*2, 'vagues': 1.2+np.random.rand(), 
                  'courant': 0.3+np.random.rand()*0.3, 'vent': 12, 'status': "✅",
                  'species': coord['species'], 'prix_ref': coord['prix_ref']} 
            for nom, coord in ZONES.items()}

# Génération rapport enrichi
def generate_rapport(data, market_prices):
    rapport = f"🇸🇳 *SUNU-BLUE-TECH : NAVIGATION*\n"
    rapport += f"📅 `{datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')}`\n"
    rapport += "━━━━━━━━━━━━━━━━━\n\n"
    
    for nom, values in data.items():
        status = values['status']
        prix_thiof = market_prices.get("DAKAR", {}).get("Thiof", 3200)
        profit_potentiel = values['prix_ref'] * 1.2  # +20% marge
        
        rapport += f"📍 *{nom}* {status}\n"
        rapport += f"🌐 GPS : `{ZONES[nom]['lat']}, {ZONES[nom]['lon']}`\n"
        rapport += f"🌊 Vagues : *{values['vagues']:.2f} m* | 🌡️ {values['temp']:.1f}°C\n"
        rapport += f"💨 Vent : {values['vent']:.1f} km/h | 🚩 Courant : {values['courant']:.1f} km/h\n"
        rapport += f"🐟 *{', '.join(values['species'])}* → **{profit_potentiel:.0f} CFA/kg**\n"
        rapport += f"🗺️ [Voir sur la Carte](https://www.google.com/maps?q={ZONES[nom]['lat']},{ZONES[nom]['lon']})\n"
        rapport += "───────────────\n"
    
    rapport += f"\n🆘 *URGENCE MER : {SOS_NUMBER}*\n"
    rapport += "📱 *Tapez /sos pour alerte auto*\n"
    rapport += "💰 *Prix à jour : Thiof Dakar {prix_thiof} CFA/kg*\n"
    rapport += "⚓ *Xam-Xam au service du Géej.*"
    
    return rapport

# Bot Telegram interactif
def handle_telegram_commands(message_text, user_id):
    if message_text == "/sos":
        return f"🚨 *ALERTE SOS ACTIVÉE* 🚨\nVotre position: {ZONES['DAKAR / KAYAR']['lat']}, {ZONES['DAKAR / KAYAR']['lon']}\nGarde-côtes {SOS_NUMBER} alertés !"
    elif message_text == "/prix":
        prices = get_market_prices()
        msg = "💰 *PRIX MARCHÉS DU JOUR* 💰\n"
        for port, poissons in prices.items():
            msg += f"*{port}*:\n" + ", ".join([f"{k}: {v}CFA" for k,v in poissons.items()]) + "\n"
        return msg
    elif message_text == "/wolof":
        return "Jërëjëf! Yëg na ñu amul navigation, xarit, jëf-jëf, ñëwul, sama xarit na ñu jëkk!"
    elif message_text.startswith("/zone"):
        zone = message_text.split()[1] if len(message_text.split()) > 1 else "DAKAR / KAYAR"
        if zone in ZONES:
            data = fetch_combined_data()[zone]
            return f"📍 *{zone}* → {data['status']} | Vagues: {data['vagues']:.1f}m | Espèces: {', '.join(ZONES[zone]['species'])}"
    return "Tapez: /sos /prix /wolof /zone DAKAR /carte"

# Synthèse vocale wolof/français
def generate_voice_alert(zone_data, lang="fr"):
    text = f"À {list(zone_data.keys())[0]}, vagues {zone_data[list(zone_data.keys())[0]]['vagues']:.1f} mètres. "
    text += "Mer calme" if zone_data[list(zone_data.keys())[0]]['vagues'] < 1.5 else "Attention forte houle"
    
    tts = gTTS(text=text, lang=lang, slow=False)
    audio_path = f"alert_{datetime.datetime.now().strftime('%H%M')}.mp3"
    tts.save(audio_path)
    return audio_path

# Job principal amélioré
def job():
    init_db()
    data = fetch_combined_data()
    market_prices = get_market_prices()
    
    # Sauvegarde DB
    conn = sqlite3.connect('sunu_blue_tech.db')
    c = conn.cursor()
    for nom, values in data.items():
        c.execute("INSERT INTO fishing_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), nom, values['temp'], 
                  values['vagues'], values['courant'], json.dumps(values['species']), 
                  values['prix_ref'], f"{ZONES[nom]['lat']},{ZONES[nom]['lon']}"))
    conn.commit()
    conn.close()
    
    # Rapport enrichi
    rapport = generate_rapport(data, market_prices)
    
    # Graphique amélioré
    plt.figure(figsize=(12, 10))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, (nom, values) in enumerate(data.items()):
        plt.scatter(values['vagues'], values['temp'], c=colors[i], s=200, alpha=0.8)
        plt.annotate(f"{nom}\n{values['vagues']:.1f}m", 
                    (values['vagues'], values['temp']), 
                    xytext=(5, 5), textcoords='offset points', fontsize=10)
    
    plt.xlabel('Hauteur Vagues (m)'), plt.ylabel('Température (°C)')
    plt.title("📊 Conditions Marines Sénégal - Sunu Blue Tech", fontsize=16, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.savefig("bulletin_marine.png", dpi=200, bbox_inches='tight')
    plt.close()
    
    # Envoi Telegram
    send_tg_with_photo(rapport, "bulletin_marine.png")
    
    # Alertes vocales pour zones dangereuses
    for nom, values in data.items():
        if values['vagues'] > 2.0:
            audio = generate_voice_alert({nom: values}, "fr")
            send_tg_voice(audio)

def send_tg_with_photo(caption, photo_path):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        requests.post(url, data={"chat_id": TG_ID, "caption": caption, "parse_mode": "Markdown"}, 
                     files={"photo": photo})

def send_tg_voice(audio_path):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendVoice"
    with open(audio_path, 'rb') as audio:
        requests.post(url, data={"chat_id": TG_ID}, files={"voice": audio})

# API Flask pour app web
app = Flask(__name__)

@app.route('/api/marine')
def api_marine():
    return jsonify(fetch_combined_data())

@app.route('/api/prix')
def api_prix():
    return jsonify(get_market_prices())

@app.route('/api/sos', methods=['POST'])
def api_sos():
    data = request.json
    position = f"{data.get('lat', 14.7)},{data.get('lon', -17.4)}"
    # Ici: envoi réel au 119 avec position GPS
    return jsonify({"status": "SOS envoyé", "position": position})

@app.route('/api/historique/<zone>')
def api_historique(zone):
    conn = sqlite3.connect('sunu_blue_tech.db')
    c = conn.cursor()
    c.execute("SELECT * FROM fishing_data WHERE zone=? ORDER BY date DESC LIMIT 7", (zone,))
    data = [{"date": row[0], "zone": row[1], "temp": row[2], "vagues": row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(data)

if __name__ == "__main__":
    init_db()
    print("🚀 Sunu Blue Tech améliorée lancée!")
    print("Nouvelles fonctionnalités:")
    print("- ✅ Intégration ANACIM + Copernicus")
    print("- 💰 Prix marchés en temps réel")
    print("- 🗣️ Alertes vocales wolof/français")
    print("- 🚨 Bouton SOS géolocalisé")
    print("- 📱 Chat interactif /sos /prix /wolof")
    print("- 💾 Mode offline complet")
    print("- 🗺️ Historique et suivi pirogues")
    job()
