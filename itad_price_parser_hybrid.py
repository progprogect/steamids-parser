"""
ITAD Price History Parser - Hybrid Approach
Stage 1: Storelow (batched) to determine available currencies
Stage 2: History (parallel) only for available currencies
"""
import logging
import time
from typing import List, Dict, Optional, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import config
from itad_api import ITADAPIClient
from itad_currency_mapping import (
    get_all_currencies,
    get_country_for_currency,
    get_currency_symbol,
    get_currency_name
)
from database import Database
from checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class ITADPriceParserHybrid:
    """Hybrid ITAD price parser with storelow + history approach"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ITAD hybrid price parser
        
        Args:
            api_key: ITAD API key (optional, can be set in config)
        """
        self.client = ITADAPIClient(api_key)
        self.database = Database()
        self.checkpoint_manager = CheckpointManager(self.database)
        self.currencies = get_all_currencies()
        self.parallel_threads = config.ITAD_PARALLEL_THREADS
        self.running = True
        
        # Cache for UUIDs per batch
        self._uuid_cache = {}
        
        logger.info(f"Initialized ITAD Hybrid Parser with {self.parallel_threads} parallel threads")
    
    def parse_price_history_batch(self, app_ids: List[int], batch_number: int) -> Dict[str, int]:
        """
        Parse price history for a batch using hybrid approach
        
        Args:
            app_ids: List of Steam app IDs
            batch_number: Batch number
            
        Returns:
            Dict with statistics: {'processed': X, 'errors': Y}
        """
        stats = {'processed': 0, 'errors': 0, 'currencies_found': 0}
        
        logger.info(f"Processing batch {batch_number} with {len(app_ids)} app IDs")
        
        # Step 1: Lookup UUIDs once for the batch
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
        
        # Step 2: Determine available currencies using storelow (batched)
        available_currencies = self._determine_available_currencies(app_ids)
        stats['currencies_found'] = sum(len(currencies) for currencies in available_currencies.values())
        
        avg_currencies = stats['currencies_found'] / len(app_ids) if app_ids else 0
        games_with_currencies = sum(1 for currencies in available_currencies.values() if currencies)
        games_without_currencies = len(app_ids) - games_with_currencies
        
        logger.info(f"Determined available currencies: avg {avg_currencies:.1f} per game")
        logger.info(f"Games with currencies found: {games_with_currencies}/{len(app_ids)}")
        if games_without_currencies > 0:
            logger.warning(f"Games without any currencies: {games_without_currencies} (these will be marked as errors)")
        
        # Step 3: Fetch history only for available currencies (parallel)
        all_records = []
        errors = []
        
        # Process each game with its available currencies
        for app_id in app_ids:
            if app_id not in self._uuid_cache:
                errors.append(app_id)
                self.checkpoint_manager.mark_itad_error(app_id, "UUID not found in lookup")
                continue
            
            currencies = available_currencies.get(app_id, set())
            if not currencies:
                logger.debug(f"No currencies found for app_id {app_id}")
                # Mark as error - no currencies available in ITAD
                self.checkpoint_manager.mark_itad_error(app_id, "No currencies found in ITAD")
                errors.append(app_id)
                continue
            
            # Mark currencies as checked
            self.checkpoint_manager.mark_itad_currencies_checked(app_id, list(currencies))
            
            uuid = self._uuid_cache[app_id]
            
            # Fetch history for this game's currencies (parallel)
            game_records = self._fetch_history_for_currencies(app_id, uuid, currencies)
            
            if game_records:
                all_records.extend(game_records)
                # Mark as completed
                self.checkpoint_manager.mark_itad_completed(app_id, len(game_records))
            else:
                errors.append(app_id)
                self.checkpoint_manager.mark_itad_error(app_id, "No history records found")
        
        # Step 4: Save to database
        if all_records:
            self._save_to_database(all_records)
            logger.info(f"Saved {len(all_records)} records to database for batch {batch_number}")
        
        # Calculate statistics
        stats['processed'] = len(app_ids) - len(errors)  # Successfully processed apps
        stats['errors'] = len(errors)
        
        if errors:
            logger.warning(f"Failed to fetch history for {len(errors)} games in batch {batch_number}")
        
        logger.info(f"Batch {batch_number} completed: {stats['processed']} processed, {stats['errors']} errors")
        
        return stats
    
    def _determine_available_currencies(self, app_ids: List[int]) -> Dict[int, Set[str]]:
        """
        Stage 1: Determine available currencies using storelow (batched)
        
        Args:
            app_ids: List of Steam app IDs
            
        Returns:
            Dict mapping app_id to set of available currency codes
        """
        available_currencies = {app_id: set() for app_id in app_ids}
        
        logger.info(f"Stage 1: Determining available currencies for {len(app_ids)} games")
        
        # Process each currency (storelow supports batching)
        for currency in self.currencies:
            if not self.running:
                break
                
            country = get_country_for_currency(currency)
            if not country:
                logger.warning(f"No country mapping for currency {currency}, skipping")
                continue
            
            try:
                # Storelow request for entire batch (batched!)
                # Add delay between storelow requests to avoid rate limiting
                time.sleep(config.ITAD_REQUEST_DELAY)
                
                storelow_result = self.client.get_store_lowest_prices(
                    app_ids, 
                    country=country, 
                    shops=[config.STEAM_SHOP_ID]
                )
                
                if storelow_result:
                    games_with_lows = 0
                    games_with_matching_currency = 0
                    
                    for game in storelow_result:
                        # app_id is already added by get_store_lowest_prices
                        app_id = game.get('app_id')
                        lows = game.get('lows', [])
                        
                        if app_id and lows:
                            games_with_lows += 1
                            # Check if currency matches
                            for low in lows:
                                low_currency = low.get('price', {}).get('currency', '').upper()
                                if low_currency == currency.upper():
                                    available_currencies[app_id].add(currency)
                                    games_with_matching_currency += 1
                                    break
                    
                    # Логируем статистику для диагностики (только для первых нескольких валют)
                    if currency in list(self.currencies)[:3]:  # Только для первых 3 валют
                        logger.debug(f"Currency {currency} ({country}): {len(storelow_result)} games returned, "
                                   f"{games_with_lows} with lows, {games_with_matching_currency} matching currency")
                else:
                    # Логируем если результат пустой (только для первых валют)
                    if currency in list(self.currencies)[:3]:
                        logger.debug(f"Currency {currency} ({country}): storelow returned None or empty")
                
            except Exception as e:
                logger.error(f"Error determining currencies for {currency}: {e}")
                continue
        
        return available_currencies
    
    def _fetch_history_for_currencies(self, app_id: int, uuid: str, currencies: Set[str]) -> List[Dict]:
        """
        Stage 2: Fetch history for available currencies (parallel)
        
        Args:
            app_id: Steam app ID
            uuid: ITAD game UUID
            currencies: Set of available currency codes
            
        Returns:
            List of price records
        """
        all_records = []
        
        def fetch_currency_history(currency: str) -> List[Dict]:
            """Fetch history for a single currency"""
            if not self.running:
                return []
            
            country = get_country_for_currency(currency)
            if not country:
                return []
            
            try:
                # Get history since 2012
                since_date = getattr(config, 'ITAD_HISTORY_SINCE', '2012-01-01T00:00:00Z')
                history_data = self.client.get_price_history(
                    uuid, 
                    country, 
                    shops=[config.STEAM_SHOP_ID],
                    since=since_date
                )
                
                if not history_data:
                    return []
                
                # Parse history entries
                records = []
                for entry in history_data:
                    record = self._parse_history_entry(entry, app_id, currency)
                    if record:
                        records.append(record)
                
                return records
                
            except Exception as e:
                logger.warning(f"Error fetching history for app_id {app_id}, currency {currency}: {e}")
                return []
        
        # Parallel execution for all currencies
        with ThreadPoolExecutor(max_workers=self.parallel_threads) as executor:
            futures = {executor.submit(fetch_currency_history, currency): currency 
                      for currency in currencies}
            
            for future in as_completed(futures):
                currency = futures[future]
                try:
                    records = future.result()
                    if records:
                        all_records.extend(records)
                        logger.debug(f"Fetched {len(records)} records for app_id {app_id}, currency {currency}")
                except Exception as e:
                    logger.error(f"Error processing currency {currency} for app_id {app_id}: {e}")
        
        return all_records
    
    def _parse_history_entry(self, entry: Dict, app_id: int, currency: str) -> Optional[Dict]:
        """
        Parse single history entry from ITAD API
        
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
            deal = entry.get('deal')
            if not deal or not isinstance(deal, dict):
                return None
            
            price_obj = deal.get('price')
            if not price_obj or not isinstance(price_obj, dict):
                return None
            
            price = price_obj.get('amount')
            entry_currency = price_obj.get('currency', '').upper()
            
            # Verify currency matches
            if entry_currency and entry_currency != currency.upper():
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
                # Try parsing ISO format with timezone first
                if 'T' in timestamp:
                    # Handle timezone formats
                    if '+' in timestamp:
                        # Format: "2022-12-27T11:21:08+01:00"
                        dt = datetime.fromisoformat(timestamp)
                    elif timestamp.endswith('Z'):
                        # Format: "2022-12-27T11:21:08Z"
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        # Format: "2022-12-27T11:21:08" (no timezone)
                        dt = datetime.fromisoformat(timestamp)
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
    
    def _save_to_database(self, records: List[Dict]):
        """
        Save price records to database (batch insert)
        
        Args:
            records: List of price records
        """
        if not records:
            return
        
        try:
            self.database.save_price_data_batch(records)
            logger.debug(f"Saved {len(records)} records to database")
        except Exception as e:
            logger.error(f"Error saving records to database: {e}")
            raise

