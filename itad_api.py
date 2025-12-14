"""
ITAD (IsThereAnyDeal) API client for price history parsing
"""
import logging
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class ITADAPIClient:
    """Client for IsThereAnyDeal API"""
    
    BASE_URL = "https://api.isthereanydeal.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ITAD API client
        
        Args:
            api_key: ITAD API key (can be set via ITAD_API_KEY env var)
        """
        self.api_key = api_key or config.ITAD_API_KEY
        if not self.api_key:
            logger.warning("ITAD API key not provided. Some endpoints may not work.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SteamParser/1.0'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 request per second max (reduced to avoid 429 errors)
    
    def _rate_limit(self):
        """Apply rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _request(self, endpoint: str, params: Dict = None, method: str = 'GET') -> Optional[Dict]:
        """
        Make API request
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            method: HTTP method
            
        Returns:
            JSON response or None on error
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        if params is None:
            params = {}
        
        # Add API key if available
        if self.api_key:
            params['key'] = self.api_key
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=params, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def get_price_history(self, uuid: str, country: str = 'US', shops: List[int] = None, since: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Get full price history for a single game using /games/history/v2
        
        Args:
            uuid: ITAD game UUID
            country: Country code (US, EU, GB, UA, etc.)
            shops: List of shop IDs (default: [61] for Steam)
            since: Optional ISO timestamp to get history from (e.g., '2012-01-01T00:00:00Z')
            
        Returns:
            List of history entries or None on error
        """
        if shops is None:
            shops = [config.STEAM_SHOP_ID]
        
        params = {
            'id': uuid,
            'country': country,
            'shops': ','.join(map(str, shops))
        }
        
        # Add since parameter if provided
        if since:
            params['since'] = since
        else:
            # Default to 2012 if not specified
            params['since'] = config.ITAD_HISTORY_SINCE if hasattr(config, 'ITAD_HISTORY_SINCE') else '2012-01-01T00:00:00Z'
        
        response = self._request('/games/history/v2', params=params)
        
        if response and isinstance(response, list):
            return response
        
        return None
    
    def get_lowest_price_history(self, game_ids: List[int], country: str = 'US') -> Optional[List[Dict]]:
        """
        Get lowest price history for games using /games/historylow/v1
        
        Args:
            game_ids: List of Steam app IDs
            country: Country code (2-letter ISO)
            
        Returns:
            List of dicts with 'id' (UUID) and 'low' (historylow object) or None on error
        """
        # First, we need to lookup game IDs to get UUIDs
        # ITAD uses format: steam/app/{app_id} for lookup
        game_ids_list = [f"steam/app/{app_id}" for app_id in game_ids]
        
        # Lookup to get UUIDs
        lookup_response = self.lookup_games_by_shop_id(game_ids_list)
        if not lookup_response:
            logger.warning("Failed to lookup game IDs")
            return None
        
        # Extract UUIDs from lookup response
        # Response format: {"app/730": "uuid-string", "app/440": "uuid-string"} or {"app/730": None}
        uuids = []
        
        for shop_id, uuid in lookup_response.items():
            if uuid:  # UUID can be None if game not found
                if isinstance(uuid, str):
                    uuids.append(uuid)
                elif isinstance(uuid, dict) and 'id' in uuid:
                    uuids.append(uuid['id'])
        
        if not uuids:
            logger.warning("No UUIDs found in lookup response")
            return None
        
        # Now get history low using UUIDs
        params = {'country': country}
        response = self._request('/games/historylow/v1', params=params, method='POST', json_body=uuids)
        
        if response and isinstance(response, list):
            return response
        
        return None
    
    def get_store_lowest_prices(self, game_ids: List[int], country: str = 'US', shops: List[int] = None) -> Optional[List[Dict]]:
        """
        Get store lowest prices using /games/storelow/v2
        This is better for getting Steam-specific prices
        
        Args:
            game_ids: List of Steam app IDs
            country: Country code (2-letter ISO)
            shops: List of shop IDs (default: [61] for Steam)
            
        Returns:
            List of dicts with 'id' (UUID) and 'lows' (array of store lows) or None on error
        """
        if shops is None:
            shops = [config.STEAM_SHOP_ID]
        
        # First lookup to get UUIDs
        game_ids_list = [f"steam/app/{app_id}" for app_id in game_ids]
        lookup_response = self.lookup_games_by_shop_id(game_ids_list)
        if not lookup_response:
            logger.warning("Failed to lookup game IDs")
            return None
        
        # Extract UUIDs from lookup response
        # Response format: {"app/730": "uuid-string", "app/440": "uuid-string"} or {"app/730": None}
        uuids = []
        uuid_to_app_id = {}  # Map UUID to app_id for later use
        
        for shop_id, uuid in lookup_response.items():
            if uuid:  # UUID can be None if game not found
                if isinstance(uuid, str):
                    uuids.append(uuid)
                    # Extract app_id from shop_id format "app/730"
                    try:
                        app_id = int(shop_id.split('/')[-1])
                        uuid_to_app_id[uuid] = app_id
                    except (ValueError, IndexError):
                        logger.warning(f"Could not extract app_id from {shop_id}")
                elif isinstance(uuid, dict) and 'id' in uuid:
                    uuid_str = uuid['id']
                    uuids.append(uuid_str)
                    try:
                        app_id = int(shop_id.split('/')[-1])
                        uuid_to_app_id[uuid_str] = app_id
                    except (ValueError, IndexError):
                        pass
        
        if not uuids:
            logger.warning("No UUIDs found in lookup response")
            return None
        
        # Get store lows
        params = {
            'country': country,
            'shops': ','.join(map(str, shops))
        }
        response = self._request('/games/storelow/v2', params=params, method='POST', json_body=uuids)
        
        if response and isinstance(response, list):
            # Add app_id mapping to response
            for item in response:
                if 'id' in item and item['id'] in uuid_to_app_id:
                    item['app_id'] = uuid_to_app_id[item['id']]
            return response
        
        return None
    
    def lookup_games_by_shop_id(self, shop_ids: List[str]) -> Optional[Dict]:
        """
        Lookup games by shop ID to get UUIDs
        
        Args:
            shop_ids: List of shop IDs in format ["steam/app/730", "steam/app/440"]
            
        Returns:
            Dict mapping shop_id to UUID (or None if not found)
        """
        # Use /lookup/id/shop/{shopId}/v1 endpoint (POST)
        # shopId = 61 for Steam (numeric ID)
        # Format shop_ids: remove "steam/" prefix, keep "app/730"
        formatted_ids = [sid.replace('steam/', '') if sid.startswith('steam/') else sid for sid in shop_ids]
        response = self._request('/lookup/id/shop/61/v1', method='POST', json_body=formatted_ids)
        return response
    
    def _request(self, endpoint: str, params: Dict = None, method: str = 'GET', json_body: List = None, max_retries: int = 3) -> Optional[Dict]:
        """
        Make API request with retry logic for rate limiting
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            method: HTTP method
            json_body: JSON body for POST requests (list of UUIDs or game IDs)
            max_retries: Maximum number of retries for 429 errors
            
        Returns:
            JSON response or None on error
        """
        url = f"{self.BASE_URL}{endpoint}"
        if params is None:
            params = {}
        
        # Add API key if available
        if self.api_key:
            params['key'] = self.api_key
        
        for attempt in range(max_retries):
            self._rate_limit()
            
            try:
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=30)
                elif method == 'POST':
                    if json_body:
                        response = self.session.post(url, params=params, json=json_body, timeout=30)
                    else:
                        response = self.session.post(url, params=params, json=params, timeout=30)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # Handle 429 Too Many Requests
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))  # Default 60 seconds
                    wait_time = retry_after * (attempt + 1)  # Exponential backoff
                    logger.warning(f"Rate limited (429). Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    wait_time = retry_after * (attempt + 1)
                    logger.warning(f"Rate limited (429). Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API request failed: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_detail = e.response.json()
                            logger.error(f"Error details: {error_detail}")
                        except:
                            logger.error(f"Response text: {e.response.text[:500]}")
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_detail = e.response.json()
                        logger.error(f"Error details: {error_detail}")
                    except:
                        logger.error(f"Response text: {e.response.text[:500]}")
                return None
        
        # All retries exhausted
        logger.error(f"Failed after {max_retries} retries for {endpoint}")
        return None
    
    def get_game_info(self, game_id: int) -> Optional[Dict]:
        """
        Get game information
        
        Args:
            game_id: Steam app ID
            
        Returns:
            Game info dict or None
        """
        params = {
            'game_id': f"steam/app/{game_id}"
        }
        
        return self._request('/games/info/v1', params=params)

