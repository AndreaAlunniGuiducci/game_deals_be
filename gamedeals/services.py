import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DealListService:
    BASE_URL = "https://www.cheapshark.com/api/1.0/deals"
    
    @classmethod
    def fetch_games(cls) -> List[Dict]:
        try:
            params = {
                'pageSize': 16,
            }
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            games_data = response.json()
                    
            logger.info(f"Recuperati {len(games_data)} giochi dall'API")
            
            return games_data
            
        except requests.RequestException as e:
            logger.error(f"Errore nel recupero dei giochi: {e}")
            return []
    
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