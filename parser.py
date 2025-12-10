#!/usr/bin/env python3
"""
Main parser script for SteamDB data collection
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import List
import time

import config
from database import Database
from browser_manager import BrowserManager
from batch_manager import BatchManager
from checkpoint import CheckpointManager
from ccu_parser import CCUParser
from price_parser import PriceParser
from progress import ProgressTracker
from steamcharts_parser import SteamChartsParser

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class SteamDBParser:
    """Main parser class"""
    
    def __init__(self, data_source: str = 'steamcharts'):
        """
        Initialize parser
        
        Args:
            data_source: 'steamcharts' or 'steamdb' (default: 'steamcharts')
        """
        self.database = Database()
        self.browser_manager = None
        self.checkpoint_manager = CheckpointManager(self.database)
        self.data_source = data_source
        
        if data_source == 'steamcharts':
            self.ccu_parser = SteamChartsParser()
            self.price_parser = None  # Price parsing not implemented for SteamCharts
        else:
            self.ccu_parser = CCUParser()
            self.price_parser = PriceParser()
        
        self.progress_tracker = None
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        logger.info("Received interrupt signal, shutting down gracefully...")
        self.running = False
    
    def load_app_ids(self) -> List[int]:
        """Load APP IDs from file"""
        if not config.APP_IDS_FILE.exists():
            logger.error(f"APP IDs file not found: {config.APP_IDS_FILE}")
            return []
        
        app_ids = []
        with open(config.APP_IDS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    app_ids.append(int(line))
        
        logger.info(f"Loaded {len(app_ids)} APP IDs from file")
        return app_ids
    
    async def process_batch_async(self, context, batch: List[int]):
        """Process a batch of APP IDs asynchronously"""
        results = {'ccu': {}, 'price': {}}
        
        try:
            if self.data_source == 'steamcharts':
                # SteamCharts API processing
                for app_id in batch:
                    try:
                        ccu_data_dict = await self.ccu_parser.fetch_ccu_data(app_id)
                        
                        # Save average and peak data separately
                        avg_data = ccu_data_dict.get('avg', [])
                        peak_data = ccu_data_dict.get('peak', [])
                        
                        if avg_data:
                            self.database.save_ccu_data(app_id, avg_data, value_type='avg')
                        if peak_data:
                            self.database.save_ccu_data(app_id, peak_data, value_type='peak')
                        
                        total_records = len(avg_data) + len(peak_data)
                        if total_records > 0:
                            self.checkpoint_manager.mark_ccu_done(app_id, total_records)
                            results['ccu'][app_id] = avg_data + peak_data
                        else:
                            self.checkpoint_manager.mark_app_error(
                                app_id, 'ccu', 'No data returned',
                                config.STEAMCHARTS_API_URL.format(appid=app_id)
                            )
                            results['ccu'][app_id] = []
                            
                    except Exception as e:
                        logger.error(f"Error processing SteamCharts data for app_id {app_id}: {e}")
                        self.checkpoint_manager.mark_app_error(
                            app_id, 'ccu', str(e),
                            config.STEAMCHARTS_API_URL.format(appid=app_id)
                        )
                        results['ccu'][app_id] = []
            
            else:
                # SteamDB processing (original logic)
                ccu_results = await self.ccu_parser.parse_ccu_batch(context, batch)
                results['ccu'] = ccu_results
                
                # Save CCU data
                for app_id, ccu_data in ccu_results.items():
                    if ccu_data:
                        self.database.save_ccu_data(app_id, ccu_data, value_type='avg')
                        self.checkpoint_manager.mark_ccu_done(app_id, len(ccu_data))
                    else:
                        self.checkpoint_manager.mark_app_error(app_id, 'ccu', 'No data returned', 
                                                              f"{config.STEAMDB_COMPARE_URL}{','.join(map(str, batch))}")
                
                # Delay between requests
                await asyncio.sleep(config.DELAY_BETWEEN_REQUESTS)
                
                # Parse Price data (one by one) - only for SteamDB
                if self.price_parser:
                    for app_id in batch:
                        try:
                            price_data = await self.price_parser.parse_price_data(context, app_id)
                            if price_data:
                                self.database.save_price_data(app_id, price_data)
                                self.checkpoint_manager.mark_price_done(app_id, len(price_data))
                                
                                # Mark as completed if CCU was also done
                                ccu_count = len(ccu_results.get(app_id, []))
                                if ccu_count > 0:
                                    self.checkpoint_manager.mark_app_completed(app_id, ccu_count, len(price_data))
                            else:
                                self.checkpoint_manager.mark_app_error(app_id, 'price', 'No data returned',
                                                                      f"{config.STEAMDB_APP_URL}/{app_id}/")
                        except Exception as e:
                            logger.error(f"Error processing Price for app_id {app_id}: {e}")
                            self.checkpoint_manager.mark_app_error(app_id, 'price', str(e),
                                                                  f"{config.STEAMDB_APP_URL}/{app_id}/")
                        
                        await asyncio.sleep(config.DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            for app_id in batch:
                error_url = (config.STEAMCHARTS_API_URL.format(appid=app_id) 
                           if self.data_source == 'steamcharts' 
                           else f"{config.STEAMDB_COMPARE_URL}{','.join(map(str, batch))}")
                self.checkpoint_manager.mark_app_error(app_id, 'ccu', str(e), error_url)
        
        return results
    
    async def _process_batch_with_context(self, context, batch: List[int], batch_manager: BatchManager):
        """Process batch and return context to pool"""
        try:
            await self.process_batch_async(context, batch)
            batch_manager.mark_batch_processed(batch)
        finally:
            await self.browser_manager.return_context(context)
    
    async def run_async(self):
        """Main async run method"""
        # Load APP IDs
        app_ids = self.load_app_ids()
        if not app_ids:
            logger.error("No APP IDs to process")
            return
        
        # Initialize checkpoint
        self.checkpoint_manager.initialize_app_ids(app_ids)
        
        # Get pending APP IDs
        pending_app_ids = self.checkpoint_manager.get_pending_app_ids()
        if not pending_app_ids:
            logger.info("No pending APP IDs to process")
            return
        
        logger.info(f"Starting parsing for {len(pending_app_ids)} APP IDs using {self.data_source}")
        
        # Initialize browser only for SteamDB
        if self.data_source == 'steamdb':
            self.browser_manager = BrowserManager(config.PARALLEL_THREADS)
            await self.browser_manager.initialize()
        
        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(self.checkpoint_manager)
        
        # Create batch manager
        batch_size = config.COMPARE_BATCH_SIZE if self.data_source == 'steamdb' else 1  # SteamCharts processes one at a time
        batch_manager = BatchManager(pending_app_ids, batch_size)
        
        processed_batches = 0
        
        if self.data_source == 'steamcharts':
            # SteamCharts: process without browser context
            try:
                while batch_manager.has_pending_batches() and self.running:
                    batch = batch_manager.get_next_batch()
                    if not batch:
                        break
                    
                    try:
                        # Process batch (no context needed for API)
                        await self.process_batch_async(None, batch)
                        batch_manager.mark_batch_processed(batch)
                        processed_batches += 1
                        
                        # Update progress
                        self.progress_tracker.update_progress()
                        
                        # Display statistics periodically
                        if processed_batches % 100 == 0:
                            self.progress_tracker.display_statistics(force=True)
                            self.checkpoint_manager.save_checkpoint()
                        
                    except Exception as e:
                        logger.error(f"Error processing batch: {e}")
                        # Continue with next batch even if this one failed
            finally:
                # Close SteamCharts parser session
                if isinstance(self.ccu_parser, SteamChartsParser):
                    await self.ccu_parser.close()
        
        else:
            # SteamDB: original browser-based processing
            context = await self.browser_manager.get_context()
            
            try:
                while batch_manager.has_pending_batches() and self.running:
                    batch = batch_manager.get_next_batch()
                    if not batch:
                        break
                    
                    try:
                        # Process batch using the same context (maintains session)
                        await self.process_batch_async(context, batch)
                        batch_manager.mark_batch_processed(batch)
                        processed_batches += 1
                        
                        # Save cookies after each batch to maintain session
                        cookies = await context.cookies()
                        if cookies:
                            self.browser_manager._save_cookies(cookies)
                        
                        # Update progress
                        self.progress_tracker.update_progress()
                        
                        # Display statistics periodically
                        if processed_batches % 10 == 0:
                            self.progress_tracker.display_statistics(force=True)
                            self.checkpoint_manager.save_checkpoint()
                        
                        # Small delay between batches
                        await asyncio.sleep(config.DELAY_BETWEEN_REQUESTS)
                        
                    except Exception as e:
                        logger.error(f"Error processing batch: {e}")
                        # Continue with next batch even if this one failed
            finally:
                # Return context to pool
                await self.browser_manager.return_context(context)
                await self.browser_manager.close()
        
        # Final statistics
        self.progress_tracker.display_statistics(force=True)
        self.checkpoint_manager.save_checkpoint()
        
        logger.info("Parsing completed")
    
    def run(self):
        """Main run method (synchronous entry point)"""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            if self.browser_manager:
                asyncio.run(self.browser_manager.close())
            if isinstance(self.ccu_parser, SteamChartsParser):
                asyncio.run(self.ccu_parser.close())
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            if self.browser_manager:
                asyncio.run(self.browser_manager.close())
            if isinstance(self.ccu_parser, SteamChartsParser):
                asyncio.run(self.ccu_parser.close())


def main():
    """Main entry point"""
    parser = SteamDBParser()
    parser.run()


if __name__ == "__main__":
    main()

