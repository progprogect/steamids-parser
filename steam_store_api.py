"""
Steam Store API client for getting current prices
"""
import logging
import requests
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SteamStoreAPIClient:
    """Client for Steam Store API"""
    
    BASE_URL = "https://store.steampowered.com/api/appdetails"
    
    def __init__(self):
        """Initialize Steam Store API client"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.02  # 50 requests per second max (1/50 = 0.02)
    
    def _rate_limit(self):
        """Apply rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def get_price(self, app_id: int, country: str = 'US') -> Optional[Dict]:
        """
        Get current price for a game
        
        Args:
            app_id: Steam App ID
            country: Country code (US, RU, DE, GB, UA, etc.)
            
        Returns:
            {
                'currency': 'USD',
                'price_final': 20.99,
                'price_initial': 59.99,
                'discount_percent': 65,
                'is_free': False
            } or None
        """
        self._rate_limit()
        
        params = {
            'appids': app_id,
            'cc': country,
            'l': 'en'
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning(f"Rate limited (429) for app_id {app_id}, country {country}")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            if str(app_id) not in data:
                return None
            
            app_data = data[str(app_id)]
            
            if not app_data.get('success'):
                return None
            
            game_data = app_data.get('data', {})
            
            # Check if free
            if game_data.get('is_free', False):
                return {
                    'currency': None,
                    'price_final': 0.0,
                    'price_initial': 0.0,
                    'discount_percent': 0,
                    'is_free': True
                }
            
            # Get price overview
            price_overview = game_data.get('price_overview')
            
            if not price_overview:
                return None
            
            currency = price_overview.get('currency', '')
            final_price = price_overview.get('final', 0) / 100.0  # Convert from cents
            initial_price = price_overview.get('initial', 0) / 100.0
            discount_percent = price_overview.get('discount_percent', 0)
            
            return {
                'currency': currency,
                'price_final': final_price,
                'price_initial': initial_price,
                'discount_percent': discount_percent,
                'is_free': False
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for app_id {app_id}, country {country}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing response for app_id {app_id}, country {country}: {e}")
            return None

