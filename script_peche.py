import asyncio
import aiohttp
import logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor

# 1. LOGGING PRO
def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logger = logging.getLogger("PecheurConnect")
    handler = RotatingFileHandler("logs/pecheur_connect.log", maxBytes=2*1024*1024, backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logging()

# 2. COPERNICUS EN THREAD (Non-bloquant)
async def fetch_copernicus_async(dataset_id, variables, lat, lon, start, end):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        # Exécute la fonction bloquante dans un thread
        return await loop.run_in_executor(
            pool, _fetch_copernicus_variable, dataset_id, variables, lat, lon, start, end
        )

# 3. TRAITEMENT DE ZONE ASYNC
async def process_zone_async(session, name, coords, now):
    logger.info(f"Début traitement asynchrone : {name}")
    # Appel Météo Async
    weather = await fetch_weather_async(session, coords['lat'], coords['lon'])
    
    # Appel Copernicus (via Thread)
    # ... logique de récupération similairement adaptée ...
    
    logger.info(f"Zone {name} terminée avec succès.")
    return result # Dictionnaire de données

async def main_async():
    now = datetime.utcnow()
    async with aiohttp.ClientSession() as session:
        tasks = [process_zone_async(session, n, c, now) for n, c in ZONES.items()]
        data = await asyncio.gather(*tasks)
        # Suite de la logique (save, stats, telegram...)
        save_to_history(data)
        generate_all_stats()
        send_telegram(data)

if __name__ == "__main__":
    asyncio.run(main_async())
