"""
Steam Price Parser Main - Orchestrator for parsing current prices from Steam API
"""
import logging
from typing import List
from database import Database
from steam_price_parser import SteamPriceParser
import config

logger = logging.getLogger(__name__)


class SteamParserMain:
    """Main orchestrator for Steam price parser"""
    
    def __init__(self):
        """Initialize Steam parser main"""
        self.database = Database()
        self.parser = SteamPriceParser()
        self.running = True
    
    def load_error_app_ids(self) -> List[int]:
        """Load App IDs with itad_error status from database"""
        cursor = self.database._get_cursor()
        
        if self.database.use_postgresql:
            cursor.execute("""
                SELECT app_id
                FROM app_status
                WHERE status = 'itad_error'
                ORDER BY app_id
            """)
        else:
            cursor.execute("""
                SELECT app_id
                FROM app_status
                WHERE status = 'itad_error'
                ORDER BY app_id
            """)
        
        rows = cursor.fetchall()
        
        if self.database.use_postgresql:
            app_ids = [row['app_id'] for row in rows]
        else:
            app_ids = [row[0] for row in rows]
        
        logger.info(f"Loaded {len(app_ids)} App IDs with itad_error status")
        return app_ids
    
    def run(self):
        """Run Steam price parser"""
        try:
            # Load App IDs with errors
            app_ids = self.load_error_app_ids()
            
            if not app_ids:
                logger.warning("No App IDs with errors found")
                return
            
            logger.info(f"Processing {len(app_ids)} App IDs")
            
            # Split into batches
            batch_size = config.STEAM_BATCH_SIZE
            batches = [
                app_ids[i:i + batch_size]
                for i in range(0, len(app_ids), batch_size)
            ]
            
            total_batches = len(batches)
            logger.info(f"Split into {total_batches} batches of {batch_size} App IDs")
            
            # Process batches
            total_processed = 0
            total_errors = 0
            total_records = 0
            
            for batch_num, batch_app_ids in enumerate(batches, 1):
                if not self.running:
                    logger.info("Parser stopped by user signal")
                    break
                
                logger.info(f"\n{'='*70}")
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_app_ids)} App IDs)")
                logger.info(f"{'='*70}")
                
                try:
                    # Parse batch
                    stats = self.parser.parse_current_prices(batch_app_ids)
                    
                    batch_processed = stats.get('processed', 0)
                    batch_errors = stats.get('errors', 0)
                    batch_records = stats.get('records', 0)
                    
                    total_processed += batch_processed
                    total_errors += batch_errors
                    total_records += batch_records
                    
                    logger.info(f"Batch {batch_num} summary: {batch_processed} processed, {batch_errors} errors, {batch_records} records")
                    
                    # Check if parser was stopped
                    if not self.running:
                        logger.warning("Parser was stopped during batch processing")
                        break
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                    total_errors += len(batch_app_ids)
                    continue
            
            # Final summary
            logger.info(f"\n{'='*70}")
            if not self.running:
                logger.info("PARSING STOPPED (not completed)")
            else:
                logger.info("PARSING COMPLETED")
            logger.info(f"{'='*70}")
            logger.info(f"Batches processed: {batch_num}/{total_batches}")
            logger.info(f"Total apps processed successfully: {total_processed}")
            logger.info(f"Total apps with errors: {total_errors}")
            logger.info(f"Total price records saved: {total_records}")
            logger.info(f"{'='*70}\n")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise
        finally:
            self.parser.close()
            self.database.close()
    
    def stop(self):
        """Stop parser"""
        self.running = False
        self.parser.stop()
        logger.info("Steam parser stopped")

