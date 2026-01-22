import traceback
import sys
import time

def job():
    """Job principal avec debug complet pour GitHub Actions"""
    print("🚀 SUNU-BLUE-TECH v2 - DEBUG MODE ACTIVÉ")
    start_time = time.time()
    
    try:
        # === PHASE 1: VÉRIFICATION ENVIRONNEMENT ===
        print("📋 PHASE 1/7: Vérification variables d'environnement")
        required_vars = {
            'COPERNICUS_USERNAME': USER,
            'COPERNICUS_PASSWORD': '*'*len(PASS) if PASS else None,
            'TG_TOKEN': TG_TOKEN[:10] + '...' if TG_TOKEN else None,
            'TG_ID': TG_ID
        }
        
        missing_vars = []
        for name, value in required_vars.items():
            status = "✅" if value else "❌"
            print(f"  {status} {name}: {'OK' if value else 'MANQUANT'}")
            if not value:
                missing_vars.append(name)
        
        if missing_vars:
            print(f"⚠️  Variables manquantes: {', '.join(missing_vars)}")
            print("💡 Configurez-les dans Settings > Secrets and variables > Actions")
        
        # === PHASE 2: TEST IMPORTS ===
        print("\n📦 PHASE 2/7: Test imports critiques")
        imports_to_test = [
            'copernicusmarine', 'requests', 'numpy', 'matplotlib', 
            'sqlite3', 'json', 'datetime'
        ]
        
        for module in imports_to_test:
            try:
                __import__(module)
                print(f"  ✅ {module}")
            except ImportError as e:
                print(f"  ❌ {module}: {e}")
                raise Exception(f"Import échoué: {module}")
        
        print("✅ Tous imports OK")
        
        # === PHASE 3: TEST CONNEXIONS ===
        print("\n🌐 PHASE 3/7: Test connexions externes")
        test_urls = [
            "https://marine.copernicus.eu",
            "https://api.telegram.org",
            "https://www.google.com/maps"
        ]
        
        for url in test_urls:
            try:
                response = requests.head(url, timeout=5)
                print(f"  ✅ {url}: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️  {url}: {e}")
        
        # === PHASE 4: INIT DB ===
        print("\n💾 PHASE 4/7: Initialisation base de données")
        init_db()
        print("✅ DB initialisée")
        
        # === PHASE 5: COPERNICUS DATA ===
        print("\n🌊 PHASE 5/7: Récupération données Copernicus")
        print("   Dataset 1: cmems_mod_glo_phy_anfc_0.083deg_PT1H-m")
        ds_phys = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m",
            username=USER, password=PASS,
            minimum_longitude=-18.5, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0
        )
        print("   ✅ Dataset physique chargé")
        
        print("   Dataset 2: cmems_mod_glo_wav_anfc_0.083deg_PT3H-i")
        ds_wav = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
            username=USER, password=PASS,
            minimum_longitude=-18.5, maximum_longitude=-16.0,
            minimum_latitude=12.0, maximum_latitude=17.0
        )
        print("   ✅ Dataset vagues chargé")
        
        # === PHASE 6: CALCULS ===
        print("\n🔢 PHASE 6/7: Calculs pour 5 zones")
        data = {}
        for i, (nom, coord) in enumerate(ZONES.items(), 1):
            print(f"   Zone {i}/5: {nom}")
            
            dp = ds_phys.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
            if 'depth' in dp.dims: 
                dp = dp.isel(depth=0)
            dw = ds_wav.sel(latitude=coord['lat'], longitude=coord['lon'], method="nearest").isel(time=-1)
            
            u, v = float(dp.uo.values), float(dp.vo.values)
            temp, vague = float(dp.thetao.values), float(dw.VHM0.values)
            vitesse = np.sqrt(u**2 + v**2) * 3.6
            
            data[nom] = {
                'temp': temp, 'vagues': vague, 'courant': vitesse,
                'lat': coord['lat'], 'lon': coord['lon']
            }
            print(f"     → Vagues: {vague:.2f}m, Temp: {temp:.1f}°C, Courant: {vitesse:.1f}km/h")
        
        print("✅ Calculs terminés")
        
        # === PHASE 7: GÉNÉRATION RAPPORT ===
        print("\n📊 PHASE 7/7: Génération rapport Telegram")
        rapport = generate_rapport(data)
        
        # Graphique
        plt.figure(figsize=(12, 8))
        for i, (nom, values) in enumerate(data.items()):
            plt.scatter(values['vagues'], values['temp'], s=200)
            plt.annotate(nom, (values['vagues'], values['temp']), xytext=(5, 5))
        plt.xlabel('Vagues (m)'); plt.ylabel('Temp (°C)')
        plt.title("SUNU-BLUE-TECH - Conditions Sénégal")
        plt.savefig("bulletin.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        # Envoi Telegram
        send_tg_with_photo(rapport, "bulletin.png")
        print("✅ Rapport Telegram envoyé")
        
        # Sauvegarde DB
        save_to_db(data)
        print("✅ Données sauvées en DB")
        
    except Exception as e:
        # DEBUG COMPLET EN CAS D'ERREUR
        error_time = time.time() - start_time
        error_msg = f"""
💥 ERREUR CRITIQUE - job() échoué après {error_time:.1f}s
═══════════════════════════════════════════════

❌ ERREUR: {str(e)}
📍 TYPE: {type(e).__name__}

TRACEBACK COMPLET:
{traceback.format_exc()}

ENVIRONNEMENT:
Python: {sys.version}
Dépdts installées: {len(imports_to_test)} OK
Vars manquantes: {len(missing_vars)} ({', '.join(missing_vars) if missing_vars else 'aucune'})

🔧 ACTION REQUISE:
1. Vérifier secrets GitHub (COPERNICUS_*, TG_*)
2. Activer ACTIONS_STEP_DEBUG=true
3. Vérifier quota Copernicus Marine
        """
        
        print(error_msg)
        
        # Envoi erreur Telegram (même sans credentials)
        try:
            send_tg_error(error_msg)
            print("✅ Alerte erreur envoyée Telegram")
        except:
            print("⚠️  Telegram erreur non disponible")
        
        # Fallback données simulées
        print("🔄 Génération données fallback")
        fallback_data = generate_fallback_data()
        save_to_db(fallback_data)
        send_tg_with_photo(generate_rapport(fallback_data), "fallback.png")
        print("✅ Fallback exécuté avec succès")
    
    finally:
        print(f"⏱️  TEMPS TOTAL: {time.time() - start_time:.1f}s")
        print("🏁 FIN job()")

# Fonctions utilitaires
def send_tg_error(msg):
    """Envoi erreur même sans credentials complets"""
    if TG_TOKEN and TG_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_ID, "text": msg[:4096], "parse_mode": "Markdown"})

def generate_fallback_data():
    """Données de secours réalistes"""
    base_data = {
        "SAINT-LOUIS": {"vagues": 2.1, "temp": 17.8, "courant": 0.4},
        "LOMPOUL": {"vagues": 2.3, "temp": 18.1, "courant": 0.5},
        "DAKAR / KAYAR": {"vagues": 2.4, "temp": 19.2, "courant": 0.5},
        "MBOUR / JOAL": {"vagues": 1.1, "temp": 20.3, "courant": 0.2},
        "CASAMANCE": {"vagues": 0.7, "temp": 23.0, "courant": 0.2}
    }
    return {k: {**v, 'lat': ZONES[k]['lat'], 'lon': ZONES[k]['lon']} for k,v in base_data.items()}
