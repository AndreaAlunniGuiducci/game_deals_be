import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DealListService:
    BASE_URL = "https://www.cheapshark.com/api/1.0/deals"
    
    @classmethod
    def fetch_games(cls, store_id: Optional[str] = None) -> List[Dict]:
        try:
            params = {
            }
            if store_id:
                params['storeID'] = store_id
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            games_data = response.json()
                    
            logger.info(f"Recuperati {len(games_data)} giochi dall'API")
            
            return games_data
            
        except requests.RequestException as e:
            logger.error(f"Errore nel recupero dei giochi: {e}")
            return []
    
    @classmethod
    def fetch_games_by_stores(cls, store_ids: List[str], base_games_per_store: int = 5, total_target: int = 16) -> List[Dict]:

        all_games = []
        extra_games_needed = total_target - (base_games_per_store * len(store_ids))
        
        for store_id in store_ids:
            try:
                logger.info(f"Recupero giochi per store {store_id}")
                store_games = cls.fetch_games(store_id=store_id)
                
                if store_games:
                    selected_games = store_games[:base_games_per_store]
                    all_games.extend(selected_games)
                    logger.info(f"Aggiunti {len(selected_games)} giochi per store {store_id}")
                else:
                    logger.warning(f"Nessun gioco trovato per store {store_id}")
                    
            except Exception as e:
                logger.error(f"Errore nel recupero giochi per store {store_id}: {e}")
                continue
        
        if extra_games_needed > 0 and len(all_games) < total_target:
            logger.info(f"Recupero {extra_games_needed} giochi extra")
            
            for store_id in store_ids:
                if extra_games_needed <= 0:
                    break
                    
                try:
                    store_games = cls.fetch_games(store_id=store_id)
                    
                    if store_games and len(store_games) > base_games_per_store:
                        extra_games = store_games[base_games_per_store:base_games_per_store + extra_games_needed]
                        all_games.extend(extra_games)
                        logger.info(f"Aggiunti {len(extra_games)} giochi extra per store {store_id}")
                        extra_games_needed -= len(extra_games)
                        
                except Exception as e:
                    logger.error(f"Errore nel recupero giochi extra per store {store_id}: {e}")
                    continue
                
        logger.info(f"Totale giochi recuperati: {len(all_games)}")
        return all_games[:total_target]

    @classmethod
    def get_game_deals(cls, game_id: str) -> Optional[Dict]:
        try:
            response = requests.get(f"{cls.BASE_URL}?id={game_id}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Errore nel recupero del gioco {game_id}: {e}")
            return None
        
class StoreListService:
    BASE_URL = "https://www.cheapshark.com/api/1.0/stores"
    
    @classmethod
    def fetch_stores(cls) -> List[Dict]:
        try:
            response = requests.get(cls.BASE_URL, timeout=10)
            response.raise_for_status()
            stores_data = response.json()
            logger.info(f"Recuperati {len(stores_data)} negozi dall'API")
            return stores_data
        except requests.RequestException as e:
            logger.error(f"Errore nel recupero dei negozi: {e}")
            return []