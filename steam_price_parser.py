"""
Steam Price Parser - Get current prices from Steam Store API
"""
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import config
from steam_store_api import SteamStoreAPIClient
from itad_currency_mapping import (
    get_all_currencies,
    get_country_for_currency,
    get_currency_symbol,
    get_currency_name
)
from database import Database

logger = logging.getLogger(__name__)


class SteamPriceParser:
    """Parser for current Steam prices"""
    
    def __init__(self):
        """Initialize Steam price parser"""
        self.client = SteamStoreAPIClient()
        self.database = Database()
        self.currencies = get_all_currencies()
        self.parallel_threads = config.STEAM_PARSER_THREADS
        self.running = True
        
        logger.info(f"Initialized Steam Price Parser with {self.parallel_threads} parallel threads")
    
    def parse_current_prices(self, app_ids: List[int]) -> Dict:
        """
        Parse current prices for a list of App IDs
        
        Args:
            app_ids: List of Steam App IDs
            
        Returns:
            Dict with statistics: {'processed': X, 'errors': Y, 'records': Z}
        """
        stats = {'processed': 0, 'errors': 0, 'records': 0}
        
        logger.info(f"Processing {len(app_ids)} App IDs")
        
        # Get current datetime for all records
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Process App IDs in parallel
        all_records = []
        errors = []
        
        def process_app_id(app_id: int) -> tuple:
            """Process single App ID"""
            if not self.running:
                return app_id, None, False
            
            app_records = []
            app_errors = []
            
            # Try to get price for each currency
            for currency in self.currencies:
                if not self.running:
                    break
                
                country = get_country_for_currency(currency)
                if not country:
                    continue
                
                try:
                    price_data = self.client.get_price(app_id, country)
                    
                    if price_data is None:
                        continue
                    
                    # Skip free games (or save with price 0 if needed)
                    if price_data.get('is_free', False):
                        # Можно сохранить с ценой 0 или пропустить
                        # Пока пропускаем бесплатные игры
                        continue
                    
                    currency_code = price_data.get('currency', '')
                    if not currency_code:
                        continue
                    
                    # Verify currency matches
                    if currency_code.upper() != currency.upper():
                        continue
                    
                    # Create record
                    record = {
                        'app_id': app_id,
                        'datetime': current_datetime,
                        'price_final': price_data['price_final'],
                        'currency_symbol': currency_code,
                        'currency_name': get_currency_name(currency) or currency_code
                    }
                    
                    app_records.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error getting price for app_id {app_id}, currency {currency}: {e}")
                    app_errors.append((currency, str(e)))
                    continue
            
            if app_records:
                return app_id, app_records, True
            else:
                return app_id, None, False
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=self.parallel_threads) as executor:
            futures = {executor.submit(process_app_id, app_id): app_id 
                      for app_id in app_ids}
            
            for future in as_completed(futures):
                app_id = futures[future]
                try:
                    result_app_id, records, success = future.result()
                    
                    if records:
                        all_records.extend(records)
                        stats['processed'] += 1
                        stats['records'] += len(records)
                    else:
                        errors.append(app_id)
                        stats['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing app_id {app_id}: {e}")
                    errors.append(app_id)
                    stats['errors'] += 1
        
        # Save to database
        if all_records:
            self._save_to_database(all_records)
            logger.info(f"Saved {len(all_records)} records to database")
        
        logger.info(f"Completed: {stats['processed']} processed, {stats['errors']} errors, {stats['records']} records")
        
        return stats
    
    def _save_to_database(self, records: List[Dict]):
        """Save price records to database"""
        if not records:
            return
        
        try:
            self.database.save_price_data_batch(records)
        except Exception as e:
            logger.error(f"Error saving records to database: {e}")
            raise
    
    def stop(self):
        """Stop parser"""
        self.running = False
        logger.info("Steam price parser stopped")
    
    def close(self):
        """Close database connection"""
        self.database.close()

