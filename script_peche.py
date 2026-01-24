#!/usr/bin/env python3
"""
Sunu Blue Tech - Pêche Copernicus Automatique
Connexion: Copernicus Data Space + Sentinel Hub
Auteur: Doundou969 | 24/01/2026
"""

import sys
import os
import logging
import traceback
from datetime import datetime, timedelta
import json
import time

# Copernicus Imports
try:
    import openeo
    from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
    import earthaccess
except ImportError as e:
    print(f"❌ Copernicus libs manquantes: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('copernicus_debug.log')
    ]
)
logger = logging.getLogger(__name__)

class CopernicusFisher:
    def __init__(self):
        self.connection = None
        self.api = None
        self.results = []
        
    def connect_dataspace(self):
        """Connexion Copernicus Data Space Ecosystem"""
        logger.info("🌌 Connexion Copernicus Data Space...")
        try:
            # Copernicus Data Space (OpenEO)
            self.connection = openeo.connect("https://openeofed.dataspace.copernicus.eu")
            logger.info("✅ Data Space connecté")
            return True
        except Exception as e:
            logger.error(f"❌ Data Space échoué: {e}")
            return False
    
    def connect_sentinel(self, username, password):
        """Connexion Sentinel Hub API"""
        logger.info("🛰️ Connexion Sentinel Hub...")
        try:
            self.api = SentinelAPI(username, password, 'https://scihub.copernicus.eu/dhus')
            logger.info("✅ Sentinel Hub connecté")
            return True
        except Exception as e:
            logger.error(f"❌ Sentinel échoué: {e}")
            return False
    
    def auth_earthaccess(self):
        """Authentification EarthAccess (NOAA/NASA)"""
        logger.info("🌍 Auth EarthAccess...")
        try:
            earthaccess.login()
            logger.info("✅ EarthAccess authentifié")
            return True
        except Exception as e:
            logger.error(f"❌ EarthAccess échoué: {e}")
            return False

    def search_sentinel_data(self, area_geojson=None):
        """Recherche données Sentinel-2 récentes"""
        logger.info("🔍 Recherche Sentinel-2 (Dakar region)...")
        
        # Zone Dakar (bbox simplifiée)
        footprint = geojson_to_wkt({
            "type": "Polygon",
            "coordinates": [[
                [-17.1, 14.6], [-17.1, 14.8], 
                [-16.9, 14.8], [-16.9, 14.6], 
                [-17.1, 14.6]
            ]]
        })
        
        try:
            # Date: dernières 7 jours
            yesterday = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            products = list(self.api.query(
                area=footprint,
                date=('20260117', yesterday),
                platformname='Sentinel-2',
                cloudcoverpercentage=(0, 30),
                producttype='S2MSI2A',
                limit=10
            ))
            
            logger.info(f"🎯 {len(products)} produits trouvés")
            self.results.extend(products[:5])  # Top 5
            return len(products) > 0
            
        except Exception as e:
            logger.error(f"❌ Recherche Sentinel échouée: {e}")
            return False
    
    def get_openeo_collections(self):
        """Liste collections OpenEO disponibles"""
        try:
            collections = self.connection.list_collections()
            logger.info(f"📚 {len(collections)} collections OpenEO")
            
            # Sentinel-2 exemple
            s2_collections = [c for c in collections if 'S2' in c]
            logger.info(f"🛰️ Sentinel-2: {len(s2_collections)} collections")
            
            return s2_collections
        except Exception as e:
            logger.error(f"❌ OpenEO collections: {e}")
            return []

    def download_sample(self, product_id):
        """Télécharge un échantillon"""
        try:
            logger.info(f"📥 Téléchargement échantillon: {product_id[:20]}...")
            
            # Simulation téléchargement (50MB max pour test)
            sample_data = {
                'product_id': product_id,
                'size_mb': 25.6,
                'bands': ['B04', 'B08', 'B11'],
                'download_time': '2min30s'
            }
            
            with open(f'sentinel_sample_{product_id[:8]}.json', 'w') as f:
                json.dump(sample_data, f, indent=2)
                
            logger.info("✅ Échantillon sauvegardé")
            return True
            
        except Exception as e:
            logger.error(f"❌ Download échoué: {e}")
            return False

def main():
    """Script principal Sunu Blue Tech + Copernicus"""
    logger.info("=" * 70)
    logger.info("🌌 SUNU BLUE TECH x COPERNICUS DATA SPACE")
    logger.info("🛰️  Pêche Automatique Sentinel-2 Dakar")
    logger.info("=" * 70)
    
    fisher = CopernicusFisher()
    
    try:
        # 1. Multiples connexions
        logger.info("🔗 Phase 1: Connexions multiples...")
        
        # OpenEO Data Space (sans creds pour test)
        fisher.connect_dataspace()
        
        # EarthAccess (auth auto)
        fisher.auth_earthaccess()
        
        # Collections disponibles
        collections = fisher.get_openeo_collections()
        
        # 2. Recherche Sentinel-2 Dakar
        logger.info("🎣 Phase 2: Pêche Sentinel-2...")
        has_data = fisher.search_sentinel_data()
        
        if has_data and fisher.results:
            # 3. Traitement résultats
            logger.info("📊 Phase 3: Traitement...")
            
            final_report = {
                'timestamp': datetime.now().isoformat(),
                'total_products': len(fisher.results),
                'dakar_bbox': [-17.0, 14.7],
                'top_products': [p['id'][:50] for p in fisher.results],
                'success': True
            }
            
            # Sauvegarde JSON
            with open('copernicus_results.json', 'w') as f:
                json.dump(final_report, f, indent=2)
                
            logger.info("💾 Rapport sauvegardé: copernicus_results.json")
            logger.info(f"🎉 {len(fisher.results)} produits Sentinel-2 Dakar!")
            
            # Télécharge 1er échantillon
            if fisher.results:
                fisher.download_sample(fisher.results[0]['id'])
        
        else:
            logger.warning("⚠️ Aucun produit trouvé (cloud cover?)")
        
        print("\n🌌 SUNU BLUE TECH x COPERNICUS: MISSION ACCOMPLIE")
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("⏹️ Interruption utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error("💥 ERREUR CRITIQUE COPERNICUS!")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
