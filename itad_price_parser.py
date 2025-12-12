"""
ITAD Price History Parser
Parses lowest price history for Steam games using ITAD API
"""
import logging
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import config
from itad_api import ITADAPIClient
from itad_currency_mapping import (
    get_all_currencies,
    get_country_for_currency,
    get_currency_symbol,
    get_currency_name
)

logger = logging.getLogger(__name__)


class ITADPriceParser:
    """Parser for ITAD price history"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ITAD price parser
        
        Args:
            api_key: ITAD API key (optional, can be set in config)
        """
        self.client = ITADAPIClient(api_key)
        self.currencies = get_all_currencies()
        self.output_dir = config.DATA_DIR / "itad_price_history"
        self.output_dir.mkdir(exist_ok=True)
        self._uuid_cache = {}  # Cache UUIDs for batch
    
    def parse_price_history(self, app_ids: List[int], batch_number: int = 1) -> Dict[str, int]:
        """
        Parse price history for a batch of app IDs across all currencies
        
        Args:
            app_ids: List of Steam app IDs
            batch_number: Batch number for file naming
            
        Returns:
            Dict with statistics: {'processed': X, 'errors': Y}
        """
        stats = {'processed': 0, 'errors': 0}
        
        logger.info(f"Processing batch {batch_number} with {len(app_ids)} app IDs")
        
        # Lookup UUIDs once for the entire batch
        game_ids_list = [f"steam/app/{app_id}" for app_id in app_ids]
        lookup_response = self.client.lookup_games_by_shop_id(game_ids_list)
        if not lookup_response:
            logger.warning(f"Failed to lookup game IDs for batch {batch_number}")
            return stats
        
        # Store UUIDs mapping
        self._uuid_cache = {}
        for shop_id, uuid in lookup_response.items():
            if uuid:
                try:
                    app_id = int(shop_id.split('/')[-1])
                    self._uuid_cache[app_id] = uuid
                except (ValueError, IndexError):
                    pass
        
        logger.info(f"Found {len(self._uuid_cache)} UUIDs for batch {batch_number}")
        
        # Collect all records across all currencies
        all_records = []
        
        # Process each currency
        for currency in self.currencies:
            country = get_country_for_currency(currency)
            
            if not country:
                logger.warning(f"No country mapping for currency {currency}, skipping")
                continue
            
            try:
                logger.info(f"Fetching price history for currency {currency} (country: {country})")
                
                # Get full price history for each game in batch
                history_data = []
                for app_id in app_ids:
                    if app_id not in self._uuid_cache:
                        continue
                    uuid = self._uuid_cache[app_id]
                    game_history = self.client.get_price_history(uuid, country, shops=[config.STEAM_SHOP_ID])
                    if game_history:
                        # Add app_id to each entry
                        for entry in game_history:
                            entry['app_id'] = app_id
                        history_data.extend(game_history)
                
                if not history_data:
                    logger.debug(f"No data returned for currency {currency}")
                    continue
                
                # Parse data for this currency
                price_records = self._parse_history_response(history_data, app_ids, currency)
                
                if price_records:
                    all_records.extend(price_records)
                    logger.info(f"Collected {len(price_records)} records for currency {currency}")
                else:
                    logger.debug(f"No price records extracted for currency {currency}")
                    
            except Exception as e:
                logger.error(f"Error processing currency {currency}: {e}", exc_info=True)
                stats['errors'] += 1
        
        # Save all records to single CSV file
        if all_records:
            self._save_to_csv(all_records, batch_number)
            stats['processed'] = len(all_records)
            logger.info(f"Saved {len(all_records)} total records to single CSV for batch {batch_number}")
        
        return stats
    
    def _parse_history_response(self, response: List[Dict], app_ids: List[int], currency: str) -> List[Dict]:
        """
        Parse ITAD API history response into price records
        
        Args:
            response: ITAD API response (list from /games/history/v2)
            app_ids: Original app IDs list
            currency: Currency code
            
        Returns:
            List of price records
        """
        records = []
        
        # Response format: [{timestamp, shop: {id, name}, deal: {price, regular, cut}}, ...]
        if isinstance(response, list):
            for entry in response:
                app_id = entry.get('app_id')
                if not app_id or app_id not in app_ids:
                    continue
                
                # Filter only Steam entries (shop.id == 61)
                shop = entry.get('shop', {})
                if shop.get('id') != config.STEAM_SHOP_ID:
                    continue
                
                record = self._parse_history_entry(entry, app_id, currency)
                if record:
                    records.append(record)
        
        return records
    
    def _parse_history_entry(self, entry: Dict, app_id: int, currency: str) -> Optional[Dict]:
        """
        Parse single history entry from ITAD API (/games/history/v2)
        
        Args:
            entry: Single history entry
            app_id: Steam app ID
            currency: Currency code
            
        Returns:
            Price record dict or None
        """
        try:
            # Extract timestamp
            timestamp = entry.get('timestamp')
            if not timestamp:
                return None
            
            # Normalize timestamp
            datetime_str = self._normalize_datetime(timestamp)
            
            # Extract price from deal format
            # Format: { "deal": { "price": { "amount": 9.99, "currency": "EUR" }, ... } }
            deal = entry.get('deal')
            if not deal or not isinstance(deal, dict):
                return None
            
            price_obj = deal.get('price')
            if not price_obj or not isinstance(price_obj, dict):
                return None
            
            price = price_obj.get('amount')
            entry_currency = price_obj.get('currency', '').upper()
            
            # Verify currency matches (or skip if different)
            if entry_currency and entry_currency != currency.upper():
                # Skip entries with different currency
                return None
            
            if price is None:
                return None
            
            # Get currency info
            currency_symbol = get_currency_symbol(currency)
            currency_name = get_currency_name(currency)
            
            return {
                'app_id': app_id,
                'datetime': datetime_str,
                'price_final': float(price),
                'currency_symbol': currency_symbol,
                'currency_name': currency_name
            }
            
        except Exception as e:
            logger.warning(f"Error parsing history entry: {e}")
            return None
    
    def _normalize_datetime(self, timestamp) -> str:
        """
        Normalize timestamp to YYYY-MM-DD HH:MM:SS format
        
        Args:
            timestamp: Timestamp in various formats
            
        Returns:
            Normalized datetime string
        """
        try:
            # Handle ISO format: "2022-12-27T11:21:08+01:00"
            if isinstance(timestamp, str):
                # Remove timezone info for simplicity
                if '+' in timestamp:
                    timestamp = timestamp.split('+')[0]
                elif 'Z' in timestamp:
                    timestamp = timestamp.replace('Z', '')
                
                # Try parsing ISO format
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # Try other formats
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d',
                    ]
                    for fmt in formats:
                        try:
                            dt = datetime.strptime(timestamp, fmt)
                            return dt.strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue
            
            # Handle Unix timestamp
            elif isinstance(timestamp, (int, float)):
                if timestamp > 1e10:
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            
            return str(timestamp)
            
        except Exception as e:
            logger.warning(f"Failed to normalize datetime {timestamp}: {e}")
            return str(timestamp)
    
    def _save_to_csv(self, records: List[Dict], batch_number: int):
        """
        Save price records to single CSV file
        
        Args:
            records: List of price records (all currencies combined)
            batch_number: Batch number
        """
        filename = self.output_dir / f"price_history_batch_{batch_number}.csv"
        
        # Sort by app_id, then datetime for better readability
        records_sorted = sorted(records, key=lambda x: (x['app_id'], x['datetime']))
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'app_id', 'datetime', 'price_final', 'currency_symbol', 'currency_name'
            ])
            writer.writeheader()
            writer.writerows(records_sorted)
        
        logger.debug(f"Saved {len(records_sorted)} records to {filename}")

